"""
Prosody extraction and transfer for chills-inducing speech.
Gracefully handles missing praat-parselmouth library.
"""

import json
from pathlib import Path
from typing import Optional

from app.config import ASSETS_DIR

# Try to import parselmouth, but don't fail if it's not available
try:
    import parselmouth
    from parselmouth.praat import call
    import numpy as np
    PARSELMOUTH_AVAILABLE = True
except ImportError:
    PARSELMOUTH_AVAILABLE = False
    print("[Prosody] praat-parselmouth not available - prosody transfer disabled")


def extract_prosody(audio_path: str) -> dict:
    """Extract prosody features from audio file."""
    if not PARSELMOUTH_AVAILABLE:
        return _empty_profile()
    
    try:
        sound = parselmouth.Sound(audio_path)
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        pitch_values = pitch.selected_array['frequency']
        pitch_values = pitch_values[pitch_values > 0]
        
        intensity = call(sound, "To Intensity", 75, 0.0, True)
        num_points = min(200, int(sound.duration * 10))
        intensity_values = [
            call(intensity, "Get value at time", t, "cubic")
            for t in np.linspace(0, sound.duration, num_points)
        ]
        intensity_values = [v for v in intensity_values if v is not None and not np.isnan(v)]
        
        pitch_times = np.linspace(0, sound.duration, num_points)
        pitch_contour = []
        for t in pitch_times:
            val = call(pitch, "Get value at time", t, "Hertz", "Linear")
            if val and not np.isnan(val) and val > 0:
                pitch_contour.append({"time": float(t), "pitch": float(val)})
        
        duration_ms = int(sound.duration * 1000)
        
        trajectory = None
        if len(pitch_contour) >= 10:
            pitches = [p["pitch"] for p in pitch_contour]
            first_third = np.mean(pitches[:len(pitches)//3])
            middle_third = np.mean(pitches[len(pitches)//3:2*len(pitches)//3])
            last_third = np.mean(pitches[2*len(pitches)//3:])
            trajectory = {
                "start": float(first_third),
                "middle": float(middle_third),
                "end": float(last_third),
                "shape": "rising" if last_third > first_third else "falling",
                "has_peak": middle_third > first_third and middle_third > last_third,
            }
        
        return {
            "duration_ms": duration_ms,
            "pitch_mean": float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0,
            "pitch_std": float(np.std(pitch_values)) if len(pitch_values) > 0 else 0,
            "pitch_min": float(np.min(pitch_values)) if len(pitch_values) > 0 else 0,
            "pitch_max": float(np.max(pitch_values)) if len(pitch_values) > 0 else 0,
            "pitch_range": float(np.max(pitch_values) - np.min(pitch_values)) if len(pitch_values) > 0 else 0,
            "energy_mean": float(np.mean(intensity_values)) if len(intensity_values) > 0 else 0,
            "energy_std": float(np.std(intensity_values)) if len(intensity_values) > 0 else 0,
            "energy_min": float(np.min(intensity_values)) if len(intensity_values) > 0 else 0,
            "energy_max": float(np.max(intensity_values)) if len(intensity_values) > 0 else 0,
            "pitch_contour": [p["pitch"] for p in pitch_contour][:100],
            "energy_contour": intensity_values[:100],
            "trajectory": trajectory,
            "num_voiced_frames": len(pitch_values),
            "voiced_ratio": len(pitch_values) / max(1, num_points),
        }
    except Exception as e:
        print(f"[Prosody] Error extracting prosody: {e}")
        return _empty_profile()


def _empty_profile() -> dict:
    """Return empty prosody profile."""
    return {
        "duration_ms": 0,
        "pitch_mean": 0,
        "pitch_std": 0,
        "pitch_min": 0,
        "pitch_max": 0,
        "pitch_range": 0,
        "energy_mean": 0,
        "energy_std": 0,
        "energy_min": 0,
        "energy_max": 0,
        "pitch_contour": [],
        "energy_contour": [],
        "trajectory": None,
        "num_voiced_frames": 0,
        "voiced_ratio": 0,
    }


def get_prosody_profile(reference: str) -> Optional[dict]:
    """Get prosody profile for a reference."""
    if reference == "none":
        return None
    
    prosody_dir = ASSETS_DIR / "prosody"
    
    # Try to load cached profile first
    profile_path = prosody_dir / f"{reference}_profile.json"
    if profile_path.exists():
        try:
            with open(profile_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    
    # If parselmouth not available, can't extract new profiles
    if not PARSELMOUTH_AVAILABLE:
        return None
    
    # Try to extract from audio file
    for ext in [".m4a", ".mp3", ".wav", ".ogg"]:
        audio_path = prosody_dir / f"{reference}{ext}"
        if audio_path.exists():
            profile = extract_prosody(str(audio_path))
            profile["source_file"] = str(audio_path)
            profile["id"] = reference
            profile["name"] = reference.replace("_", " ").title()
            
            try:
                with open(profile_path, "w") as f:
                    json.dump(profile, f, indent=2)
            except Exception:
                pass
            
            return profile
    
    return None


def apply_prosody(voice_path: str, reference: str, intensity: float = 0.5) -> str:
    """Apply prosody transfer to voice audio."""
    if reference == "none" or intensity <= 0:
        return voice_path
    
    if not PARSELMOUTH_AVAILABLE:
        print("[Prosody] Skipping - praat-parselmouth not available")
        return voice_path
    
    profile = get_prosody_profile(reference)
    if not profile:
        return voice_path
    
    try:
        import tempfile
        sound = parselmouth.Sound(voice_path)
        
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        source_mean = call(pitch, "Get mean", 0, 0, "Hertz")
        source_std = call(pitch, "Get standard deviation", 0, 0, "Hertz")
        
        if source_mean <= 0 or source_std <= 0:
            return voice_path
        
        target_mean = profile.get("pitch_mean", source_mean)
        target_std = profile.get("pitch_std", source_std)
        
        if target_mean <= 0:
            target_mean = source_mean
        if target_std <= 0:
            target_std = source_std
        
        mean_shift = 1 + (target_mean / source_mean - 1) * intensity
        mean_shift = max(0.5, min(2.0, mean_shift))
        
        range_scale = 1 + (target_std / source_std - 1) * intensity * 0.5
        range_scale = max(0.5, min(2.0, range_scale))
        
        manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
        pitch_tier = call(manipulation, "Extract pitch tier")
        call(pitch_tier, "Multiply frequencies", sound.xmin, sound.xmax, mean_shift)
        call([manipulation, pitch_tier], "Replace pitch tier")
        new_sound = call(manipulation, "Get resynthesis (overlap-add)")
        
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        new_sound.save(out_path, "WAV")
        
        return out_path
    except Exception as e:
        print(f"[Prosody] Error: {e}")
        return voice_path


def compare_prosody(voice_path: str, reference: str) -> dict:
    """Compare voice audio to a prosody reference."""
    if not PARSELMOUTH_AVAILABLE:
        return {"error": "Prosody analysis not available"}
    
    profile = get_prosody_profile(reference)
    if not profile:
        return {"error": "Reference not found"}
    
    voice_profile = extract_prosody(voice_path)
    if voice_profile["duration_ms"] == 0:
        return {"error": "Could not analyze voice"}
    
    pitch_mean_diff = abs(voice_profile["pitch_mean"] - profile["pitch_mean"])
    pitch_std_diff = abs(voice_profile["pitch_std"] - profile["pitch_std"])
    energy_mean_diff = abs(voice_profile["energy_mean"] - profile["energy_mean"])
    
    pitch_mean_similarity = max(0, 100 - pitch_mean_diff)
    pitch_std_similarity = max(0, 100 - pitch_std_diff * 2)
    energy_similarity = max(0, 100 - energy_mean_diff * 2)
    
    overall = (pitch_mean_similarity + pitch_std_similarity + energy_similarity) / 3
    
    return {
        "voice_profile": voice_profile,
        "reference_profile": profile,
        "overall_similarity": overall,
    }


def list_prosody_references() -> list:
    """List available prosody references."""
    references = [
        {
            "id": "none",
            "name": "None",
            "description": "No prosody transfer",
        },
    ]
    
    # Only show Great Dictator if profile exists (pre-cached)
    prosody_dir = ASSETS_DIR / "prosody"
    profile_path = prosody_dir / "great_dictator_profile.json"
    if profile_path.exists():
        references.append({
            "id": "great_dictator",
            "name": "Great Dictator (Chaplin)",
            "description": "Emotional crescendo pattern" + ("" if PARSELMOUTH_AVAILABLE else " (disabled - library not available)"),
        })
    
    return references


def preload_profiles():
    """Pre-extract and cache all prosody profiles."""
    if not PARSELMOUTH_AVAILABLE:
        print("[Prosody] Skipping preload - praat-parselmouth not available")
        return
    
    prosody_dir = ASSETS_DIR / "prosody"
    if not prosody_dir.exists():
        return
    
    for f in prosody_dir.iterdir():
        if f.suffix.lower() in [".mp3", ".wav", ".m4a", ".ogg"]:
            stem = f.stem
            profile_path = prosody_dir / f"{stem}_profile.json"
            if not profile_path.exists():
                profile = extract_prosody(str(f))
                profile["id"] = stem
                profile["name"] = stem.replace("_", " ").title()
                try:
                    with open(profile_path, "w") as pf:
                        json.dump(profile, pf, indent=2)
                except Exception:
                    pass
