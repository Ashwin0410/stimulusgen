import io
import re
import time
import tempfile
from typing import List

import requests
from pydub import AudioSegment

from app.config import ELEVENLABS_API_KEY, ELEVENLABS_BASE_URL

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[\.\!\?])\s+')
_PAUSE_TOKEN = "[pause]"
_PAUSE_SENTINEL = "<<<PAUSE>>>"

DEFAULT_MAX_CHARS = 3200


def _split_text_into_chunks(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    sentences = _SENTENCE_SPLIT_RE.split(text)
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0

    for s in sentences:
        s = s.strip()
        if not s:
            continue
        add_len = len(s) + (1 if cur_len > 0 else 0)
        if cur_len + add_len <= max_chars:
            cur.append(s)
            cur_len += add_len
        else:
            if cur:
                chunks.append(" ".join(cur))
            if len(s) > max_chars:
                for i in range(0, len(s), max_chars):
                    chunks.append(s[i:i + max_chars])
                cur, cur_len = [], 0
            else:
                cur, cur_len = [s], len(s)

    if cur:
        chunks.append(" ".join(cur))
    return chunks


def _is_v3_model(model: str) -> bool:
    """Check if the model is an ElevenLabs v3 model."""
    return model.startswith("eleven_v3")


def _synth_chunk(
    text: str,
    voice_id: str,
    model: str = "eleven_v3",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    speaker_boost: bool = True,
    speed: float = 1.0,
    timeout: int = 120,
    max_retries: int = 3,
    backoff_base: float = 1.5,
) -> AudioSegment:
    
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    
    # Build voice_settings based on model type
    # v3 models ONLY support stability - other params cause 400 Bad Request
    if _is_v3_model(model):
        voice_settings = {
            "stability": stability,
        }
    else:
        voice_settings = {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": speaker_boost,
        }
    
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": voice_settings,
    }
    
    # v3 models support speed parameter directly in the API payload
    if _is_v3_model(model) and speed != 1.0:
        payload["speed"] = speed

    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=timeout,
            )

            if r.status_code in (429, 500, 502, 503, 504):
                last_exc = Exception(f"ElevenLabs HTTP {r.status_code}")
                if attempt < max_retries:
                    sleep_s = backoff_base ** attempt
                    print(f"[TTS] HTTP {r.status_code}, retrying in {sleep_s:.1f}s...")
                    time.sleep(sleep_s)
                    continue
                else:
                    r.raise_for_status()

            r.raise_for_status()

            buf = io.BytesIO()
            for c in r.iter_content(16384):
                if c:
                    buf.write(c)
            buf.seek(0)
            return AudioSegment.from_file(buf, format="mp3")

        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            if attempt < max_retries:
                sleep_s = backoff_base ** attempt
                print(f"[TTS] Network error, retrying in {sleep_s:.1f}s...")
                time.sleep(sleep_s)
                continue
            else:
                raise

        except requests.RequestException as e:
            last_exc = e
            if attempt < max_retries:
                sleep_s = backoff_base ** attempt
                print(f"[TTS] Request error, retrying in {sleep_s:.1f}s...")
                time.sleep(sleep_s)
                continue
            else:
                raise

    if last_exc:
        raise last_exc
    raise RuntimeError("Unknown TTS error")


def synthesize_speech(
    text: str,
    voice_id: str,
    model: str = "eleven_v3",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    speaker_boost: bool = True,
    speed: float = 1.0,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    raw = (text or "").strip()
    if not raw:
        silent = AudioSegment.silent(duration=1000, frame_rate=44100)
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        silent.export(f.name, format="wav")
        return f.name

    raw = raw.replace("[breath]", " ")
    raw = raw.replace(_PAUSE_TOKEN, f" {_PAUSE_SENTINEL} ")

    blocks = [b.strip() for b in raw.split(_PAUSE_SENTINEL) if b.strip()]
    if not blocks:
        silent = AudioSegment.silent(duration=1000, frame_rate=44100)
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        silent.export(f.name, format="wav")
        return f.name

    segs: List[AudioSegment] = []
    PAUSE_MS = 900
    CHUNK_GAP_MS = 350

    for block_idx, block in enumerate(blocks):
        parts = _split_text_into_chunks(block, max_chars=max_chars)
        for j, p in enumerate(parts):
            print(f"[TTS] Synthesizing block {block_idx + 1}/{len(blocks)}, chunk {j + 1}/{len(parts)}, len={len(p)}")
            
            seg = _synth_chunk(
                p,
                voice_id,
                model=model,
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                speaker_boost=speaker_boost,
                speed=speed,
            )
            segs.append(seg)
            
            if j < len(parts) - 1:
                segs.append(AudioSegment.silent(duration=CHUNK_GAP_MS, frame_rate=44100))

        if block_idx < len(blocks) - 1:
            segs.append(AudioSegment.silent(duration=PAUSE_MS, frame_rate=44100))

    full = segs[0]
    for s in segs[1:]:
        full += s

    # Only apply pydub speed adjustment for non-v3 models
    # v3 models handle speed directly via API
    if not _is_v3_model(model) and speed != 1.0 and 0.5 <= speed <= 2.0:
        full = full._spawn(full.raw_data, overrides={
            "frame_rate": int(full.frame_rate * speed)
        }).set_frame_rate(44100)

    outf = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    full.export(outf.name, format="wav")
    return outf.name


def get_available_voices() -> list:
    url = f"{ELEVENLABS_BASE_URL}/voices"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        voices = []
        for v in data.get("voices", []):
            voices.append({
                "voice_id": v.get("voice_id", ""),
                "name": v.get("name", ""),
                "category": v.get("category", ""),
                "description": v.get("description", ""),
                "preview_url": v.get("preview_url", ""),
            })
        return voices
    except Exception as e:
        print(f"[TTS] Error fetching voices: {e}")
        return []
