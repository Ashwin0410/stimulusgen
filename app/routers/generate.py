import os
import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from app.config import ASSETS_DIR, OUTPUTS_DIR
from app.models.schemas import StimulusCreate, GenerateRequest, GenerateResponse
from app.db.crud import (
    get_stimulus, 
    create_stimulus, 
    update_stimulus_status,
    get_next_stimulus_id,
)
from app.services.tts import synthesize_speech
from app.services.mix import mix_audio, mix_voice_only
from app.services.prosody import apply_prosody
from app.utils.naming import generate_output_filename

router = APIRouter()

MUSIC_DIR = ASSETS_DIR / "music" / "tracks"


class GenerateFromParamsRequest(BaseModel):
    """Generate directly from parameters without saving to DB first."""
    stimulus_id: Optional[str] = None
    
    # Text
    speech_text: str
    
    # Voice
    voice_id: str
    voice_model: str = "eleven_multilingual_v2"
    voice_stability: float = 0.5
    voice_similarity_boost: float = 0.75
    voice_style_exaggeration: float = 0.0
    voice_speaker_boost: bool = True
    voice_speed: float = 1.0
    
    # Music (optional)
    music_track: Optional[str] = None
    music_volume_db: float = -6.0
    music_speech_entry_ms: int = 0
    music_crossfade_ms: int = 2000
    
    # Mix
    reverb_mix: float = 25.0
    reverb_decay: float = 1.5
    compression_ratio: float = 2.0
    deesser_threshold: float = -6.0
    eq_low_cut: int = 80
    eq_high_cut: int = 12000
    pitch_shift: int = 0
    normalization_lufs: float = -16.0
    
    # Prosody
    prosody_reference: str = "none"
    prosody_intensity: float = 0.0
    
    # Options
    save_to_db: bool = True


def _get_file_size(path: str) -> int:
    """Get file size in bytes, returns 0 if file doesn't exist."""
    try:
        return os.path.getsize(path) if os.path.exists(path) else 0
    except Exception:
        return 0


@router.post("/generate", response_model=GenerateResponse)
async def generate_stimulus(request: GenerateRequest):
    """Generate audio for an existing stimulus."""
    stimulus = get_stimulus(request.stimulus_id)
    if not stimulus:
        raise HTTPException(status_code=404, detail="Stimulus not found")
    
    if not stimulus.text.speech_text:
        raise HTTPException(status_code=400, detail="Stimulus has no speech text")
    
    if not stimulus.voice.voice_id:
        raise HTTPException(status_code=400, detail="Stimulus has no voice selected")
    
    try:
        # Update status to generating
        update_stimulus_status(request.stimulus_id, "generating")
        
        # Step 1: Synthesize speech
        print(f"[Generate] Synthesizing speech for {request.stimulus_id}")
        voice_path = synthesize_speech(
            text=stimulus.text.speech_text,
            voice_id=stimulus.voice.voice_id,
            model=stimulus.voice.model,
            stability=stimulus.voice.stability,
            similarity_boost=stimulus.voice.similarity_boost,
            style=stimulus.voice.style_exaggeration,
            speaker_boost=stimulus.voice.speaker_boost,
            speed=stimulus.voice.speed,
        )
        print(f"[Generate] TTS complete: {voice_path} ({_get_file_size(voice_path)} bytes)")
        
        # Step 2: Apply prosody transfer if requested
        if stimulus.prosody.reference != "none" and stimulus.prosody.intensity > 0:
            original_voice_path = voice_path
            original_size = _get_file_size(original_voice_path)
            
            print(f"[Generate] ===== PROSODY TRANSFER =====")
            print(f"[Generate] Reference: {stimulus.prosody.reference}")
            print(f"[Generate] Intensity: {stimulus.prosody.intensity}")
            print(f"[Generate] Input path: {original_voice_path}")
            print(f"[Generate] Input size: {original_size} bytes")
            
            voice_path = apply_prosody(
                voice_path=voice_path,
                reference=stimulus.prosody.reference,
                intensity=stimulus.prosody.intensity,
            )
            
            new_size = _get_file_size(voice_path)
            print(f"[Generate] Output path: {voice_path}")
            print(f"[Generate] Output size: {new_size} bytes")
            
            # Verify prosody was actually applied
            if original_voice_path == voice_path:
                print(f"[Generate] WARNING: Prosody returned SAME path! Transfer may have failed.")
            else:
                print(f"[Generate] SUCCESS: Prosody returned different path (transfer applied)")
            print(f"[Generate] ===== PROSODY TRANSFER END =====")
        else:
            print(f"[Generate] Prosody skipped: reference={stimulus.prosody.reference}, intensity={stimulus.prosody.intensity}")
        
        # Step 3: Mix with music or export voice only
        output_filename = generate_output_filename(request.stimulus_id)
        
        if stimulus.music.track:
            music_path = MUSIC_DIR / stimulus.music.track
            if not music_path.exists():
                raise HTTPException(status_code=400, detail=f"Music track not found: {stimulus.music.track}")
            
            print(f"[Generate] Mixing with music: {stimulus.music.track}")
            output_path, duration_ms = mix_audio(
                voice_path=voice_path,
                music_path=str(music_path),
                output_filename=output_filename,
                music_volume_db=stimulus.music.volume_db,
                speech_entry_ms=stimulus.music.speech_entry_ms,
                crossfade_ms=stimulus.music.crossfade_ms,
                reverb_mix=stimulus.mix.reverb_mix,
                reverb_decay=stimulus.mix.reverb_decay,
                compression_ratio=stimulus.mix.compression_ratio,
                deesser_threshold=stimulus.mix.deesser_threshold,
                eq_low_cut=stimulus.mix.eq_low_cut,
                eq_high_cut=stimulus.mix.eq_high_cut,
                pitch_shift=stimulus.mix.pitch_shift,
                normalization_lufs=stimulus.mix.normalization_lufs,
            )
        else:
            print(f"[Generate] Exporting voice only (no music)")
            output_path, duration_ms = mix_voice_only(
                voice_path=voice_path,
                output_filename=output_filename,
                reverb_mix=stimulus.mix.reverb_mix,
                reverb_decay=stimulus.mix.reverb_decay,
                compression_ratio=stimulus.mix.compression_ratio,
                deesser_threshold=stimulus.mix.deesser_threshold,
                eq_low_cut=stimulus.mix.eq_low_cut,
                eq_high_cut=stimulus.mix.eq_high_cut,
                pitch_shift=stimulus.mix.pitch_shift,
                normalization_lufs=stimulus.mix.normalization_lufs,
            )
        
        # Update status to complete
        update_stimulus_status(
            request.stimulus_id, 
            "generated", 
            audio_filename=output_filename,
            duration_ms=duration_ms
        )
        
        print(f"[Generate] Complete: {output_filename}, {duration_ms}ms")
        
        return GenerateResponse(
            stimulus_id=request.stimulus_id,
            status="generated",
            audio_url=f"/outputs/{output_filename}",
            duration_ms=duration_ms,
        )
        
    except Exception as e:
        print(f"[Generate] Error: {e}")
        traceback.print_exc()
        update_stimulus_status(request.stimulus_id, "failed")
        return GenerateResponse(
            stimulus_id=request.stimulus_id,
            status="failed",
            error=str(e),
        )


@router.post("/generate/direct", response_model=GenerateResponse)
async def generate_direct(request: GenerateFromParamsRequest):
    """Generate audio directly from parameters."""
    stimulus_id = request.stimulus_id or get_next_stimulus_id()
    
    try:
        # Save to DB if requested
        if request.save_to_db:
            from app.models.schemas import (
                MusicParams, VoiceParams, TextParams, MixParams, ProsodyParams
            )
            
            stimulus = StimulusCreate(
                id=stimulus_id,
                music=MusicParams(
                    track=request.music_track or "",
                    volume_db=request.music_volume_db,
                    speech_entry_ms=request.music_speech_entry_ms,
                    crossfade_ms=request.music_crossfade_ms,
                ),
                voice=VoiceParams(
                    model=request.voice_model,
                    voice_id=request.voice_id,
                    stability=request.voice_stability,
                    similarity_boost=request.voice_similarity_boost,
                    style_exaggeration=request.voice_style_exaggeration,
                    speaker_boost=request.voice_speaker_boost,
                    speed=request.voice_speed,
                ),
                text=TextParams(
                    source="manual",
                    speech_text=request.speech_text,
                ),
                mix=MixParams(
                    reverb_mix=request.reverb_mix,
                    reverb_decay=request.reverb_decay,
                    compression_ratio=request.compression_ratio,
                    deesser_threshold=request.deesser_threshold,
                    eq_low_cut=request.eq_low_cut,
                    eq_high_cut=request.eq_high_cut,
                    pitch_shift=request.pitch_shift,
                    normalization_lufs=request.normalization_lufs,
                ),
                prosody=ProsodyParams(
                    reference=request.prosody_reference,
                    intensity=request.prosody_intensity,
                ),
            )
            create_stimulus(stimulus)
            update_stimulus_status(stimulus_id, "generating")
        
        # Step 1: Synthesize
        print(f"[Generate] Synthesizing speech for {stimulus_id}")
        voice_path = synthesize_speech(
            text=request.speech_text,
            voice_id=request.voice_id,
            model=request.voice_model,
            stability=request.voice_stability,
            similarity_boost=request.voice_similarity_boost,
            style=request.voice_style_exaggeration,
            speaker_boost=request.voice_speaker_boost,
            speed=request.voice_speed,
        )
        print(f"[Generate] TTS complete: {voice_path} ({_get_file_size(voice_path)} bytes)")
        
        # Step 2: Prosody
        if request.prosody_reference != "none" and request.prosody_intensity > 0:
            original_voice_path = voice_path
            original_size = _get_file_size(original_voice_path)
            
            print(f"[Generate] ===== PROSODY TRANSFER =====")
            print(f"[Generate] Reference: {request.prosody_reference}")
            print(f"[Generate] Intensity: {request.prosody_intensity}")
            print(f"[Generate] Input path: {original_voice_path}")
            print(f"[Generate] Input size: {original_size} bytes")
            
            voice_path = apply_prosody(
                voice_path=voice_path,
                reference=request.prosody_reference,
                intensity=request.prosody_intensity,
            )
            
            new_size = _get_file_size(voice_path)
            print(f"[Generate] Output path: {voice_path}")
            print(f"[Generate] Output size: {new_size} bytes")
            
            # Verify prosody was actually applied
            if original_voice_path == voice_path:
                print(f"[Generate] WARNING: Prosody returned SAME path! Transfer may have failed.")
            else:
                print(f"[Generate] SUCCESS: Prosody returned different path (transfer applied)")
            print(f"[Generate] ===== PROSODY TRANSFER END =====")
        else:
            print(f"[Generate] Prosody skipped: reference={request.prosody_reference}, intensity={request.prosody_intensity}")
        
        # Step 3: Mix
        output_filename = generate_output_filename(stimulus_id)
        
        if request.music_track:
            music_path = MUSIC_DIR / request.music_track
            if not music_path.exists():
                raise HTTPException(status_code=400, detail=f"Music not found: {request.music_track}")
            
            print(f"[Generate] Mixing with music: {request.music_track}")
            output_path, duration_ms = mix_audio(
                voice_path=voice_path,
                music_path=str(music_path),
                output_filename=output_filename,
                music_volume_db=request.music_volume_db,
                speech_entry_ms=request.music_speech_entry_ms,
                crossfade_ms=request.music_crossfade_ms,
                reverb_mix=request.reverb_mix,
                reverb_decay=request.reverb_decay,
                compression_ratio=request.compression_ratio,
                deesser_threshold=request.deesser_threshold,
                eq_low_cut=request.eq_low_cut,
                eq_high_cut=request.eq_high_cut,
                pitch_shift=request.pitch_shift,
                normalization_lufs=request.normalization_lufs,
            )
        else:
            print(f"[Generate] Voice only (no music)")
            output_path, duration_ms = mix_voice_only(
                voice_path=voice_path,
                output_filename=output_filename,
                reverb_mix=request.reverb_mix,
                reverb_decay=request.reverb_decay,
                compression_ratio=request.compression_ratio,
                deesser_threshold=request.deesser_threshold,
                eq_low_cut=request.eq_low_cut,
                eq_high_cut=request.eq_high_cut,
                pitch_shift=request.pitch_shift,
                normalization_lufs=request.normalization_lufs,
            )
        
        if request.save_to_db:
            update_stimulus_status(stimulus_id, "generated", output_filename, duration_ms)
        
        print(f"[Generate] Complete: {output_filename}, {duration_ms}ms")
        
        return GenerateResponse(
            stimulus_id=stimulus_id,
            status="generated",
            audio_url=f"/outputs/{output_filename}",
            duration_ms=duration_ms,
        )
        
    except Exception as e:
        print(f"[Generate] Error: {e}")
        traceback.print_exc()
        if request.save_to_db:
            update_stimulus_status(stimulus_id, "failed")
        return GenerateResponse(
            stimulus_id=stimulus_id,
            status="failed",
            error=str(e),
        )


@router.get("/generate/status/{stimulus_id}")
async def get_generation_status(stimulus_id: str):
    """Check generation status for a stimulus."""
    stimulus = get_stimulus(stimulus_id)
    if not stimulus:
        raise HTTPException(status_code=404, detail="Stimulus not found")
    
    return {
        "stimulus_id": stimulus_id,
        "status": stimulus.status,
        "audio_url": stimulus.audio_url,
        "duration_ms": stimulus.duration_ms,
    }
