import csv
import json
import io
import zipfile
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import OUTPUTS_DIR
from app.db.crud import get_all_stimuli, get_stimulus

router = APIRouter()


@router.get("/export/csv")
async def export_csv():
    """Export all stimuli as CSV."""
    stimuli = get_all_stimuli()
    
    if not stimuli:
        raise HTTPException(status_code=404, detail="No stimuli to export")
    
    # Create CSV in memory
    output = io.StringIO()
    
    # Define columns
    columns = [
        "id", "created_at", "status", "audio_url", "duration_ms",
        "music_track", "music_volume_db", "music_speech_entry_ms", "music_crossfade_ms",
        "voice_model", "voice_id", "voice_name", "voice_stability", "voice_similarity_boost",
        "voice_style_exaggeration", "voice_speaker_boost", "voice_speed",
        "text_source", "text_llm_model", "text_llm_temperature", "text_speech_text",
        "mix_reverb_mix", "mix_reverb_decay", "mix_compression_ratio", "mix_deesser_threshold",
        "mix_eq_low_cut", "mix_eq_high_cut", "mix_pitch_shift", "mix_normalization_lufs",
        "prosody_reference", "prosody_intensity",
        "notes"
    ]
    
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    
    for s in stimuli:
        row = {
            "id": s.id,
            "created_at": s.created_at.isoformat(),
            "status": s.status,
            "audio_url": s.audio_url,
            "duration_ms": s.duration_ms,
            "music_track": s.music.track,
            "music_volume_db": s.music.volume_db,
            "music_speech_entry_ms": s.music.speech_entry_ms,
            "music_crossfade_ms": s.music.crossfade_ms,
            "voice_model": s.voice.model,
            "voice_id": s.voice.voice_id,
            "voice_name": s.voice.voice_name,
            "voice_stability": s.voice.stability,
            "voice_similarity_boost": s.voice.similarity_boost,
            "voice_style_exaggeration": s.voice.style_exaggeration,
            "voice_speaker_boost": s.voice.speaker_boost,
            "voice_speed": s.voice.speed,
            "text_source": s.text.source,
            "text_llm_model": s.text.llm_model,
            "text_llm_temperature": s.text.llm_temperature,
            "text_speech_text": s.text.speech_text[:500] if s.text.speech_text else "",
            "mix_reverb_mix": s.mix.reverb_mix,
            "mix_reverb_decay": s.mix.reverb_decay,
            "mix_compression_ratio": s.mix.compression_ratio,
            "mix_deesser_threshold": s.mix.deesser_threshold,
            "mix_eq_low_cut": s.mix.eq_low_cut,
            "mix_eq_high_cut": s.mix.eq_high_cut,
            "mix_pitch_shift": s.mix.pitch_shift,
            "mix_normalization_lufs": s.mix.normalization_lufs,
            "prosody_reference": s.prosody.reference,
            "prosody_intensity": s.prosody.intensity,
            "notes": s.notes,
        }
        writer.writerow(row)
    
    output.seek(0)
    
    filename = f"stimuli_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/json")
async def export_json():
    """Export all stimuli as JSON."""
    stimuli = get_all_stimuli()
    
    if not stimuli:
        raise HTTPException(status_code=404, detail="No stimuli to export")
    
    data = {
        "exported_at": datetime.now().isoformat(),
        "total": len(stimuli),
        "stimuli": [
            {
                "id": s.id,
                "created_at": s.created_at.isoformat(),
                "status": s.status,
                "audio_url": s.audio_url,
                "duration_ms": s.duration_ms,
                "music": s.music.model_dump(),
                "voice": s.voice.model_dump(),
                "text": s.text.model_dump(),
                "mix": s.mix.model_dump(),
                "prosody": s.prosody.model_dump(),
                "notes": s.notes,
            }
            for s in stimuli
        ]
    }
    
    output = json.dumps(data, indent=2)
    filename = f"stimuli_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        iter([output]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/stimulus/{stimulus_id}")
async def export_single_stimulus(stimulus_id: str, include_audio: bool = True):
    """Export a single stimulus with its audio file."""
    stimulus = get_stimulus(stimulus_id)
    if not stimulus:
        raise HTTPException(status_code=404, detail="Stimulus not found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add metadata JSON
        metadata = {
            "id": stimulus.id,
            "created_at": stimulus.created_at.isoformat(),
            "status": stimulus.status,
            "duration_ms": stimulus.duration_ms,
            "music": stimulus.music.model_dump(),
            "voice": stimulus.voice.model_dump(),
            "text": stimulus.text.model_dump(),
            "mix": stimulus.mix.model_dump(),
            "prosody": stimulus.prosody.model_dump(),
            "notes": stimulus.notes,
        }
        zf.writestr(f"{stimulus_id}_metadata.json", json.dumps(metadata, indent=2))
        
        # Add speech text as separate file
        if stimulus.text.speech_text:
            zf.writestr(f"{stimulus_id}_speech.txt", stimulus.text.speech_text)
        
        # Add audio file if available and requested
        if include_audio and stimulus.audio_url:
            audio_filename = stimulus.audio_url.split("/")[-1]
            audio_path = OUTPUTS_DIR / audio_filename
            if audio_path.exists():
                zf.write(audio_path, audio_filename)
    
    zip_buffer.seek(0)
    filename = f"{stimulus_id}_export.zip"
    
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/batch")
async def export_batch(stimulus_ids: str, include_audio: bool = True):
    """Export multiple stimuli as a ZIP file."""
    ids = [s.strip() for s in stimulus_ids.split(",")]
    
    if not ids:
        raise HTTPException(status_code=400, detail="No stimulus IDs provided")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        all_metadata = []
        
        for stimulus_id in ids:
            stimulus = get_stimulus(stimulus_id)
            if not stimulus:
                continue
            
            metadata = {
                "id": stimulus.id,
                "created_at": stimulus.created_at.isoformat(),
                "status": stimulus.status,
                "duration_ms": stimulus.duration_ms,
                "music": stimulus.music.model_dump(),
                "voice": stimulus.voice.model_dump(),
                "text": stimulus.text.model_dump(),
                "mix": stimulus.mix.model_dump(),
                "prosody": stimulus.prosody.model_dump(),
                "notes": stimulus.notes,
            }
            all_metadata.append(metadata)
            
            # Add audio file
            if include_audio and stimulus.audio_url:
                audio_filename = stimulus.audio_url.split("/")[-1]
                audio_path = OUTPUTS_DIR / audio_filename
                if audio_path.exists():
                    zf.write(audio_path, f"audio/{audio_filename}")
        
        # Add combined metadata
        zf.writestr("metadata.json", json.dumps({
            "exported_at": datetime.now().isoformat(),
            "total": len(all_metadata),
            "stimuli": all_metadata,
        }, indent=2))
    
    zip_buffer.seek(0)
    filename = f"stimuli_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )