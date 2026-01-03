import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List

from app.config import ASSETS_DIR, UPLOADS_DIR
from app.utils.audio import get_file_duration_ms
from app.utils.naming import sanitize_filename, generate_track_id, extract_track_name
from app.services.prompt import calculate_target_words  # NEW: Import helper

router = APIRouter()

MUSIC_DIR = ASSETS_DIR / "music" / "tracks"
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


def scan_music_library() -> List[dict]:
    """Scan music directory and return all tracks."""
    tracks = []
    
    if not MUSIC_DIR.exists():
        return tracks
    
    def scan_folder(folder: Path, folder_name: str = ""):
        for item in sorted(folder.iterdir()):
            if item.is_dir():
                # Recurse into subfolders
                subfolder_name = item.name if not folder_name else f"{folder_name}/{item.name}"
                scan_folder(item, subfolder_name)
            elif item.suffix.lower() in ALLOWED_EXTENSIONS:
                try:
                    track = {
                        "id": generate_track_id(item),
                        "name": extract_track_name(item),
                        "filename": item.name,
                        "folder": folder_name,
                        "path": str(item.relative_to(MUSIC_DIR)),
                        "full_path": str(item),
                        "extension": item.suffix.lower(),
                        "size_bytes": item.stat().st_size,
                    }
                    # Duration extraction is expensive - skip for listing
                    tracks.append(track)
                except Exception as e:
                    print(f"[Music] Error scanning {item}: {e}")
    
    scan_folder(MUSIC_DIR)
    return tracks


@router.get("/music")
async def list_music():
    """Get all available music tracks."""
    tracks = scan_music_library()
    
    # Group by folder
    folders = {}
    for track in tracks:
        folder = track["folder"] or "Uncategorized"
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(track)
    
    return {
        "tracks": tracks,
        "total": len(tracks),
        "folders": folders,
        "folder_names": list(folders.keys()),
    }


@router.get("/music/folders")
async def list_folders():
    """Get list of music folders."""
    if not MUSIC_DIR.exists():
        return {"folders": []}
    
    folders = []
    for item in sorted(MUSIC_DIR.iterdir()):
        if item.is_dir():
            track_count = sum(1 for f in item.rglob("*") if f.suffix.lower() in ALLOWED_EXTENSIONS)
            folders.append({
                "name": item.name,
                "track_count": track_count,
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
                # NEW: Also calculate target words
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
    full_path = MUSIC_DIR / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        duration_ms = get_file_duration_ms(str(full_path))
        
        # NEW: Calculate target words from duration
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
            "duration_formatted": duration_formatted,  # NEW
            "target_words": target_words,  # NEW
        }
        return track
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading track: {str(e)}")


# NEW: Quick endpoint to get just duration and target words
@router.get("/music/duration")
async def get_track_duration(path: str, wpm: int = 140):
    """
    Get duration and target word count for a music track.
    
    This is a lightweight endpoint specifically for the word count calculation.
    
    Args:
        path: Relative path to the track within music directory
        wpm: Words per minute for calculation (default 140)
    
    Returns:
        duration_ms, duration_formatted, target_words
    """
    full_path = MUSIC_DIR / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        duration_ms = get_file_duration_ms(str(full_path))
        
        if not duration_ms or duration_ms <= 0:
            raise HTTPException(status_code=500, detail="Could not determine track duration")
        
        target_words = calculate_target_words(duration_ms, wpm)
        
        return {
            "path": path,
            "duration_ms": duration_ms,
            "duration_formatted": _format_duration(duration_ms),
            "words_per_minute": wpm,
            "target_words": target_words,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading track: {str(e)}")


# NEW: Helper function to format duration
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
    
    # Determine destination
    safe_filename = sanitize_filename(Path(file.filename).stem) + ext
    if folder:
        dest_dir = MUSIC_DIR / sanitize_filename(folder)
    else:
        dest_dir = MUSIC_DIR / "uploads"
    
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
        
        return {
            "success": True,
            "track": {
                "id": generate_track_id(dest_path),
                "name": extract_track_name(dest_path),
                "filename": dest_path.name,
                "path": str(dest_path.relative_to(MUSIC_DIR)),
                "folder": folder or "uploads",
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/music/track/{track_id}")
async def delete_track(track_id: str):
    """Delete a music track."""
    tracks = scan_music_library()
    for track in tracks:
        if track["id"] == track_id:
            try:
                Path(track["full_path"]).unlink()
                return {"success": True, "deleted": track["filename"]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    raise HTTPException(status_code=404, detail="Track not found")