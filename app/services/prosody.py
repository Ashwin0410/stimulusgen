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
import os
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import subprocess

import numpy as np
import parselmouth
from parselmouth.praat import call
from pydub import AudioSegment

from app.config import ASSETS_DIR, FFMPEG_BIN


def _convert_to_wav(audio_path: str) -> str:
    """
    Convert audio file to WAV format for Parselmouth compatibility.
    
    Parselmouth (Praat) cannot read .m4a files directly.
    This function converts any audio format to WAV using FFmpeg.
    
    Args:
        audio_path: Path to input audio file
        
    Returns:
        Path to WAV file (either original if already WAV, or converted temp file)
    """
    # If already WAV, return as-is
    if audio_path.lower().endswith('.wav'):
        return audio_path
    
    print(f"[Prosody] Converting {audio_path} to WAV for Parselmouth compatibility...")
    
    try:
        # Create temp WAV file
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        
        # Use FFmpeg to convert
        ffmpeg = FFMPEG_BIN or "ffmpeg"
        cmd = [
            ffmpeg,
            "-i", audio_path,
            "-ar", "44100",  # Sample rate
            "-ac", "1",       # Mono
            "-y",             # Overwrite
            temp_wav
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"[Prosody] FFmpeg conversion failed: {result.stderr}")
            return audio_path  # Return original, let caller handle the error
        
        if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
            print(f"[Prosody] Converted to WAV: {temp_wav}")
            return temp_wav
        else:
            print(f"[Prosody] Conversion produced empty file")
            return audio_path
            
    except Exception as e:
        print(f"[Prosody] Conversion error: {e}")
        return audio_path


def _is_valid_profile(profile: dict) -> bool:
    """
    Check if a prosody profile has valid (non-zero) values.
    
    A profile with pitch_mean=0 or pitch_std=0 is invalid and 
    indicates extraction failed.
    
    Args:
        profile: Prosody profile dictionary
        
    Returns:
        True if profile is valid, False otherwise
    """
    if not profile:
        return False
    
    pitch_mean = profile.get("pitch_mean", 0)
    pitch_std = profile.get("pitch_std", 0)
    
    # Valid speech typically has pitch_mean between 75-400 Hz
    # and pitch_std > 0 (some variation)
    if pitch_mean <= 0 or pitch_std <= 0:
        return False
    
    return True


def extract_prosody(audio_path: str) -> dict:
    """
    Extract prosody features from audio file.
    
    Returns dict with pitch, energy, and timing information.
    """
    # Track if we created a temp file for cleanup
    temp_wav_path = None
    
    try:
        print(f"[Prosody] Extracting prosody from: {audio_path}")
        
        # Convert to WAV if needed (Parselmouth can't read .m4a)
        wav_path = _convert_to_wav(audio_path)
        if wav_path != audio_path:
            temp_wav_path = wav_path  # Mark for cleanup
        
        sound = parselmouth.Sound(wav_path)
        print(f"[Prosody] Sound loaded: duration={sound.duration:.2f}s, sample_rate={sound.sampling_frequency}")
        
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
                "has_peak": bool(middle_third > first_third and middle_third > last_third),
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
        
        print(f"[Prosody] Extraction complete: pitch_mean={profile['pitch_mean']:.1f}Hz, pitch_std={profile['pitch_std']:.1f}Hz")
        return profile
        
    except Exception as e:
        print(f"[Prosody] Error extracting prosody: {e}")
        import traceback
        traceback.print_exc()
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
    finally:
        # Cleanup temp WAV file if we created one
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.unlink(temp_wav_path)
                print(f"[Prosody] Cleaned up temp WAV: {temp_wav_path}")
            except Exception:
                pass


def get_prosody_profile(reference: str) -> Optional[dict]:
    """
    Get prosody profile for a reference.
    Caches extracted profiles for faster subsequent access.
    """
    if reference == "none":
        print(f"[Prosody] Reference is 'none', skipping profile load")
        return None
    
    prosody_dir = ASSETS_DIR / "prosody"
    print(f"[Prosody] Looking for reference '{reference}' in {prosody_dir}")
    
    # Check if prosody directory exists
    if not prosody_dir.exists():
        print(f"[Prosody] WARNING: Prosody directory does not exist: {prosody_dir}")
        return None
    
    if reference == "great_dictator":
        profile_path = prosody_dir / "great_dictator_profile.json"
        
        # Try to load cached profile
        if profile_path.exists():
            try:
                print(f"[Prosody] Loading cached profile from {profile_path}")
                with open(profile_path, "r") as f:
                    profile = json.load(f)
                print(f"[Prosody] Loaded profile: pitch_mean={profile.get('pitch_mean', 0):.1f}Hz, pitch_std={profile.get('pitch_std', 0):.1f}Hz")
                
                # VALIDATION: Check if profile has valid (non-zero) values
                if _is_valid_profile(profile):
                    return profile
                else:
                    print(f"[Prosody] WARNING: Cached profile has invalid/zero values! Will re-extract.")
                    # Delete the invalid cache file
                    try:
                        os.unlink(profile_path)
                        print(f"[Prosody] Deleted invalid cache: {profile_path}")
                    except Exception as e:
                        print(f"[Prosody] Could not delete invalid cache: {e}")
                    
            except Exception as e:
                print(f"[Prosody] Error loading cached profile: {e}")
        
        # Try different extensions
        for ext in [".m4a", ".mp3", ".wav", ".ogg"]:
            audio_path = prosody_dir / f"great_dictator{ext}"
            print(f"[Prosody] Checking for audio file: {audio_path}")
            if audio_path.exists():
                print(f"[Prosody] Found audio file, extracting profile from {audio_path}")
                profile = extract_prosody(str(audio_path))
                
                # Verify extraction succeeded
                if not _is_valid_profile(profile):
                    print(f"[Prosody] WARNING: Extraction produced invalid profile (pitch_mean={profile.get('pitch_mean', 0):.1f}Hz)")
                    continue  # Try next extension
                
                profile["source_file"] = str(audio_path)
                profile["id"] = "great_dictator"
                profile["name"] = "Great Dictator (Chaplin)"
                
                # Cache the profile
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(profile_path, "w") as f:
                        json.dump(profile, f, indent=2)
                    print(f"[Prosody] Cached profile to {profile_path}")
                except Exception as e:
                    print(f"[Prosody] Could not cache profile: {e}")
                
                return profile
        
        print(f"[Prosody] WARNING: No audio file found for great_dictator in {prosody_dir}")
        # List what files ARE in the directory
        try:
            files = list(prosody_dir.iterdir())
            print(f"[Prosody] Files in prosody directory: {[f.name for f in files]}")
        except Exception as e:
            print(f"[Prosody] Could not list directory: {e}")
        
        return None
    
    # Custom reference - look for audio file
    for ext in ["", ".m4a", ".mp3", ".wav", ".ogg"]:
        audio_path = prosody_dir / f"{reference}{ext}"
        if audio_path.exists() and audio_path.is_file():
            # Check for cached profile
            profile_path = prosody_dir / f"{audio_path.stem}_profile.json"
            if profile_path.exists():
                try:
                    print(f"[Prosody] Loading cached profile from {profile_path}")
                    with open(profile_path, "r") as f:
                        profile = json.load(f)
                    
                    # VALIDATION: Check if profile has valid values
                    if _is_valid_profile(profile):
                        return profile
                    else:
                        print(f"[Prosody] WARNING: Cached profile has invalid/zero values! Will re-extract.")
                        try:
                            os.unlink(profile_path)
                            print(f"[Prosody] Deleted invalid cache: {profile_path}")
                        except Exception:
                            pass
                except Exception:
                    pass
            
            # Extract and cache
            print(f"[Prosody] Extracting profile from {audio_path}")
            profile = extract_prosody(str(audio_path))
            
            # Only cache if valid
            if _is_valid_profile(profile):
                profile["source_file"] = str(audio_path)
                profile["id"] = reference
                profile["name"] = audio_path.stem.replace("_", " ").title()
                
                try:
                    with open(profile_path, "w") as f:
                        json.dump(profile, f, indent=2)
                    print(f"[Prosody] Cached profile to {profile_path}")
                except Exception:
                    pass
                
                return profile
            else:
                print(f"[Prosody] WARNING: Extraction failed for {audio_path}")
    
    print(f"[Prosody] WARNING: No profile found for reference '{reference}'")
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
    print(f"[Prosody] ========== PROSODY TRANSFER START ==========")
    print(f"[Prosody] Input: {voice_path}")
    print(f"[Prosody] Reference: {reference}")
    print(f"[Prosody] Intensity: {intensity}")
    
    # Get input file size for comparison
    input_size = os.path.getsize(voice_path) if os.path.exists(voice_path) else 0
    print(f"[Prosody] Input file size: {input_size} bytes")
    
    if reference == "none" or intensity <= 0:
        print(f"[Prosody] Skipping: reference={reference}, intensity={intensity}")
        print(f"[Prosody] ========== PROSODY TRANSFER END (SKIPPED) ==========")
        return voice_path
    
    profile = get_prosody_profile(reference)
    if not profile:
        print(f"[Prosody] ERROR: No profile found for reference: {reference}")
        print(f"[Prosody] ========== PROSODY TRANSFER END (NO PROFILE) ==========")
        return voice_path
    
    # VALIDATION: Check if profile is valid
    if not _is_valid_profile(profile):
        print(f"[Prosody] ERROR: Profile has invalid values (pitch_mean={profile.get('pitch_mean', 0):.1f}Hz)")
        print(f"[Prosody] ========== PROSODY TRANSFER END (INVALID PROFILE) ==========")
        return voice_path
    
    print(f"[Prosody] Target profile loaded:")
    print(f"[Prosody]   - pitch_mean: {profile.get('pitch_mean', 0):.1f} Hz")
    print(f"[Prosody]   - pitch_std: {profile.get('pitch_std', 0):.1f} Hz")
    print(f"[Prosody]   - pitch_range: {profile.get('pitch_range', 0):.1f} Hz")
    
    try:
        sound = parselmouth.Sound(voice_path)
        print(f"[Prosody] Source audio loaded: duration={sound.duration:.2f}s")
        
        # Extract source pitch characteristics
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        source_mean = call(pitch, "Get mean", 0, 0, "Hertz")
        source_std = call(pitch, "Get standard deviation", 0, 0, "Hertz")
        
        print(f"[Prosody] Source pitch analysis:")
        print(f"[Prosody]   - source_mean: {source_mean:.1f} Hz")
        print(f"[Prosody]   - source_std: {source_std:.1f} Hz")
        
        if source_mean <= 0 or source_std <= 0:
            print("[Prosody] ERROR: Could not analyze source pitch (mean or std <= 0)")
            print(f"[Prosody] ========== PROSODY TRANSFER END (ANALYSIS FAILED) ==========")
            return voice_path
        
        target_mean = profile.get("pitch_mean", source_mean)
        target_std = profile.get("pitch_std", source_std)
        
        if target_mean <= 0:
            target_mean = source_mean
            print(f"[Prosody] WARNING: Target mean invalid, using source mean")
        if target_std <= 0:
            target_std = source_std
            print(f"[Prosody] WARNING: Target std invalid, using source std")
        
        # Calculate transformations based on intensity
        # Pitch shift factor (move toward target mean)
        mean_shift = 1 + (target_mean / source_mean - 1) * intensity
        mean_shift = max(0.5, min(2.0, mean_shift))
        
        # Pitch range scaling (move toward target variation)
        range_scale = 1 + (target_std / source_std - 1) * intensity * 0.5
        range_scale = max(0.5, min(2.0, range_scale))
        
        print(f"[Prosody] Calculated transformations:")
        print(f"[Prosody]   - mean_shift: {mean_shift:.3f} (target/source = {target_mean:.1f}/{source_mean:.1f})")
        print(f"[Prosody]   - range_scale: {range_scale:.3f} (target/source std = {target_std:.1f}/{source_std:.1f})")
        
        # Create manipulation object
        print(f"[Prosody] Creating manipulation object...")
        manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
        pitch_tier = call(manipulation, "Extract pitch tier")
        
        num_points_before = call(pitch_tier, "Get number of points")
        print(f"[Prosody] Pitch tier has {num_points_before} points")
        
        # Apply pitch shift
        print(f"[Prosody] Applying pitch shift (multiply by {mean_shift:.3f})...")
        call(pitch_tier, "Multiply frequencies", sound.xmin, sound.xmax, mean_shift)
        
        # Apply range scaling (expand or compress pitch variation)
        if abs(range_scale - 1.0) > 0.05:
            print(f"[Prosody] Applying range scaling ({range_scale:.3f})...")
            # Get all pitch points
            num_points = call(pitch_tier, "Get number of points")
            if num_points > 0:
                # Calculate new mean after shift
                new_mean = source_mean * mean_shift
                
                points_modified = 0
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
                        points_modified += 1
                
                print(f"[Prosody] Modified {points_modified} pitch points")
        else:
            print(f"[Prosody] Skipping range scaling (scale {range_scale:.3f} too close to 1.0)")
        
        # Replace pitch tier and resynthesize
        print(f"[Prosody] Resynthesizing audio...")
        call([manipulation, pitch_tier], "Replace pitch tier")
        new_sound = call(manipulation, "Get resynthesis (overlap-add)")
        
        # Export to temp file
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        new_sound.save(out_path, "WAV")
        
        # Verify output
        output_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        print(f"[Prosody] Output file: {out_path}")
        print(f"[Prosody] Output file size: {output_size} bytes")
        
        # Quick verification: analyze output pitch
        try:
            out_sound = parselmouth.Sound(out_path)
            out_pitch = call(out_sound, "To Pitch", 0.0, 75, 600)
            out_mean = call(out_pitch, "Get mean", 0, 0, "Hertz")
            out_std = call(out_pitch, "Get standard deviation", 0, 0, "Hertz")
            
            print(f"[Prosody] ========== VERIFICATION ==========")
            print(f"[Prosody] Before: mean={source_mean:.1f}Hz, std={source_std:.1f}Hz")
            print(f"[Prosody] After:  mean={out_mean:.1f}Hz, std={out_std:.1f}Hz")
            print(f"[Prosody] Target: mean={target_mean:.1f}Hz, std={target_std:.1f}Hz")
            print(f"[Prosody] Change: mean={out_mean - source_mean:+.1f}Hz, std={out_std - source_std:+.1f}Hz")
            
            # Check if prosody actually changed
            if abs(out_mean - source_mean) < 1.0 and abs(out_std - source_std) < 1.0:
                print(f"[Prosody] WARNING: Pitch barely changed! Prosody transfer may not be working.")
            else:
                print(f"[Prosody] SUCCESS: Pitch modified successfully.")
        except Exception as ve:
            print(f"[Prosody] WARNING: Could not verify output: {ve}")
        
        print(f"[Prosody] ========== PROSODY TRANSFER END (SUCCESS) ==========")
        return out_path
        
    except Exception as e:
        print(f"[Prosody] ERROR: Exception during prosody transfer: {e}")
        import traceback
        traceback.print_exc()
        print(f"[Prosody] ========== PROSODY TRANSFER END (FAILED) ==========")
        return voice_path


def apply_prosody_with_diagnostics(
    voice_path: str,
    reference: str,
    intensity: float = 0.5,
) -> Dict[str, Any]:
    """
    Apply prosody transfer and return detailed diagnostics.
    
    This is the enhanced version of apply_prosody() that returns
    both the output path AND diagnostic information for verification.
    
    Args:
        voice_path: Path to input voice audio
        reference: Prosody reference ID (e.g., "great_dictator")
        intensity: Transfer intensity from 0.0 (none) to 1.0 (full)
    
    Returns:
        Dict with:
            - output_path: Path to modified audio (or original if skipped/failed)
            - applied: Whether prosody transfer was actually applied
            - skipped: Whether transfer was intentionally skipped
            - error: Error message if failed, None otherwise
            - diagnostics: Detailed diagnostic info
    """
    result = {
        "output_path": voice_path,
        "applied": False,
        "skipped": False,
        "error": None,
        "diagnostics": {
            "input_path": voice_path,
            "reference": reference,
            "intensity": intensity,
            "source_pitch_mean": None,
            "source_pitch_std": None,
            "target_pitch_mean": None,
            "target_pitch_std": None,
            "output_pitch_mean": None,
            "output_pitch_std": None,
            "mean_shift_applied": None,
            "range_scale_applied": None,
            "pitch_change": None,
            "std_change": None,
            "transfer_successful": False,
        }
    }
    
    print(f"[Prosody] ========== PROSODY TRANSFER WITH DIAGNOSTICS ==========")
    print(f"[Prosody] Input: {voice_path}")
    print(f"[Prosody] Reference: {reference}")
    print(f"[Prosody] Intensity: {intensity}")
    
    # Check if input file exists
    if not os.path.exists(voice_path):
        result["error"] = f"Input file not found: {voice_path}"
        print(f"[Prosody] ERROR: {result['error']}")
        return result
    
    input_size = os.path.getsize(voice_path)
    result["diagnostics"]["input_file_size"] = input_size
    print(f"[Prosody] Input file size: {input_size} bytes")
    
    # Check if transfer should be skipped
    if reference == "none" or intensity <= 0:
        result["skipped"] = True
        result["diagnostics"]["skip_reason"] = f"reference={reference}, intensity={intensity}"
        print(f"[Prosody] Skipping: {result['diagnostics']['skip_reason']}")
        return result
    
    # Load target profile
    profile = get_prosody_profile(reference)
    if not profile:
        result["error"] = f"No profile found for reference: {reference}"
        print(f"[Prosody] ERROR: {result['error']}")
        return result
    
    # VALIDATION: Check if profile is valid
    if not _is_valid_profile(profile):
        result["error"] = f"Profile has invalid values (pitch_mean={profile.get('pitch_mean', 0):.1f}Hz, pitch_std={profile.get('pitch_std', 0):.1f}Hz)"
        print(f"[Prosody] ERROR: {result['error']}")
        return result
    
    result["diagnostics"]["target_pitch_mean"] = profile.get("pitch_mean", 0)
    result["diagnostics"]["target_pitch_std"] = profile.get("pitch_std", 0)
    print(f"[Prosody] Target profile: mean={profile.get('pitch_mean', 0):.1f}Hz, std={profile.get('pitch_std', 0):.1f}Hz")
    
    try:
        sound = parselmouth.Sound(voice_path)
        print(f"[Prosody] Source audio loaded: duration={sound.duration:.2f}s")
        
        # Extract source pitch characteristics
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        source_mean = call(pitch, "Get mean", 0, 0, "Hertz")
        source_std = call(pitch, "Get standard deviation", 0, 0, "Hertz")
        
        result["diagnostics"]["source_pitch_mean"] = source_mean
        result["diagnostics"]["source_pitch_std"] = source_std
        print(f"[Prosody] Source pitch: mean={source_mean:.1f}Hz, std={source_std:.1f}Hz")
        
        if source_mean <= 0 or source_std <= 0:
            result["error"] = "Could not analyze source pitch (mean or std <= 0)"
            print(f"[Prosody] ERROR: {result['error']}")
            return result
        
        target_mean = profile.get("pitch_mean", source_mean)
        target_std = profile.get("pitch_std", source_std)
        
        if target_mean <= 0:
            target_mean = source_mean
        if target_std <= 0:
            target_std = source_std
        
        # Calculate transformations
        mean_shift = 1 + (target_mean / source_mean - 1) * intensity
        mean_shift = max(0.5, min(2.0, mean_shift))
        
        range_scale = 1 + (target_std / source_std - 1) * intensity * 0.5
        range_scale = max(0.5, min(2.0, range_scale))
        
        result["diagnostics"]["mean_shift_applied"] = mean_shift
        result["diagnostics"]["range_scale_applied"] = range_scale
        print(f"[Prosody] Transformations: mean_shift={mean_shift:.3f}, range_scale={range_scale:.3f}")
        
        # Create manipulation object
        manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
        pitch_tier = call(manipulation, "Extract pitch tier")
        
        num_points = call(pitch_tier, "Get number of points")
        result["diagnostics"]["pitch_points_count"] = num_points
        print(f"[Prosody] Pitch tier has {num_points} points")
        
        # Apply pitch shift
        call(pitch_tier, "Multiply frequencies", sound.xmin, sound.xmax, mean_shift)
        
        # Apply range scaling
        if abs(range_scale - 1.0) > 0.05 and num_points > 0:
            new_mean = source_mean * mean_shift
            points_modified = 0
            
            for i in range(1, num_points + 1):
                time = call(pitch_tier, "Get time from index", i)
                value = call(pitch_tier, "Get value at index", i)
                if value > 0:
                    distance = value - new_mean
                    new_value = new_mean + distance * range_scale
                    new_value = max(50, min(500, new_value))
                    call(pitch_tier, "Remove point", i)
                    call(pitch_tier, "Add point", time, new_value)
                    points_modified += 1
            
            result["diagnostics"]["pitch_points_modified"] = points_modified
            print(f"[Prosody] Modified {points_modified} pitch points")
        
        # Resynthesize
        call([manipulation, pitch_tier], "Replace pitch tier")
        new_sound = call(manipulation, "Get resynthesis (overlap-add)")
        
        # Export
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        new_sound.save(out_path, "WAV")
        
        output_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        result["diagnostics"]["output_file_size"] = output_size
        result["output_path"] = out_path
        print(f"[Prosody] Output: {out_path} ({output_size} bytes)")
        
        # Verification
        try:
            out_sound = parselmouth.Sound(out_path)
            out_pitch = call(out_sound, "To Pitch", 0.0, 75, 600)
            out_mean = call(out_pitch, "Get mean", 0, 0, "Hertz")
            out_std = call(out_pitch, "Get standard deviation", 0, 0, "Hertz")
            
            result["diagnostics"]["output_pitch_mean"] = out_mean
            result["diagnostics"]["output_pitch_std"] = out_std
            result["diagnostics"]["pitch_change"] = out_mean - source_mean
            result["diagnostics"]["std_change"] = out_std - source_std
            
            print(f"[Prosody] VERIFICATION:")
            print(f"[Prosody]   Before: mean={source_mean:.1f}Hz, std={source_std:.1f}Hz")
            print(f"[Prosody]   After:  mean={out_mean:.1f}Hz, std={out_std:.1f}Hz")
            print(f"[Prosody]   Target: mean={target_mean:.1f}Hz, std={target_std:.1f}Hz")
            print(f"[Prosody]   Change: mean={out_mean - source_mean:+.1f}Hz, std={out_std - source_std:+.1f}Hz")
            
            # Determine if transfer was successful
            pitch_changed = abs(out_mean - source_mean) >= 1.0 or abs(out_std - source_std) >= 1.0
            result["diagnostics"]["transfer_successful"] = pitch_changed
            result["applied"] = pitch_changed
            
            if pitch_changed:
                print(f"[Prosody] ✅ SUCCESS: Prosody transfer applied successfully")
            else:
                print(f"[Prosody] ⚠️ WARNING: Pitch barely changed - transfer may not be effective")
                result["diagnostics"]["warning"] = "Pitch barely changed after transfer"
                
        except Exception as ve:
            print(f"[Prosody] WARNING: Could not verify output: {ve}")
            result["diagnostics"]["verification_error"] = str(ve)
            # Still mark as applied since we did produce output
            result["applied"] = True
        
        print(f"[Prosody] ========== PROSODY TRANSFER COMPLETE ==========")
        return result
        
    except Exception as e:
        result["error"] = str(e)
        print(f"[Prosody] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return result


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
    print(f"[Prosody] Preloading profiles from {prosody_dir}")
    
    if not prosody_dir.exists():
        print(f"[Prosody] WARNING: Prosody directory does not exist: {prosody_dir}")
        return
    
    files_found = 0
    profiles_created = 0
    profiles_invalid = 0
    
    for f in prosody_dir.iterdir():
        if f.suffix.lower() in [".mp3", ".wav", ".m4a", ".ogg"]:
            files_found += 1
            stem = f.stem
            profile_path = prosody_dir / f"{stem}_profile.json"
            
            # Check if existing profile is valid
            need_extract = True
            if profile_path.exists():
                try:
                    with open(profile_path, "r") as pf:
                        existing_profile = json.load(pf)
                    if _is_valid_profile(existing_profile):
                        print(f"[Prosody] Valid profile exists: {profile_path}")
                        need_extract = False
                    else:
                        print(f"[Prosody] Existing profile is invalid (zeros), will re-extract: {profile_path}")
                        profiles_invalid += 1
                        try:
                            os.unlink(profile_path)
                        except Exception:
                            pass
                except Exception:
                    pass
            
            if need_extract:
                print(f"[Prosody] Extracting profile for {f.name}")
                profile = extract_prosody(str(f))
                
                # Only save if valid
                if _is_valid_profile(profile):
                    profile["source_file"] = str(f)
                    profile["id"] = stem
                    profile["name"] = stem.replace("_", " ").title()
                    try:
                        with open(profile_path, "w") as pf:
                            json.dump(profile, pf, indent=2)
                        profiles_created += 1
                        print(f"[Prosody] Saved profile: {profile_path} (pitch_mean={profile['pitch_mean']:.1f}Hz)")
                    except Exception as e:
                        print(f"[Prosody] Could not save profile: {e}")
                else:
                    print(f"[Prosody] WARNING: Extraction failed for {f.name} - profile has zero values")
    
    print(f"[Prosody] Preload complete: {files_found} audio files, {profiles_created} new profiles created, {profiles_invalid} invalid profiles replaced")


def verify_prosody_setup() -> dict:
    """
    Verify prosody setup is correct.
    Call this to diagnose prosody transfer issues.
    
    Returns dict with diagnostic information.
    """
    prosody_dir = ASSETS_DIR / "prosody"
    
    result = {
        "prosody_dir": str(prosody_dir),
        "prosody_dir_exists": prosody_dir.exists(),
        "audio_files": [],
        "profile_files": [],
        "great_dictator_audio": None,
        "great_dictator_profile": None,
        "parselmouth_version": parselmouth.__version__ if hasattr(parselmouth, '__version__') else "unknown",
        "status": "unknown",
        "issues": [],
    }
    
    if not prosody_dir.exists():
        result["status"] = "error"
        result["issues"].append(f"Prosody directory does not exist: {prosody_dir}")
        return result
    
    for f in prosody_dir.iterdir():
        if f.suffix.lower() in [".mp3", ".wav", ".m4a", ".ogg"]:
            result["audio_files"].append(f.name)
            if "great_dictator" in f.name.lower():
                result["great_dictator_audio"] = str(f)
        elif f.suffix.lower() == ".json":
            result["profile_files"].append(f.name)
            if "great_dictator" in f.name.lower():
                result["great_dictator_profile"] = str(f)
    
    # Check for great_dictator files
    if not result["great_dictator_audio"] and not result["great_dictator_profile"]:
        result["issues"].append("No great_dictator audio or profile found")
    
    # Try to load great_dictator profile
    profile = get_prosody_profile("great_dictator")
    result["great_dictator_profile_loaded"] = profile is not None
    if profile:
        result["great_dictator_pitch_mean"] = profile.get("pitch_mean", 0)
        result["great_dictator_pitch_std"] = profile.get("pitch_std", 0)
        
        # Check if profile values are valid
        if not _is_valid_profile(profile):
            result["issues"].append("great_dictator profile has invalid/zero values")
    else:
        result["issues"].append("Could not load great_dictator profile")
    
    # Set overall status
    if len(result["issues"]) == 0:
        result["status"] = "ok"
    elif result["great_dictator_profile_loaded"] and _is_valid_profile(profile):
        result["status"] = "warning"
    else:
        result["status"] = "error"
    
    return result


def test_prosody_transfer(test_text: str = None) -> Dict[str, Any]:
    """
    Test prosody transfer with a simple audio generation.
    
    This function creates a test WAV file with a sine wave tone,
    applies prosody transfer, and verifies the result.
    
    Returns detailed test results.
    """
    import wave
    import struct
    
    result = {
        "test_name": "prosody_transfer_test",
        "status": "unknown",
        "steps": [],
        "errors": [],
    }
    
    # Step 1: Verify setup
    result["steps"].append("Verifying prosody setup...")
    setup = verify_prosody_setup()
    result["setup_verification"] = setup
    
    if setup["status"] == "error":
        result["status"] = "failed"
        result["errors"].append("Prosody setup verification failed")
        return result
    
    # Step 2: Create a test audio file (simple tone)
    result["steps"].append("Creating test audio file...")
    try:
        test_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        
        # Generate a simple tone with varying pitch (simulates speech)
        sample_rate = 44100
        duration = 2.0  # 2 seconds
        num_samples = int(sample_rate * duration)
        
        # Create a tone that varies in frequency (100-200 Hz)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Vary frequency from 100 to 200 Hz over time
            freq = 100 + 50 * np.sin(2 * np.pi * 0.5 * t)  # Oscillate between 100-150 Hz
            sample = int(32767 * 0.5 * np.sin(2 * np.pi * freq * t))
            samples.append(sample)
        
        # Write WAV file
        with wave.open(test_path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for sample in samples:
                wav_file.writeframes(struct.pack('<h', sample))
        
        result["test_audio_path"] = test_path
        result["test_audio_size"] = os.path.getsize(test_path)
        result["steps"].append(f"Created test audio: {test_path} ({result['test_audio_size']} bytes)")
        
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Failed to create test audio: {e}")
        return result
    
    # Step 3: Extract prosody from test audio
    result["steps"].append("Extracting prosody from test audio...")
    try:
        test_profile = extract_prosody(test_path)
        result["test_audio_profile"] = {
            "pitch_mean": test_profile.get("pitch_mean", 0),
            "pitch_std": test_profile.get("pitch_std", 0),
        }
        result["steps"].append(f"Test audio pitch: mean={test_profile.get('pitch_mean', 0):.1f}Hz, std={test_profile.get('pitch_std', 0):.1f}Hz")
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Failed to extract prosody: {e}")
        return result
    
    # Step 4: Apply prosody transfer
    result["steps"].append("Applying prosody transfer...")
    try:
        transfer_result = apply_prosody_with_diagnostics(
            test_path,
            reference="great_dictator",
            intensity=0.7
        )
        result["transfer_result"] = transfer_result
        
        if transfer_result.get("error"):
            result["errors"].append(f"Prosody transfer error: {transfer_result['error']}")
        
        if transfer_result.get("applied"):
            result["steps"].append("Prosody transfer applied successfully")
        elif transfer_result.get("skipped"):
            result["steps"].append("Prosody transfer was skipped")
        else:
            result["steps"].append("Prosody transfer may not have been effective")
            
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Failed to apply prosody: {e}")
        return result
    
    # Step 5: Cleanup
    try:
        os.unlink(test_path)
        if transfer_result.get("output_path") and transfer_result["output_path"] != test_path:
            if os.path.exists(transfer_result["output_path"]):
                os.unlink(transfer_result["output_path"])
    except Exception:
        pass
    
    # Determine overall status
    if len(result["errors"]) > 0:
        result["status"] = "failed"
    elif transfer_result.get("applied"):
        result["status"] = "passed"
    else:
        result["status"] = "warning"
    
    return result
