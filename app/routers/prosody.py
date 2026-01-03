import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config import ASSETS_DIR, UPLOADS_DIR
from app.services.prosody import (
    extract_prosody,
    get_prosody_profile,
    list_prosody_references,
    compare_prosody,
    preload_profiles,
)

router = APIRouter()

PROSODY_DIR = ASSETS_DIR / "prosody"
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}


@router.get("/prosody/references")
async def get_references():
    """Get all available prosody references."""
    references = list_prosody_references()
    return {
        "references": references,
        "total": len(references),
    }


@router.get("/prosody/profile/{reference_id}")
async def get_profile(reference_id: str):
    """Get prosody profile for a reference."""
    profile = get_prosody_profile(reference_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Prosody reference not found")
    return {"profile": profile}


@router.post("/prosody/extract")
async def extract_from_file(file: UploadFile = File(...)):
    """Extract prosody profile from uploaded audio file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Save to temp location
    temp_path = UPLOADS_DIR / "prosody" / file.filename
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Extract prosody
        profile = extract_prosody(str(temp_path))
        profile["source_file"] = file.filename
        
        return {
            "success": True,
            "filename": file.filename,
            "profile": profile,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.post("/prosody/upload")
async def upload_reference(file: UploadFile = File(...), name: str = ""):
    """Upload a new prosody reference audio file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Determine filename
    if name:
        safe_name = name.lower().replace(" ", "_")
        dest_filename = f"{safe_name}{ext}"
    else:
        dest_filename = file.filename
    
    dest_path = PROSODY_DIR / dest_filename
    
    # Handle duplicates
    counter = 1
    while dest_path.exists():
        stem = dest_path.stem
        dest_path = PROSODY_DIR / f"{stem}_{counter}{ext}"
        counter += 1
    
    try:
        PROSODY_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(dest_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Extract and cache profile
        profile = extract_prosody(str(dest_path))
        profile["source_file"] = str(dest_path)
        profile["id"] = dest_path.stem
        profile["name"] = name or dest_path.stem.replace("_", " ").title()
        
        # Save profile JSON
        profile_path = PROSODY_DIR / f"{dest_path.stem}_profile.json"
        import json
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        
        return {
            "success": True,
            "reference_id": dest_path.stem,
            "filename": dest_path.name,
            "profile": profile,
        }
    except Exception as e:
        # Clean up on error
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/prosody/compare")
async def compare_to_reference(
    file: UploadFile = File(...),
    reference: str = "great_dictator"
):
    """Compare uploaded audio to a prosody reference."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Save to temp location
    temp_path = UPLOADS_DIR / "prosody" / f"compare_{file.filename}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Compare
        result = compare_prosody(str(temp_path), reference)
        
        return {
            "success": True,
            "reference": reference,
            "comparison": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
    finally:
        # Clean up
        if temp_path.exists():
            temp_path.unlink()


@router.delete("/prosody/reference/{reference_id}")
async def delete_reference(reference_id: str):
    """Delete a custom prosody reference."""
    if reference_id == "great_dictator":
        raise HTTPException(status_code=400, detail="Cannot delete built-in reference")
    
    # Find and delete the audio file
    for ext in ALLOWED_EXTENSIONS:
        audio_path = PROSODY_DIR / f"{reference_id}{ext}"
        if audio_path.exists():
            audio_path.unlink()
            
            # Also delete profile JSON if exists
            profile_path = PROSODY_DIR / f"{reference_id}_profile.json"
            if profile_path.exists():
                profile_path.unlink()
            
            return {"success": True, "deleted": reference_id}
    
    # Try exact filename match
    audio_path = PROSODY_DIR / reference_id
    if audio_path.exists():
        audio_path.unlink()
        
        profile_path = PROSODY_DIR / f"{audio_path.stem}_profile.json"
        if profile_path.exists():
            profile_path.unlink()
        
        return {"success": True, "deleted": reference_id}
    
    raise HTTPException(status_code=404, detail="Reference not found")


@router.post("/prosody/preload")
async def preload_all_profiles():
    """Pre-extract and cache all prosody profiles."""
    try:
        preload_profiles()
        references = list_prosody_references()
        return {
            "success": True,
            "message": "Profiles preloaded",
            "total_references": len(references),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preload failed: {str(e)}")
