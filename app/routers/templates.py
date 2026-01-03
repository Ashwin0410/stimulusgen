from fastapi import APIRouter, HTTPException
from typing import List

from app.models.schemas import TemplateCreate, TemplateResponse
from app.db.crud import (
    create_template,
    get_template,
    get_all_templates,
    delete_template,
)

router = APIRouter()


# Default templates (built-in presets)
DEFAULT_TEMPLATES = [
    {
        "id": "chaplin_style",
        "name": "Chaplin Style",
        "description": "Emotional crescendo like Great Dictator speech",
        "music": {"track": "", "volume_db": -6.0, "speech_entry_ms": 0, "crossfade_ms": 2000},
        "voice": {
            "model": "eleven_multilingual_v2",
            "voice_id": "qNkzaJoHLLdpvgh5tISm",
            "stability": 0.35,
            "similarity_boost": 0.8,
            "style_exaggeration": 0.4,
            "speaker_boost": True,
            "speed": 0.95,
        },
        "text": {"source": "llm", "llm_model": "claude-3-sonnet-20240229", "llm_temperature": 0.8},
        "mix": {
            "reverb_mix": 20.0,
            "reverb_decay": 1.2,
            "compression_ratio": 2.5,
            "deesser_threshold": -8.0,
            "eq_low_cut": 80,
            "eq_high_cut": 12000,
            "pitch_shift": 0,
            "normalization_lufs": -16.0,
        },
        "prosody": {"reference": "great_dictator", "intensity": 0.3},
    },
    {
        "id": "calm_meditation",
        "name": "Calm Meditation",
        "description": "Slow, peaceful, grounding",
        "music": {"track": "", "volume_db": -8.0, "speech_entry_ms": 2000, "crossfade_ms": 3000},
        "voice": {
            "model": "eleven_multilingual_v2",
            "voice_id": "qNkzaJoHLLdpvgh5tISm",
            "stability": 0.7,
            "similarity_boost": 0.6,
            "style_exaggeration": 0.1,
            "speaker_boost": True,
            "speed": 0.85,
        },
        "text": {"source": "llm", "llm_model": "claude-3-sonnet-20240229", "llm_temperature": 0.6},
        "mix": {
            "reverb_mix": 35.0,
            "reverb_decay": 2.0,
            "compression_ratio": 1.5,
            "deesser_threshold": -10.0,
            "eq_low_cut": 60,
            "eq_high_cut": 14000,
            "pitch_shift": 0,
            "normalization_lufs": -18.0,
        },
        "prosody": {"reference": "none", "intensity": 0.0},
    },
    {
        "id": "cosmic_wonder",
        "name": "Cosmic Wonder",
        "description": "Sagan-style awe and perspective",
        "music": {"track": "", "volume_db": -5.0, "speech_entry_ms": 3000, "crossfade_ms": 2500},
        "voice": {
            "model": "eleven_multilingual_v2",
            "voice_id": "qNkzaJoHLLdpvgh5tISm",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style_exaggeration": 0.25,
            "speaker_boost": True,
            "speed": 0.9,
        },
        "text": {"source": "llm", "llm_model": "claude-3-sonnet-20240229", "llm_temperature": 0.7},
        "mix": {
            "reverb_mix": 30.0,
            "reverb_decay": 1.8,
            "compression_ratio": 2.0,
            "deesser_threshold": -6.0,
            "eq_low_cut": 70,
            "eq_high_cut": 13000,
            "pitch_shift": 0,
            "normalization_lufs": -16.0,
        },
        "prosody": {"reference": "none", "intensity": 0.0},
    },
]


@router.get("/templates")
async def list_templates():
    """Get all templates (built-in + custom)."""
    custom_templates = get_all_templates()
    
    return {
        "default_templates": DEFAULT_TEMPLATES,
        "custom_templates": [t.model_dump() for t in custom_templates],
        "total": len(DEFAULT_TEMPLATES) + len(custom_templates),
    }


@router.get("/templates/defaults")
async def list_default_templates():
    """Get built-in default templates only."""
    return {
        "templates": DEFAULT_TEMPLATES,
        "total": len(DEFAULT_TEMPLATES),
    }


@router.get("/templates/{template_id}")
async def get_template_by_id(template_id: str):
    """Get a specific template by ID."""
    # Check default templates first
    for t in DEFAULT_TEMPLATES:
        if t["id"] == template_id:
            return {"template": t, "is_default": True}
    
    # Check custom templates
    template = get_template(template_id)
    if template:
        return {"template": template.model_dump(), "is_default": False}
    
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/templates")
async def create_new_template(template: TemplateCreate):
    """Create a new custom template."""
    try:
        template_id = create_template(template)
        return {
            "success": True,
            "template_id": template_id,
            "message": f"Template '{template.name}' created",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.delete("/templates/{template_id}")
async def delete_template_by_id(template_id: str):
    """Delete a custom template."""
    # Can't delete default templates
    for t in DEFAULT_TEMPLATES:
        if t["id"] == template_id:
            raise HTTPException(status_code=400, detail="Cannot delete default templates")
    
    success = delete_template(template_id)
    if success:
        return {"success": True, "message": f"Template {template_id} deleted"}
    raise HTTPException(status_code=404, detail="Template not found")