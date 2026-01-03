from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models.schemas import StimulusCreate, StimulusResponse, StimulusList
from app.db.crud import (
    create_stimulus,
    get_stimulus,
    get_all_stimuli,
    update_stimulus,
    delete_stimulus,
    get_next_stimulus_id,
)

router = APIRouter()


@router.get("/stimuli", response_model=StimulusList)
async def list_stimuli(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Get all stimuli with optional filtering."""
    stimuli = get_all_stimuli()
    
    # Filter by status if provided
    if status:
        stimuli = [s for s in stimuli if s.status == status]
    
    total = len(stimuli)
    stimuli = stimuli[offset:offset + limit]
    
    return StimulusList(stimuli=stimuli, total=total)


@router.get("/stimuli/next-id")
async def get_next_id():
    """Get the next available stimulus ID."""
    next_id = get_next_stimulus_id()
    return {"next_id": next_id}


@router.get("/stimuli/{stimulus_id}", response_model=StimulusResponse)
async def get_stimulus_by_id(stimulus_id: str):
    """Get a specific stimulus by ID."""
    stimulus = get_stimulus(stimulus_id)
    if not stimulus:
        raise HTTPException(status_code=404, detail="Stimulus not found")
    return stimulus


@router.post("/stimuli", response_model=dict)
async def create_new_stimulus(stimulus: StimulusCreate):
    """Create a new stimulus record."""
    try:
        # Auto-generate ID if not provided
        if not stimulus.id:
            stimulus.id = get_next_stimulus_id()
        
        # Check if ID already exists
        existing = get_stimulus(stimulus.id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Stimulus {stimulus.id} already exists")
        
        stimulus_id = create_stimulus(stimulus)
        return {
            "success": True,
            "stimulus_id": stimulus_id,
            "message": f"Stimulus {stimulus_id} created",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create stimulus: {str(e)}")


@router.put("/stimuli/{stimulus_id}", response_model=dict)
async def update_stimulus_by_id(stimulus_id: str, stimulus: StimulusCreate):
    """Update an existing stimulus."""
    existing = get_stimulus(stimulus_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Stimulus not found")
    
    try:
        success = update_stimulus(stimulus_id, stimulus)
        if success:
            return {
                "success": True,
                "stimulus_id": stimulus_id,
                "message": f"Stimulus {stimulus_id} updated",
            }
        else:
            raise HTTPException(status_code=500, detail="Update failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update stimulus: {str(e)}")


@router.delete("/stimuli/{stimulus_id}")
async def delete_stimulus_by_id(stimulus_id: str):
    """Delete a stimulus."""
    existing = get_stimulus(stimulus_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Stimulus not found")
    
    try:
        success = delete_stimulus(stimulus_id)
        if success:
            return {
                "success": True,
                "stimulus_id": stimulus_id,
                "message": f"Stimulus {stimulus_id} deleted",
            }
        else:
            raise HTTPException(status_code=500, detail="Delete failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete stimulus: {str(e)}")


@router.post("/stimuli/{stimulus_id}/duplicate")
async def duplicate_stimulus(stimulus_id: str, new_id: Optional[str] = None):
    """Duplicate a stimulus with a new ID."""
    existing = get_stimulus(stimulus_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Stimulus not found")
    
    # Create new stimulus with same params
    new_stimulus = StimulusCreate(
        id=new_id or get_next_stimulus_id(),
        music=existing.music,
        voice=existing.voice,
        text=existing.text,
        mix=existing.mix,
        prosody=existing.prosody,
        notes=f"Duplicated from {stimulus_id}",
    )
    
    try:
        created_id = create_stimulus(new_stimulus)
        return {
            "success": True,
            "original_id": stimulus_id,
            "new_id": created_id,
            "message": f"Stimulus duplicated as {created_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate: {str(e)}")