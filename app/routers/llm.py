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
    calculate_target_words,  # NEW: Import helper function
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
    target_words: Optional[int] = None  # NEW: Target word count


class GenerateTextResponse(BaseModel):
    text: str
    model: str
    tokens_used: int
    style: str
    template: str
    target_words: Optional[int] = None  # NEW: Return target used
    actual_words: Optional[int] = None  # NEW: Return actual word count


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
            target_words=request.target_words,  # NEW: Pass target_words
        )
        
        # Generate text
        result = generate_text(
            prompt=user_prompt,
            model=request.model,
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        # NEW: Calculate actual word count
        generated_text = result["text"]
        actual_words = len(generated_text.split()) if generated_text else 0
        
        return GenerateTextResponse(
            text=generated_text,
            model=result["model"],
            tokens_used=result["tokens_used"],
            style=request.style,
            template=request.template,
            target_words=request.target_words,  # NEW: Return target
            actual_words=actual_words,  # NEW: Return actual count
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


# NEW: Endpoint to calculate target words from duration
@router.get("/llm/calculate-words")
async def calculate_words_from_duration(duration_ms: int, wpm: int = 140):
    """
    Calculate target word count from audio duration.
    
    Args:
        duration_ms: Duration in milliseconds
        wpm: Words per minute (default 140 for clear narration)
    
    Returns:
        target_words and estimated duration
    """
    if duration_ms <= 0:
        raise HTTPException(status_code=400, detail="Duration must be positive")
    
    target_words = calculate_target_words(duration_ms, wpm)
    
    # Calculate estimated duration string
    duration_seconds = duration_ms / 1000
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    
    return {
        "duration_ms": duration_ms,
        "words_per_minute": wpm,
        "target_words": target_words,
        "duration_formatted": f"{minutes}:{seconds:02d}",
    }