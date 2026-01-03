from __future__ import annotations
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, Optional

from pydub import AudioSegment

from app.config import FFMPEG_BIN, OUTPUTS_DIR
from app.utils.audio import load_audio, normalize_dbfs, make_stereo


def _ffmpeg_available() -> bool:
    try:
        subprocess.run([FFMPEG_BIN, "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def _ffmpeg_has(needle: str) -> bool:
    try:
        out = subprocess.run(
            [FFMPEG_BIN, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=True,
        )
        return needle in (out.stdout + out.stderr)
    except Exception:
        return False


def _atempo_chain(factor: float) -> str:
    if factor <= 0:
        return "atempo=1.0"
    parts = []
    f = float(factor)
    while f > 2.0:
        parts.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        parts.append("atempo=0.5")
        f *= 2.0
    parts.append(f"atempo={f:.6f}")
    return ",".join(parts)


def _retime_with_ffmpeg(src_wav: str, target_ms: int) -> str:
    seg = AudioSegment.from_file(src_wav)
    cur_ms = len(seg)
    
    if cur_ms <= 0 or target_ms <= 0:
        out_raw = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        seg.export(out_raw.name, format="wav")
        return out_raw.name

    max_delta_ratio = 0.15
    lo = int(target_ms * (1 - max_delta_ratio))
    hi = int(target_ms * (1 + max_delta_ratio))
    
    if cur_ms < lo:
        pad = AudioSegment.silent(duration=target_ms - cur_ms, frame_rate=seg.frame_rate)
        seg = seg + pad
    elif cur_ms > hi:
        seg = seg[:target_ms]

    mid_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    seg.export(mid_wav.name, format="wav")

    cur_ms2 = len(AudioSegment.from_file(mid_wav.name))
    factor = max(1e-6, cur_ms2 / float(target_ms))

    out_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", mid_wav.name,
        "-filter:a", _atempo_chain(factor),
        out_wav.name,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_wav.name


def _rms_dbfs(chunk: AudioSegment) -> float:
    if chunk.rms <= 1:
        return -120.0
    return 20.0 * math.log10(chunk.rms / float(1 << (8 * chunk.sample_width - 1)))


def _peak_dbfs(seg: AudioSegment) -> float:
    sample_peak = seg.max
    full_scale = float(1 << (8 * seg.sample_width - 1))
    if sample_peak <= 0:
        return -120.0
    return 20.0 * math.log10(sample_peak / full_scale)


def _apply_peak_guard(seg: AudioSegment, ceiling_dbfs: float = -1.0) -> AudioSegment:
    pk = _peak_dbfs(seg)
    headroom = ceiling_dbfs - pk
    if headroom < 0:
        seg = seg.apply_gain(headroom)
    return seg


def _hard_fit(seg: AudioSegment, target_ms: int) -> AudioSegment:
    if len(seg) < target_ms:
        return seg + AudioSegment.silent(duration=target_ms - len(seg), frame_rate=seg.frame_rate)
    elif len(seg) > target_ms:
        return seg[:target_ms]
    return seg


def _hard_fit_samples(seg: AudioSegment, target_samples_per_ch: int) -> AudioSegment:
    """Sample-accurate fitting for precise audio alignment."""
    ch = seg.channels
    sw = seg.sample_width
    frame_bytes = ch * sw

    raw = seg.raw_data
    total_frames = len(raw) // frame_bytes
    if total_frames == target_samples_per_ch:
        return seg

    if total_frames > target_samples_per_ch:
        new_bytes = target_samples_per_ch * frame_bytes
        raw = raw[:new_bytes]
        return seg._spawn(raw)
    else:
        need_frames = target_samples_per_ch - total_frames
        pad_ms = int(1000 * need_frames / seg.frame_rate)
        silence = AudioSegment.silent(duration=pad_ms, frame_rate=seg.frame_rate).set_channels(ch).set_sample_width(sw)
        out = seg + silence
        raw2 = out.raw_data[: target_samples_per_ch * frame_bytes]
        return out._spawn(raw2)


def _decode_samples(path: Path) -> tuple[int, int, int]:
    """Decode and return (total_frames, frame_rate, channels) for verification."""
    seg = AudioSegment.from_file(str(path))
    ch = seg.channels
    sw = seg.sample_width
    frame_bytes = ch * sw
    total_frames = len(seg.raw_data) // frame_bytes
    return total_frames, seg.frame_rate, ch


def analyze_music(music_path: str | Path, frame_ms: int = 200) -> dict:
    """Analyze music to find drop/climax point."""
    seg = make_stereo(load_audio(music_path).set_frame_rate(44100))
    if len(seg) <= 0:
        return {"drop_ms": None, "frame_ms": frame_ms}

    win = max(50, frame_ms)
    energies: list[float] = []
    for i in range(0, len(seg), win):
        chunk = seg[i: i + win]
        energies.append(_rms_dbfs(chunk))

    if not energies:
        return {"drop_ms": None, "frame_ms": win}

    k = 4
    smoothed: list[float] = []
    for i in range(len(energies)):
        lo = max(0, i - k)
        hi = min(len(energies), i + k + 1)
        smoothed.append(sum(energies[lo:hi]) / (hi - lo))

    diffs = [smoothed[i + 1] - smoothed[i] for i in range(len(smoothed) - 1)]
    if not diffs:
        return {"drop_ms": None, "frame_ms": win}

    search_len = max(1, int(0.8 * len(diffs)))
    search_diffs = diffs[:search_len]

    max_idx = max(range(len(search_diffs)), key=lambda i: search_diffs[i])
    drop_ms = max_idx * win

    return {"drop_ms": drop_ms, "frame_ms": win}


def _duck_music_to_voice(
    music: AudioSegment,
    voice: AudioSegment,
    floor_boost_db: float = 3.0,
    max_duck_db: float = -3.0,
    attack_ms: int = 180,
    release_ms: int = 650,
    win_ms: int = 60,
    lookahead_ms: int = 500,
    gap_hold_ms: int = 2600,
) -> AudioSegment:
    """Duck music volume when voice is present with lookahead."""
    win = max(20, win_ms)
    step = win
    out = AudioSegment.silent(duration=0, frame_rate=music.frame_rate)
    prev_gain = 0.0
    silence_threshold_db = -45.0
    in_voice_region = False
    silence_run_ms = 0

    for i in range(0, len(music), step):
        i_ms = i
        m_chunk = music[i_ms: i_ms + win]

        start_v_la = i_ms + lookahead_ms
        end_v_la = start_v_la + win
        v_chunk_la = voice[start_v_la:end_v_la]
        v_db_la = _rms_dbfs(v_chunk_la)

        v_now = voice[i_ms: i_ms + win]
        v_now_db = _rms_dbfs(v_now)
        voice_now = v_now_db > silence_threshold_db

        if voice_now:
            in_voice_region = True
            silence_run_ms = 0
        else:
            if in_voice_region:
                silence_run_ms += step
                if silence_run_ms >= gap_hold_ms:
                    in_voice_region = False
            else:
                silence_run_ms = 0

        if v_db_la <= -48.0:
            target = floor_boost_db
        elif v_db_la >= -26.0:
            target = max_duck_db
        else:
            t = (v_db_la + 48.0) / 22.0
            target = max_duck_db * t + floor_boost_db * (1 - t)

        short_gap = (not voice_now) and in_voice_region and (silence_run_ms < gap_hold_ms)
        if short_gap:
            hold_level = max(max_duck_db + 1.5, -1.5)
            target = min(target, hold_level)

        if target < prev_gain:
            alpha = min(1.0, step / float(max(1, attack_ms)))
        else:
            alpha = min(1.0, step / float(max(1, release_ms)))
        gain = prev_gain + alpha * (target - prev_gain)
        prev_gain = gain

        out += m_chunk.apply_gain(gain)

    return out


def _build_user_voice_effects(
    eq_low_cut: int = 80,
    eq_high_cut: int = 12000,
    deesser_threshold: float = -6.0,
    compression_ratio: float = 2.0,
    pitch_shift: int = 0,
) -> Optional[str]:
    """Build additional user-requested voice effects filter chain."""
    filters = []
    
    # Additional EQ adjustments beyond base (only if different from defaults)
    if eq_low_cut > 80:
        filters.append(f"highpass=f={eq_low_cut}")
    if eq_high_cut < 12000:
        filters.append(f"lowpass=f={eq_high_cut}")
    
    # De-esser (user-adjustable sibilance reduction)
    if deesser_threshold > -20 and deesser_threshold < 0:
        filters.append(f"highshelf=f=5000:g={deesser_threshold}")
    
    # Additional compression (if user wants more than base)
    if compression_ratio > 3.0:
        extra_ratio = compression_ratio - 2.0
        filters.append(f"acompressor=threshold=-18dB:ratio={extra_ratio}:attack=15:release=200:makeup=1.5dB")
    
    # Pitch shift
    if pitch_shift != 0:
        rate_change = 2 ** (pitch_shift / 12.0)
        filters.append(f"asetrate=44100*{rate_change},aresample=44100")
    
    return ",".join(filters) if filters else None


def _build_reverb_filter(
    reverb_mix: float = 25.0,
    reverb_decay: float = 1.5,
) -> Optional[str]:
    """Build reverb filter using aecho."""
    if reverb_mix <= 0:
        return None
    
    wet = reverb_mix / 100.0
    dry = 1.0 - wet
    
    delay1 = int(reverb_decay * 100)
    delay2 = int(reverb_decay * 170)
    delay3 = int(reverb_decay * 250)
    
    decay1 = min(0.9, 0.5 * (reverb_decay / 2.0))
    decay2 = min(0.9, 0.3 * (reverb_decay / 2.0))
    decay3 = min(0.9, 0.2 * (reverb_decay / 2.0))
    
    return f"aecho={dry}:{wet}:{delay1}|{delay2}|{delay3}:{decay1}|{decay2}|{decay3}"


def _apply_ffmpeg_filter(input_path: str, output_path: str, filter_chain: str) -> bool:
    """Apply ffmpeg audio filter chain."""
    try:
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", input_path,
            "-af", filter_chain,
            "-ar", "44100",
            "-ac", "2",
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[Mix] FFmpeg filter error: {e}")
        return False


def mix_audio(
    voice_path: str,
    music_path: str,
    output_filename: str,
    # Music params
    music_volume_db: float = -6.0,
    speech_entry_ms: int = 0,
    crossfade_ms: int = 2000,
    # Mix params (user-adjustable)
    reverb_mix: float = 25.0,
    reverb_decay: float = 1.5,
    compression_ratio: float = 2.0,
    deesser_threshold: float = -6.0,
    eq_low_cut: int = 80,
    eq_high_cut: int = 12000,
    pitch_shift: int = 0,
    normalization_lufs: float = -16.0,
    # Advanced (ReWire defaults)
    voice_target_dbfs: float = -13.0,
    music_target_dbfs: float = -17.5,
    final_peak_dbfs: float = -1.0,
    sync_mode: Literal["retime_voice_to_music", "retime_music_to_voice", "no_retime"] = "retime_voice_to_music",
) -> tuple[str, int]:
    """
    Mix voice and music tracks with full audio processing.
    
    Uses ReWire's battle-tested audio chain with user-adjustable parameters layered on top.
    Returns tuple of (output_path, duration_ms).
    """
    print(f"[Mix] Starting mix: voice={voice_path}, music={music_path}")
    print(f"[Mix] Params: reverb={reverb_mix}%, compression={compression_ratio}:1, pitch={pitch_shift}st")
    
    # ========== LOAD & NORMALIZE MUSIC ==========
    music = make_stereo(load_audio(music_path).set_frame_rate(44100))
    music = normalize_dbfs(music, music_target_dbfs)
    music = music.apply_gain(music_volume_db + 6)
    
    if len(music) <= 0:
        raise ValueError("Music track is empty or unreadable")

    # ========== MUSIC EQ (ReWire's proven values) ==========
    if _ffmpeg_has("equalizer"):
        tmp_m_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_m_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        music.export(tmp_m_in.name, format="wav")
        try:
            # ReWire's tested music EQ - reduce low rumble
            af = "equalizer=f=50:t=h:w=2:g=-3,equalizer=f=80:t=h:w=2:g=-2"
            subprocess.run(
                [FFMPEG_BIN, "-y", "-i", tmp_m_in.name, "-af", af, tmp_m_out.name],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            music = AudioSegment.from_file(tmp_m_out.name).set_frame_rate(44100).set_channels(2)
        except Exception:
            pass

    # ========== MUSIC COMPRESSION (ReWire's proven values) ==========
    if _ffmpeg_has("acompressor"):
        tmp_m2_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_m2_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        music.export(tmp_m2_in.name, format="wav")
        try:
            # ReWire's tested music compression
            af = "acompressor=threshold=-20dB:ratio=3:attack=18:release=280:makeup=2.5"
            subprocess.run(
                [FFMPEG_BIN, "-y", "-i", tmp_m2_in.name, "-af", af, tmp_m2_out.name],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            music = AudioSegment.from_file(tmp_m2_out.name).set_frame_rate(44100).set_channels(2)
        except Exception:
            pass

    # ========== LOAD & NORMALIZE VOICE ==========
    voice = make_stereo(load_audio(voice_path).set_frame_rate(44100))
    voice = normalize_dbfs(voice, voice_target_dbfs)
    
    if len(voice) <= 0:
        raise ValueError("Voice track is empty or unreadable")

    # ========== VOICE EQ (ReWire's proven base values) ==========
    if _ffmpeg_has("equalizer") or _ffmpeg_has("highpass"):
        tmp_v_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_v_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        voice.export(tmp_v_in.name, format="wav")
        try:
            # ReWire's tested voice EQ
            vf = "highpass=f=70,equalizer=f=150:t=h:w=1.5:g=2,equalizer=f=3800:t=h:w=2:g=-1.5"
            subprocess.run(
                [FFMPEG_BIN, "-y", "-i", tmp_v_in.name, "-af", vf, tmp_v_out.name],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            voice = AudioSegment.from_file(tmp_v_out.name).set_frame_rate(44100).set_channels(2)
        except Exception:
            pass

    # ========== USER VOICE EFFECTS (layered on top) ==========
    user_fx = _build_user_voice_effects(
        eq_low_cut=eq_low_cut,
        eq_high_cut=eq_high_cut,
        deesser_threshold=deesser_threshold,
        compression_ratio=compression_ratio,
        pitch_shift=pitch_shift,
    )
    if user_fx and _ffmpeg_available():
        tmp_ufx_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_ufx_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        voice.export(tmp_ufx_in.name, format="wav")
        if _apply_ffmpeg_filter(tmp_ufx_in.name, tmp_ufx_out.name, user_fx):
            voice = AudioSegment.from_file(tmp_ufx_out.name).set_frame_rate(44100).set_channels(2)

    # ========== REVERB (user-adjustable) ==========
    reverb_filter = _build_reverb_filter(reverb_mix, reverb_decay)
    if reverb_filter and _ffmpeg_available():
        tmp_rv_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_rv_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        voice.export(tmp_rv_in.name, format="wav")
        if _apply_ffmpeg_filter(tmp_rv_in.name, tmp_rv_out.name, reverb_filter):
            voice = AudioSegment.from_file(tmp_rv_out.name).set_frame_rate(44100).set_channels(2)

    # ========== CALCULATE TARGET DURATION (sample-accurate) ==========
    ch = music.channels
    sw = music.sample_width
    frame_bytes = ch * sw
    
    target_samples_per_ch = len(music.raw_data) // frame_bytes
    target_ms = int(round(1000 * target_samples_per_ch / music.frame_rate))

    if sync_mode == "retime_voice_to_music":
        tmp_v = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        voice.export(tmp_v.name, format="wav")
        v_wav = _retime_with_ffmpeg(tmp_v.name, target_ms)
        voice = AudioSegment.from_file(v_wav).set_frame_rate(44100).set_channels(ch)
    elif sync_mode == "retime_music_to_voice":
        voice_frames = len(voice.raw_data) // frame_bytes
        target_samples_per_ch = voice_frames
        target_ms = int(round(1000 * target_samples_per_ch / voice.frame_rate))
        
        tmp_m = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        music.export(tmp_m.name, format="wav")
        m_wav = _retime_with_ffmpeg(tmp_m.name, target_ms)
        music = AudioSegment.from_file(m_wav).set_frame_rate(44100).set_channels(ch)
    else:
        voice_frames = len(voice.raw_data) // frame_bytes
        target_samples_per_ch = max(voice_frames, len(music.raw_data) // frame_bytes)
        target_ms = int(round(1000 * target_samples_per_ch / 44100))

    # ========== SAMPLE-ACCURATE FITTING ==========
    voice = _hard_fit_samples(voice, target_samples_per_ch)
    music = _hard_fit_samples(music, target_samples_per_ch)

    # ========== SPEECH ENTRY DELAY ==========
    if speech_entry_ms > 0:
        silence = AudioSegment.silent(duration=speech_entry_ms, frame_rate=44100).set_channels(ch).set_sample_width(sw)
        voice = silence + voice
        voice = _hard_fit_samples(voice, target_samples_per_ch)

    # ========== DUCK MUSIC UNDER VOICE ==========
    music_ducked = _duck_music_to_voice(
        music, voice,
        floor_boost_db=3.0,
        max_duck_db=-1.5,
        attack_ms=180,
        release_ms=650,
        win_ms=60,
        lookahead_ms=500,
        gap_hold_ms=2600,
    )
    music_ducked = _hard_fit_samples(music_ducked, target_samples_per_ch)

    # ========== MIX TOGETHER ==========
    final_mix = music_ducked.overlay(voice)
    final_mix = _apply_peak_guard(final_mix, ceiling_dbfs=final_peak_dbfs)
    final_mix = _hard_fit_samples(final_mix, target_samples_per_ch)

    # ========== FADES ==========
    tail_ms = min(900, max(350, target_ms // 18))
    final_mix = final_mix.fade_out(tail_ms)
    
    if crossfade_ms > 0:
        final_mix = final_mix.fade_in(crossfade_ms)

    # ========== FINAL LOUDNESS NORMALIZATION ==========
    tmp_wav_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    final_mix.export(tmp_wav_in.name, format="wav")

    tmp_wav_polished = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    if _ffmpeg_has("loudnorm"):
        af = f"loudnorm=I={normalization_lufs}:TP=-1.0:LRA=11:linear=true"
    else:
        af = "dynaudnorm=f=125:s=12,volume=-0.6dB"

    subprocess.run(
        [FFMPEG_BIN, "-y", "-i", tmp_wav_in.name, "-af", af, "-ar", "44100", "-ac", str(ch), tmp_wav_polished.name],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    polished = AudioSegment.from_file(tmp_wav_polished.name).set_channels(ch).set_frame_rate(44100)
    polished = _hard_fit_samples(polished, target_samples_per_ch)

    # ========== EXPORT FINAL MP3 ==========
    tmp_wav_exact = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    polished.export(tmp_wav_exact.name, format="wav")

    output_path = OUTPUTS_DIR / output_filename
    t_sec = f"{target_samples_per_ch / 44100.0:.6f}"
    
    subprocess.run(
        [
            FFMPEG_BIN, "-y",
            "-i", tmp_wav_exact.name,
            "-t", t_sec,
            "-shortest",
            "-ar", "44100",
            "-ac", str(ch),
            "-codec:a", "libmp3lame",
            "-b:a", "256k",
            str(output_path),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # ========== VERIFY OUTPUT ==========
    out_frames, out_sr, out_ch = _decode_samples(output_path)
    SAMPLE_TOL = 64

    ok_by_samples = (
        out_sr == 44100
        and out_ch == ch
        and abs(out_frames - target_samples_per_ch) <= SAMPLE_TOL
    )

    if not ok_by_samples:
        target_ms_exact = int(round(1000 * target_samples_per_ch / 44100.0))
        actual_ms_exact = int(round(1000 * out_frames / 44100.0))
        MS_TOL = 3
        if abs(actual_ms_exact - target_ms_exact) > MS_TOL:
            print(f"[Mix] Warning: Length drift {actual_ms_exact}ms vs {target_ms_exact}ms")

    duration_ms = int(round(1000 * target_samples_per_ch / 44100.0))
    print(f"[Mix] Complete: {output_path}, duration={duration_ms}ms")
    return str(output_path), duration_ms


def mix_voice_only(
    voice_path: str,
    output_filename: str,
    # Mix params
    reverb_mix: float = 25.0,
    reverb_decay: float = 1.5,
    compression_ratio: float = 2.0,
    deesser_threshold: float = -6.0,
    eq_low_cut: int = 80,
    eq_high_cut: int = 12000,
    pitch_shift: int = 0,
    normalization_lufs: float = -16.0,
    voice_target_dbfs: float = -13.0,
) -> tuple[str, int]:
    """
    Process voice-only (no music) with full audio processing.
    
    Returns tuple of (output_path, duration_ms).
    """
    print(f"[Mix] Voice-only processing: {voice_path}")
    
    voice = make_stereo(load_audio(voice_path).set_frame_rate(44100))
    voice = normalize_dbfs(voice, voice_target_dbfs)
    
    # Base voice EQ (ReWire's values)
    if _ffmpeg_has("equalizer") or _ffmpeg_has("highpass"):
        tmp_v_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_v_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        voice.export(tmp_v_in.name, format="wav")
        try:
            vf = "highpass=f=70,equalizer=f=150:t=h:w=1.5:g=2,equalizer=f=3800:t=h:w=2:g=-1.5"
            subprocess.run(
                [FFMPEG_BIN, "-y", "-i", tmp_v_in.name, "-af", vf, tmp_v_out.name],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            voice = AudioSegment.from_file(tmp_v_out.name).set_frame_rate(44100).set_channels(2)
        except Exception:
            pass

    # User voice effects
    user_fx = _build_user_voice_effects(
        eq_low_cut=eq_low_cut,
        eq_high_cut=eq_high_cut,
        deesser_threshold=deesser_threshold,
        compression_ratio=compression_ratio,
        pitch_shift=pitch_shift,
    )
    if user_fx and _ffmpeg_available():
        tmp_ufx_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_ufx_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        voice.export(tmp_ufx_in.name, format="wav")
        if _apply_ffmpeg_filter(tmp_ufx_in.name, tmp_ufx_out.name, user_fx):
            voice = AudioSegment.from_file(tmp_ufx_out.name).set_frame_rate(44100).set_channels(2)

    # Reverb
    reverb_filter = _build_reverb_filter(reverb_mix, reverb_decay)
    if reverb_filter and _ffmpeg_available():
        tmp_rv_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_rv_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        voice.export(tmp_rv_in.name, format="wav")
        if _apply_ffmpeg_filter(tmp_rv_in.name, tmp_rv_out.name, reverb_filter):
            voice = AudioSegment.from_file(tmp_rv_out.name).set_frame_rate(44100).set_channels(2)

    # Fade out
    tail_ms = min(500, len(voice) // 10)
    voice = voice.fade_out(tail_ms)
    
    # Final loudness normalization
    tmp_wav_in = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    voice.export(tmp_wav_in.name, format="wav")

    tmp_wav_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    
    if _ffmpeg_has("loudnorm"):
        loudnorm_filter = f"loudnorm=I={normalization_lufs}:TP=-1.0:LRA=11:linear=true"
    else:
        loudnorm_filter = "dynaudnorm=f=125:s=12"

    subprocess.run(
        [FFMPEG_BIN, "-y", "-i", tmp_wav_in.name, "-af", loudnorm_filter, "-ar", "44100", "-ac", "2", tmp_wav_out.name],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    
    output_path = OUTPUTS_DIR / output_filename
    subprocess.run(
        [
            FFMPEG_BIN, "-y",
            "-i", tmp_wav_out.name,
            "-codec:a", "libmp3lame",
            "-b:a", "256k",
            str(output_path),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    
    duration_ms = len(voice)
    print(f"[Mix] Voice-only complete: {output_path}, duration={duration_ms}ms")
    return str(output_path), duration_ms