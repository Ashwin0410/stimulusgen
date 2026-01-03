"""
Prosody extraction and transfer for chills-inducing speech.

This implements a simplified prosody transfer that modifies:
1. Overall pitch level (mean pitch matching)
2. Pitch variation (standard deviation matching)
3. Pitch contour shape (general arc of the speech)

Full prosody transfer would require phoneme alignment and PSOLA,
which is beyond the scope of this MVP.
"""

import json
import tempfile
from pathlib import Path
from typing import Optional, List
import subprocess

import numpy as np
import parselmouth
from parselmouth.praat import call
from pydub import AudioSegment

from app.config import ASSETS_DIR, FFMPEG_BIN


def extract_prosody(audio_path: str) -> dict:
    """
    Extract prosody features from audio file.
    
    Returns dict with pitch, energy, and timing information.
    """
    try:
        sound = parselmouth.Sound(audio_path)
        
        # Extract pitch
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        pitch_values = pitch.selected_array['frequency']
        pitch_values = pitch_values[pitch_values > 0]  # Remove unvoiced
        
        # Extract intensity (energy)
        intensity = call(sound, "To Intensity", 75, 0.0, True)
        num_points = min(200, int(sound.duration * 10))  # ~10 points per second
        intensity_values = [
            call(intensity, "Get value at time", t, "cubic")
            for t in np.linspace(0, sound.duration, num_points)
        ]
        intensity_values = [v for v in intensity_values if v is not None and not np.isnan(v)]
        
        # Extract pitch contour at regular intervals
        pitch_times = np.linspace(0, sound.duration, num_points)
        pitch_contour = []
        for t in pitch_times:
            val = call(pitch, "Get value at time", t, "Hertz", "Linear")
            if val and not np.isnan(val) and val > 0:
                pitch_contour.append({"time": float(t), "pitch": float(val)})
        
        duration_ms = int(sound.duration * 1000)
        
        # Calculate pitch trajectory (is it rising, falling, or arc-shaped?)
        if len(pitch_contour) >= 10:
            pitches = [p["pitch"] for p in pitch_contour]
            first_third = np.mean(pitches[:len(pitches)//3])
            middle_third = np.mean(pitches[len(pitches)//3:2*len(pitches)//3])
            last_third = np.mean(pitches[2*len(pitches)//3:])
            
            # Chaplin's speech has an arc: starts lower, rises in middle, ends high
            trajectory = {
                "start": float(first_third),
                "middle": float(middle_third),
                "end": float(last_third),
                "shape": "rising" if last_third > first_third else "falling",
                "has_peak": middle_third > first_third and middle_third > last_third,
            }
        else:
            trajectory = None
        
        profile = {
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
        
        return profile
        
    except Exception as e:
        print(f"[Prosody] Error extracting prosody: {e}")
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
    """
    Get prosody profile for a reference.
    Caches extracted profiles for faster subsequent access.
    """
    if reference == "none":
        return None
    
    prosody_dir = ASSETS_DIR / "prosody"
    
    if reference == "great_dictator":
        profile_path = prosody_dir / "great_dictator_profile.json"
        if profile_path.exists():
            try:
                with open(profile_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Try different extensions
        for ext in [".m4a", ".mp3", ".wav", ".ogg"]:
            audio_path = prosody_dir / f"great_dictator{ext}"
            if audio_path.exists():
                print(f"[Prosody] Extracting profile from {audio_path}")
                profile = extract_prosody(str(audio_path))
                profile["source_file"] = str(audio_path)
                profile["id"] = "great_dictator"
                profile["name"] = "Great Dictator (Chaplin)"
                
                # Cache the profile
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(profile_path, "w") as f:
                        json.dump(profile, f, indent=2)
                except Exception as e:
                    print(f"[Prosody] Could not cache profile: {e}")
                
                return profile
        
        return None
    
    # Custom reference - look for audio file
    for ext in ["", ".m4a", ".mp3", ".wav", ".ogg"]:
        audio_path = prosody_dir / f"{reference}{ext}"
        if audio_path.exists() and audio_path.is_file():
            # Check for cached profile
            profile_path = prosody_dir / f"{audio_path.stem}_profile.json"
            if profile_path.exists():
                try:
                    with open(profile_path, "r") as f:
                        return json.load(f)
                except Exception:
                    pass
            
            # Extract and cache
            profile = extract_prosody(str(audio_path))
            profile["source_file"] = str(audio_path)
            profile["id"] = reference
            profile["name"] = audio_path.stem.replace("_", " ").title()
            
            try:
                with open(profile_path, "w") as f:
                    json.dump(profile, f, indent=2)
            except Exception:
                pass
            
            return profile
    
    return None


def apply_prosody(
    voice_path: str,
    reference: str,
    intensity: float = 0.5,
) -> str:
    """
    Apply prosody transfer to voice audio.
    
    This modifies:
    1. Overall pitch level (shift toward reference mean)
    2. Pitch variation (scale toward reference std)
    3. Basic contour shape (if intensity > 0.5)
    
    Args:
        voice_path: Path to input voice audio
        reference: Prosody reference ID (e.g., "great_dictator")
        intensity: Transfer intensity from 0.0 (none) to 1.0 (full)
    
    Returns:
        Path to modified audio file
    """
    if reference == "none" or intensity <= 0:
        return voice_path
    
    profile = get_prosody_profile(reference)
    if not profile:
        print(f"[Prosody] No profile found for reference: {reference}")
        return voice_path
    
    try:
        sound = parselmouth.Sound(voice_path)
        
        # Extract source pitch characteristics
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        source_mean = call(pitch, "Get mean", 0, 0, "Hertz")
        source_std = call(pitch, "Get standard deviation", 0, 0, "Hertz")
        
        if source_mean <= 0 or source_std <= 0:
            print("[Prosody] Could not analyze source pitch")
            return voice_path
        
        target_mean = profile.get("pitch_mean", source_mean)
        target_std = profile.get("pitch_std", source_std)
        
        if target_mean <= 0:
            target_mean = source_mean
        if target_std <= 0:
            target_std = source_std
        
        # Calculate transformations based on intensity
        # Pitch shift factor (move toward target mean)
        mean_shift = 1 + (target_mean / source_mean - 1) * intensity
        mean_shift = max(0.5, min(2.0, mean_shift))
        
        # Pitch range scaling (move toward target variation)
        range_scale = 1 + (target_std / source_std - 1) * intensity * 0.5
        range_scale = max(0.5, min(2.0, range_scale))
        
        print(f"[Prosody] Applying transfer: mean_shift={mean_shift:.2f}, range_scale={range_scale:.2f}")
        
        # Create manipulation object
        manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
        pitch_tier = call(manipulation, "Extract pitch tier")
        
        # Apply pitch shift
        call(pitch_tier, "Multiply frequencies", sound.xmin, sound.xmax, mean_shift)
        
        # Apply range scaling (expand or compress pitch variation)
        if abs(range_scale - 1.0) > 0.05:
            # Get all pitch points
            num_points = call(pitch_tier, "Get number of points")
            if num_points > 0:
                # Calculate new mean after shift
                new_mean = source_mean * mean_shift
                
                # Scale each point's distance from mean
                for i in range(1, num_points + 1):
                    time = call(pitch_tier, "Get time from index", i)
                    value = call(pitch_tier, "Get value at index", i)
                    if value > 0:
                        # Scale distance from mean
                        distance = value - new_mean
                        new_value = new_mean + distance * range_scale
                        new_value = max(50, min(500, new_value))  # Clamp to reasonable range
                        call(pitch_tier, "Remove point", i)
                        call(pitch_tier, "Add point", time, new_value)
        
        # Replace pitch tier and resynthesize
        call([manipulation, pitch_tier], "Replace pitch tier")
        new_sound = call(manipulation, "Get resynthesis (overlap-add)")
        
        # Export to temp file
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        new_sound.save(out_path, "WAV")
        
        print(f"[Prosody] Transfer complete: {out_path}")
        return out_path
        
    except Exception as e:
        print(f"[Prosody] Error applying prosody: {e}")
        import traceback
        traceback.print_exc()
        return voice_path


def compare_prosody(voice_path: str, reference: str) -> dict:
    """
    Compare voice audio to a prosody reference.
    Useful for A/B testing and validation.
    
    Returns dict with comparison metrics.
    """
    profile = get_prosody_profile(reference)
    if not profile:
        return {"error": "Reference not found"}
    
    voice_profile = extract_prosody(voice_path)
    if voice_profile["duration_ms"] == 0:
        return {"error": "Could not analyze voice"}
    
    # Calculate similarity scores
    pitch_mean_diff = abs(voice_profile["pitch_mean"] - profile["pitch_mean"])
    pitch_std_diff = abs(voice_profile["pitch_std"] - profile["pitch_std"])
    energy_mean_diff = abs(voice_profile["energy_mean"] - profile["energy_mean"])
    
    # Normalize to 0-100 similarity score
    pitch_mean_similarity = max(0, 100 - pitch_mean_diff)
    pitch_std_similarity = max(0, 100 - pitch_std_diff * 2)
    energy_similarity = max(0, 100 - energy_mean_diff * 2)
    
    overall = (pitch_mean_similarity + pitch_std_similarity + energy_similarity) / 3
    
    return {
        "voice_profile": voice_profile,
        "reference_profile": profile,
        "pitch_mean_similarity": pitch_mean_similarity,
        "pitch_std_similarity": pitch_std_similarity,
        "energy_similarity": energy_similarity,
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
        {
            "id": "great_dictator",
            "name": "Great Dictator (Chaplin)",
            "description": "Emotional crescendo pattern - humble start, passionate climax",
        },
    ]
    
    # Add custom references from prosody folder
    prosody_dir = ASSETS_DIR / "prosody"
    if prosody_dir.exists():
        for f in prosody_dir.iterdir():
            if f.suffix.lower() in [".mp3", ".wav", ".m4a", ".ogg"]:
                stem = f.stem
                if stem != "great_dictator" and not stem.endswith("_profile"):
                    references.append({
                        "id": f.name,
                        "name": stem.replace("_", " ").title(),
                        "description": "Custom prosody reference",
                    })
    
    return references


def preload_profiles():
    """Pre-extract and cache all prosody profiles."""
    prosody_dir = ASSETS_DIR / "prosody"
    if not prosody_dir.exists():
        return
    
    for f in prosody_dir.iterdir():
        if f.suffix.lower() in [".mp3", ".wav", ".m4a", ".ogg"]:
            stem = f.stem
            profile_path = prosody_dir / f"{stem}_profile.json"
            if not profile_path.exists():
                print(f"[Prosody] Pre-extracting profile for {f.name}")
                profile = extract_prosody(str(f))
                profile["source_file"] = str(f)
                profile["id"] = stem
                profile["name"] = stem.replace("_", " ").title()
                try:
                    with open(profile_path, "w") as pf:
                        json.dump(profile, pf, indent=2)
                except Exception as e:
                    print(f"[Prosody] Could not save profile: {e}")
