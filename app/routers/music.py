import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional

from app.config import ASSETS_DIR, UPLOADS_DIR
from app.utils.audio import get_file_duration_ms
from app.utils.naming import sanitize_filename, generate_track_id, extract_track_name
from app.services.prompt import (
    calculate_target_words,
    calculate_target_words_adjusted,
    get_default_tts_wpm,
    get_default_safety_factor,
)

router = APIRouter()

MUSIC_DIR = ASSETS_DIR / "music" / "tracks"
UPLOADED_MUSIC_DIR = UPLOADS_DIR / "music"
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


def scan_music_library() -> List[dict]:
    """Scan music directory and return all tracks."""
    tracks = []
    
    def scan_folder(folder: Path, folder_name: str = "", is_uploaded: bool = False):
        if not folder.exists():
            return
            
        for item in sorted(folder.iterdir()):
            if item.is_dir():
                # Recurse into subfolders
                subfolder_name = item.name if not folder_name else f"{folder_name}/{item.name}"
                scan_folder(item, subfolder_name, is_uploaded)
            elif item.suffix.lower() in ALLOWED_EXTENSIONS:
                try:
                    # Determine the base dir for relative path calculation
                    base_dir = UPLOADED_MUSIC_DIR if is_uploaded else MUSIC_DIR
                    relative_path = str(item.relative_to(base_dir))
                    
                    # Prefix uploaded tracks path to distinguish them
                    if is_uploaded:
                        path_for_api = f"__uploaded__/{relative_path}"
                    else:
                        path_for_api = relative_path
                    
                    track = {
                        "id": generate_track_id(item),
                        "name": extract_track_name(item),
                        "filename": item.name,
                        "folder": folder_name,
                        "path": path_for_api,
                        "full_path": str(item),
                        "extension": item.suffix.lower(),
                        "size_bytes": item.stat().st_size,
                        "is_uploaded": is_uploaded,
                    }
                    tracks.append(track)
                except Exception as e:
                    print(f"[Music] Error scanning {item}: {e}")
    
    # Scan default music directory
    if MUSIC_DIR.exists():
        scan_folder(MUSIC_DIR, "", is_uploaded=False)
    
    # Scan uploaded music directory
    if UPLOADED_MUSIC_DIR.exists():
        scan_folder(UPLOADED_MUSIC_DIR, "", is_uploaded=True)
    
    return tracks


def get_full_path_from_api_path(path: str) -> Path:
    """Convert API path to actual file path."""
    if path.startswith("__uploaded__/"):
        # Remove prefix and use uploaded music directory
        relative_path = path.replace("__uploaded__/", "", 1)
        return UPLOADED_MUSIC_DIR / relative_path
    else:
        return MUSIC_DIR / path


@router.get("/music")
async def list_music():
    """Get all available music tracks."""
    tracks = scan_music_library()
    
    # Group by folder, separating uploaded from default
    folders = {}
    uploaded_folders = {}
    
    for track in tracks:
        folder = track["folder"] or "Uncategorized"
        
        if track.get("is_uploaded"):
            folder_name = f"📁 Uploaded: {folder}" if folder != "Uncategorized" else "📁 Uploaded"
            if folder_name not in uploaded_folders:
                uploaded_folders[folder_name] = []
            uploaded_folders[folder_name].append(track)
        else:
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(track)
    
    # Merge folders with uploaded at the end
    all_folders = {**folders, **uploaded_folders}
    
    return {
        "tracks": tracks,
        "total": len(tracks),
        "folders": all_folders,
        "folder_names": list(all_folders.keys()),
        "has_uploads": len(uploaded_folders) > 0,
    }


@router.get("/music/folders")
async def list_folders():
    """Get list of music folders."""
    folders = []
    
    # Default music folders
    if MUSIC_DIR.exists():
        for item in sorted(MUSIC_DIR.iterdir()):
            if item.is_dir():
                track_count = sum(1 for f in item.rglob("*") if f.suffix.lower() in ALLOWED_EXTENSIONS)
                folders.append({
                    "name": item.name,
                    "track_count": track_count,
                    "is_uploaded": False,
                })
    
    # Uploaded music folders
    if UPLOADED_MUSIC_DIR.exists():
        for item in sorted(UPLOADED_MUSIC_DIR.iterdir()):
            if item.is_dir():
                track_count = sum(1 for f in item.rglob("*") if f.suffix.lower() in ALLOWED_EXTENSIONS)
                folders.append({
                    "name": f"Uploaded: {item.name}",
                    "track_count": track_count,
                    "is_uploaded": True,
                })
        
        # Count files directly in uploaded root
        root_count = sum(1 for f in UPLOADED_MUSIC_DIR.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS)
        if root_count > 0:
            folders.append({
                "name": "Uploaded",
                "track_count": root_count,
                "is_uploaded": True,
            })
    
    return {"folders": folders}


@router.get("/music/track/{track_id}")
async def get_track(track_id: str):
    """Get details for a specific track including duration."""
    tracks = scan_music_library()
    for track in tracks:
        if track["id"] == track_id:
            # Now get duration (expensive operation)
            try:
                duration_ms = get_file_duration_ms(track["full_path"])
                track["duration_ms"] = duration_ms
                if duration_ms and duration_ms > 0:
                    track["target_words"] = calculate_target_words(duration_ms)
                    track["duration_formatted"] = _format_duration(duration_ms)
                else:
                    track["target_words"] = None
                    track["duration_formatted"] = None
            except Exception:
                track["duration_ms"] = None
                track["target_words"] = None
                track["duration_formatted"] = None
            return track
    raise HTTPException(status_code=404, detail="Track not found")


@router.get("/music/by-path")
async def get_track_by_path(path: str):
    """Get track details by relative path."""
    full_path = get_full_path_from_api_path(path)
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        duration_ms = get_file_duration_ms(str(full_path))
        
        target_words = None
        duration_formatted = None
        if duration_ms and duration_ms > 0:
            target_words = calculate_target_words(duration_ms)
            duration_formatted = _format_duration(duration_ms)
        
        track = {
            "id": generate_track_id(full_path),
            "name": extract_track_name(full_path),
            "filename": full_path.name,
            "path": path,
            "full_path": str(full_path),
            "duration_ms": duration_ms,
            "duration_formatted": duration_formatted,
            "target_words": target_words,
            "is_uploaded": path.startswith("__uploaded__/"),
        }
        return track
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading track: {str(e)}")


@router.get("/music/duration")
async def get_track_duration(
    path: str,
    voice_speed: float = 1.0,
    speech_entry_ms: int = 0,
    crossfade_ms: int = 2000,
    wpm: Optional[int] = None,
    safety_factor: Optional[float] = None,
):
    """
    Get duration and target word count for a music track.
    
    This endpoint calculates the optimal word count for speech that will
    match the music duration, accounting for voice speed and timing parameters.
    
    Args:
        path: Relative path to the track within music directory
        voice_speed: ElevenLabs voice speed multiplier (0.5 to 2.0, default 1.0)
        speech_entry_ms: Delay before voice starts in ms (default 0)
        crossfade_ms: Crossfade duration at end in ms (default 2000)
        wpm: Words per minute override (optional, uses default 102 if not specified)
        safety_factor: Safety buffer override (optional, uses default 0.88 if not specified)
    
    Returns:
        duration_ms, duration_formatted, target_words, and calculation parameters
    """
    full_path = get_full_path_from_api_path(path)
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        duration_ms = get_file_duration_ms(str(full_path))
        
        if not duration_ms or duration_ms <= 0:
            raise HTTPException(status_code=500, detail="Could not determine track duration")
        
        # Use provided values or defaults
        base_wpm = wpm if wpm is not None else get_default_tts_wpm()
        used_safety_factor = safety_factor if safety_factor is not None else get_default_safety_factor()
        
        # Calculate target words with all adjustments
        target_words = calculate_target_words_adjusted(
            duration_ms=duration_ms,
            voice_speed=voice_speed,
            speech_entry_ms=speech_entry_ms,
            crossfade_ms=crossfade_ms,
            base_wpm=base_wpm,
            safety_factor=used_safety_factor,
        )
        
        # Calculate effective duration (for display purposes)
        effective_duration_ms = duration_ms - speech_entry_ms - (crossfade_ms / 2)
        effective_duration_ms = max(0, effective_duration_ms)
        
        # Estimate speech duration based on target words
        adjusted_wpm = base_wpm * voice_speed
        estimated_speech_ms = int((target_words / adjusted_wpm) * 60 * 1000) if adjusted_wpm > 0 else 0
        
        return {
            "path": path,
            "duration_ms": duration_ms,
            "duration_formatted": _format_duration(duration_ms),
            "effective_duration_ms": int(effective_duration_ms),
            "effective_duration_formatted": _format_duration(int(effective_duration_ms)),
            "target_words": target_words,
            "estimated_speech_ms": estimated_speech_ms,
            "estimated_speech_formatted": _format_duration(estimated_speech_ms),
            # Parameters used for calculation
            "params": {
                "voice_speed": voice_speed,
                "speech_entry_ms": speech_entry_ms,
                "crossfade_ms": crossfade_ms,
                "words_per_minute": base_wpm,
                "safety_factor": used_safety_factor,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading track: {str(e)}")


def _format_duration(duration_ms: int) -> str:
    """Format duration in milliseconds to MM:SS string."""
    if not duration_ms or duration_ms <= 0:
        return "0:00"
    total_seconds = duration_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


@router.post("/music/upload")
async def upload_music(file: UploadFile = File(...), folder: str = ""):
    """Upload a new music track."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Save to uploads/music directory (separate from default assets)
    safe_filename = sanitize_filename(Path(file.filename).stem) + ext
    if folder:
        dest_dir = UPLOADED_MUSIC_DIR / sanitize_filename(folder)
    else:
        dest_dir = UPLOADED_MUSIC_DIR
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / safe_filename
    
    # Handle duplicates
    counter = 1
    while dest_path.exists():
        stem = sanitize_filename(Path(file.filename).stem)
        dest_path = dest_dir / f"{stem}_{counter}{ext}"
        counter += 1
    
    # Save file
    try:
        with open(dest_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Get duration for the response
        try:
            duration_ms = get_file_duration_ms(str(dest_path))
            duration_formatted = _format_duration(duration_ms) if duration_ms else None
            target_words = calculate_target_words(duration_ms) if duration_ms else None
        except Exception:
            duration_ms = None
            duration_formatted = None
            target_words = None
        
        # Build the API path
        relative_path = str(dest_path.relative_to(UPLOADED_MUSIC_DIR))
        api_path = f"__uploaded__/{relative_path}"
        
        return {
            "success": True,
            "track": {
                "id": generate_track_id(dest_path),
                "name": extract_track_name(dest_path),
                "filename": dest_path.name,
                "path": api_path,
                "folder": folder or "Uploaded",
                "duration_ms": duration_ms,
                "duration_formatted": duration_formatted,
                "target_words": target_words,
                "is_uploaded": True,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/music/track/{track_id}")
async def delete_track(track_id: str):
    """Delete a music track (only uploaded tracks can be deleted)."""
    tracks = scan_music_library()
    for track in tracks:
        if track["id"] == track_id:
            # Only allow deleting uploaded tracks
            if not track.get("is_uploaded"):
                raise HTTPException(status_code=403, detail="Cannot delete default tracks")
            
            try:
                Path(track["full_path"]).unlink()
                return {"success": True, "deleted": track["filename"]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    raise HTTPException(status_code=404, detail="Track not found")


@router.get("/music/uploaded")
async def list_uploaded_music():
    """Get only uploaded music tracks."""
    tracks = scan_music_library()
    uploaded = [t for t in tracks if t.get("is_uploaded")]
    
    folders = {}
    for track in uploaded:
        folder = track["folder"] or "Uploaded"
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(track)
    
    return {
        "tracks": uploaded,
        "total": len(uploaded),
        "folders": folders,
    }
