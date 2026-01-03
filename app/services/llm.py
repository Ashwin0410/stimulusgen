from anthropic import Anthropic
from openai import OpenAI

from app.config import ANTHROPIC_API_KEY, OPENAI_API_KEY
from app.services.prompt import get_system_prompt


def generate_text(
    prompt: str,
    model: str = "claude-3-sonnet-20240229",
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> dict:
    """
    Generate text using Claude or OpenAI.
    
    Returns dict with 'text', 'model', 'tokens_used'.
    """
    
    if not system_prompt:
        system_prompt = get_system_prompt("default")

    is_claude = "claude" in model.lower()
    is_openai = "gpt" in model.lower()
    
    if is_claude and ANTHROPIC_API_KEY:
        return _generate_with_claude(prompt, model, system_prompt, temperature, max_tokens)
    elif is_openai and OPENAI_API_KEY:
        return _generate_with_openai(prompt, model, system_prompt, temperature, max_tokens)
    elif ANTHROPIC_API_KEY:
        return _generate_with_claude(prompt, "claude-3-sonnet-20240229", system_prompt, temperature, max_tokens)
    elif OPENAI_API_KEY:
        return _generate_with_openai(prompt, "gpt-4o", system_prompt, temperature, max_tokens)
    else:
        raise ValueError("No LLM API key configured")


def _generate_with_claude(
    prompt: str,
    model: str,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> dict:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    text = response.content[0].text
    tokens_used = response.usage.input_tokens + response.usage.output_tokens
    
    return {
        "text": text,
        "model": model,
        "tokens_used": tokens_used,
    }


def _generate_with_openai(
    prompt: str,
    model: str,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> dict:
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    text = response.choices[0].message.content
    tokens_used = response.usage.total_tokens
    
    return {
        "text": text,
        "model": model,
        "tokens_used": tokens_used,
    }


def get_available_models() -> list:
    models = []
    
    if ANTHROPIC_API_KEY:
        models.extend([
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "anthropic"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "anthropic"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "provider": "anthropic"},
        ])
    
    if OPENAI_API_KEY:
        models.extend([
            {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai"},
        ])
    
    return models