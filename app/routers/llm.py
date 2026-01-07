from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.llm import generate_text, get_available_models
from app.services.prompt import (
    build_prompt, 
    list_styles, 
    list_templates, 
    get_system_prompt,
    get_chaplin_speech,
    calculate_target_words,
    calculate_target_words_adjusted,
    get_default_tts_wpm,
    get_default_safety_factor,
)

router = APIRouter()


class GenerateTextRequest(BaseModel):
    topic: str
    style: str = "default"
    template: str = "about_topic"
    model: str = "claude-3-sonnet-20240229"
    temperature: float = 0.7
    max_tokens: int = 500
    custom_system_prompt: Optional[str] = None
    custom_user_prompt: Optional[str] = None
    context: Optional[str] = None
    target_words: Optional[int] = None  # Target word count


class GenerateTextResponse(BaseModel):
    text: str
    model: str
    tokens_used: int
    style: str
    template: str
    target_words: Optional[int] = None  # Return target used
    actual_words: Optional[int] = None  # Return actual word count
    word_count_warning: Optional[str] = None  # Warning if count is off


@router.post("/llm/generate", response_model=GenerateTextResponse)
async def generate_speech_text(request: GenerateTextRequest):
    """Generate speech text using LLM."""
    try:
        # Build prompts
        system_prompt, user_prompt = build_prompt(
            topic=request.topic,
            style=request.style,
            template=request.template,
            custom_system=request.custom_system_prompt,
            custom_user=request.custom_user_prompt,
            context=request.context,
            target_words=request.target_words,
        )
        
        # Generate text
        result = generate_text(
            prompt=user_prompt,
            model=request.model,
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        # Calculate actual word count
        generated_text = result["text"]
        actual_words = len(generated_text.split()) if generated_text else 0
        
        # Check if word count is significantly off from target
        word_count_warning = None
        if request.target_words and request.target_words > 0:
            diff = actual_words - request.target_words
            diff_percent = abs(diff) / request.target_words * 100
            
            if diff > 0 and diff_percent > 5:
                # Over target by more than 5%
                word_count_warning = f"⚠️ Generated {actual_words} words ({diff:+d} over target). Speech may run longer than music."
            elif diff < 0 and diff_percent > 15:
                # Under target by more than 15%
                word_count_warning = f"⚠️ Generated {actual_words} words ({diff:+d} under target). Speech may end early."
        
        return GenerateTextResponse(
            text=generated_text,
            model=result["model"],
            tokens_used=result["tokens_used"],
            style=request.style,
            template=request.template,
            target_words=request.target_words,
            actual_words=actual_words,
            word_count_warning=word_count_warning,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")


@router.get("/llm/models")
async def list_models():
    """Get available LLM models."""
    models = get_available_models()
    return {
        "models": models,
        "default": "claude-3-sonnet-20240229",
    }


@router.get("/llm/styles")
async def get_styles():
    """Get available prompt styles."""
    styles = list_styles()
    return {
        "styles": styles,
        "default": "default",
    }


@router.get("/llm/templates")
async def get_templates():
    """Get available prompt templates."""
    templates = list_templates()
    return {
        "templates": templates,
        "default": "about_topic",
    }


@router.get("/llm/styles/{style_id}")
async def get_style_details(style_id: str):
    """Get the full system prompt for a style."""
    prompt = get_system_prompt(style_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Style not found")
    return {
        "id": style_id,
        "system_prompt": prompt,
    }


@router.get("/llm/reference/chaplin")
async def get_chaplin_reference():
    """Get the Great Dictator speech for reference."""
    return {
        "title": "The Great Dictator - Final Speech",
        "author": "Charlie Chaplin",
        "year": 1940,
        "text": get_chaplin_speech(),
        "word_count": len(get_chaplin_speech().split()),
    }


@router.get("/llm/calculate-words")
async def calculate_words_from_duration(
    duration_ms: int,
    voice_speed: float = 1.0,
    speech_entry_ms: int = 0,
    crossfade_ms: int = 2000,
    wpm: Optional[int] = None,
    safety_factor: Optional[float] = None,
):
    """
    Calculate target word count from audio duration with voice adjustments.
    
    Args:
        duration_ms: Duration in milliseconds
        voice_speed: ElevenLabs voice speed multiplier (0.5 to 2.0, default 1.0)
        speech_entry_ms: Delay before voice starts in ms (default 0)
        crossfade_ms: Crossfade duration at end in ms (default 2000, used by mixer only)
        wpm: Words per minute override (optional, uses default 102 if not specified)
        safety_factor: Safety buffer override (optional, uses default 1.0 if not specified)
    
    Returns:
        target_words and calculation details
    """
    if duration_ms <= 0:
        raise HTTPException(status_code=400, detail="Duration must be positive")
    
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
    
    # Calculate effective duration (only subtract speech entry, crossfade is handled by mixer)
    effective_duration_ms = duration_ms - speech_entry_ms
    effective_duration_ms = max(0, effective_duration_ms)
    
    # Format durations
    duration_seconds = duration_ms / 1000
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    
    eff_seconds = effective_duration_ms / 1000
    eff_minutes = int(eff_seconds // 60)
    eff_secs = int(eff_seconds % 60)
    
    # Estimate speech duration
    adjusted_wpm = base_wpm * voice_speed
    estimated_speech_ms = int((target_words / adjusted_wpm) * 60 * 1000) if adjusted_wpm > 0 else 0
    est_seconds = estimated_speech_ms / 1000
    est_minutes = int(est_seconds // 60)
    est_secs = int(est_seconds % 60)
    
    return {
        "duration_ms": duration_ms,
        "duration_formatted": f"{minutes}:{seconds:02d}",
        "effective_duration_ms": int(effective_duration_ms),
        "effective_duration_formatted": f"{eff_minutes}:{eff_secs:02d}",
        "target_words": target_words,
        "estimated_speech_ms": estimated_speech_ms,
        "estimated_speech_formatted": f"{est_minutes}:{est_secs:02d}",
        "params": {
            "voice_speed": voice_speed,
            "speech_entry_ms": speech_entry_ms,
            "crossfade_ms": crossfade_ms,
            "words_per_minute": base_wpm,
            "safety_factor": used_safety_factor,
        },
    }
