import subprocess
import tempfile
from pathlib import Path
from pydub import AudioSegment

from app.config import FFMPEG_BIN, FFPROBE_BIN


def load_audio(path: str | Path) -> AudioSegment:
    """Load audio file and return as AudioSegment."""
    return AudioSegment.from_file(str(path))


def normalize_dbfs(seg: AudioSegment, target_dbfs: float = -16.0) -> AudioSegment:
    """Normalize audio to target dBFS level."""
    change = target_dbfs - seg.dBFS
    return seg.apply_gain(change)


def make_stereo(seg: AudioSegment) -> AudioSegment:
    """Convert mono to stereo if needed."""
    if seg.channels == 1:
        return seg.set_channels(2)
    return seg


def export_mp3(seg: AudioSegment, out_path: str | Path, bitrate: str = "192k") -> None:
    """Export AudioSegment as MP3."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    seg.export(str(out_path), format="mp3", bitrate=bitrate)


def get_duration_ms(seg: AudioSegment) -> int:
    """Get duration in milliseconds."""
    return len(seg)


def get_file_duration_ms(path: str | Path) -> int:
    """Get duration of audio file in milliseconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                FFPROBE_BIN,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        duration_sec = float(result.stdout.strip())
        return int(duration_sec * 1000)
    except Exception:
        # Fallback to pydub
        seg = AudioSegment.from_file(str(path))
        return len(seg)


def apply_fade(seg: AudioSegment, fade_in_ms: int = 0, fade_out_ms: int = 0) -> AudioSegment:
    """Apply fade in and/or fade out to audio."""
    if fade_in_ms > 0:
        seg = seg.fade_in(fade_in_ms)
    if fade_out_ms > 0:
        seg = seg.fade_out(fade_out_ms)
    return seg


def trim_audio(seg: AudioSegment, start_ms: int = 0, end_ms: int = None) -> AudioSegment:
    """Trim audio to specified start and end times."""
    if end_ms is None:
        return seg[start_ms:]
    return seg[start_ms:end_ms]


def loop_to_length(seg: AudioSegment, target_ms: int) -> AudioSegment:
    """Loop audio to reach target length."""
    if len(seg) >= target_ms:
        return seg[:target_ms]
    
    loops_needed = (target_ms // len(seg)) + 1
    looped = seg * loops_needed
    return looped[:target_ms]


def overlay_audio(base: AudioSegment, overlay: AudioSegment, position_ms: int = 0) -> AudioSegment:
    """Overlay one audio on top of another at specified position."""
    return base.overlay(overlay, position=position_ms)


def adjust_volume(seg: AudioSegment, db_change: float) -> AudioSegment:
    """Adjust volume by specified dB amount."""
    return seg.apply_gain(db_change)


def convert_to_wav(input_path: str | Path, output_path: str | Path = None) -> str:
    """Convert audio file to WAV format."""
    if output_path is None:
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    
    seg = AudioSegment.from_file(str(input_path))
    seg.export(str(output_path), format="wav")
    return str(output_path)


def get_sample_rate(seg: AudioSegment) -> int:
    """Get sample rate of audio."""
    return seg.frame_rate


def set_sample_rate(seg: AudioSegment, sample_rate: int = 44100) -> AudioSegment:
    """Set sample rate of audio."""
    return seg.set_frame_rate(sample_rate)