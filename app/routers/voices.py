from fastapi import APIRouter, HTTPException
from app.services.tts import get_available_voices
from app.config import VOICE_DEFAULT, VOICE_SEVAN, VOICE_CARTER, VOICE_JJ

router = APIRouter()


@router.get("/voices")
async def list_voices():
    """Get all available ElevenLabs voices."""
    try:
        voices = get_available_voices()
        
        # Mark default/favorite voices
        favorite_ids = [VOICE_DEFAULT, VOICE_SEVAN, VOICE_CARTER, VOICE_JJ]
        for v in voices:
            v["is_favorite"] = v["voice_id"] in favorite_ids
        
        # Sort: favorites first, then alphabetically
        voices.sort(key=lambda x: (not x["is_favorite"], x["name"].lower()))
        
        return {
            "voices": voices,
            "total": len(voices),
            "default_voice_id": VOICE_DEFAULT,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch voices: {str(e)}")


@router.get("/voices/favorites")
async def list_favorite_voices():
    """Get favorite/default voices."""
    return {
        "favorites": [
            {"id": VOICE_DEFAULT, "name": "Default (Inception Primary)", "env_key": "VOICE_DEFAULT"},
            {"id": VOICE_SEVAN, "name": "Sevan", "env_key": "VOICE_SEVAN"},
            {"id": VOICE_CARTER, "name": "Carter", "env_key": "VOICE_CARTER"},
            {"id": VOICE_JJ, "name": "JJ", "env_key": "VOICE_JJ"},
        ]
    }


@router.get("/voices/{voice_id}")
async def get_voice(voice_id: str):
    """Get details for a specific voice."""
    voices = get_available_voices()
    for v in voices:
        if v["voice_id"] == voice_id:
            return v
    raise HTTPException(status_code=404, detail="Voice not found")