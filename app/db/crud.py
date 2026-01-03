import json
import uuid
from datetime import datetime
from typing import Optional, List
from app.db.database import get_db
from app.models.schemas import (
    StimulusCreate, StimulusResponse, 
    MusicParams, VoiceParams, TextParams, MixParams, ProsodyParams,
    TemplateCreate, TemplateResponse
)


def _row_to_stimulus(row) -> StimulusResponse:
    return StimulusResponse(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        status=row["status"] or "draft",
        audio_url=f"/outputs/{row['audio_filename']}" if row["audio_filename"] else None,
        duration_ms=row["duration_ms"],
        music=MusicParams(
            track=row["music_track"] or "",
            volume_db=row["music_volume_db"] or -6.0,
            speech_entry_ms=row["music_speech_entry_ms"] or 0,
            crossfade_ms=row["music_crossfade_ms"] or 2000
        ),
        voice=VoiceParams(
            model=row["voice_model"] or "eleven_multilingual_v2",
            voice_id=row["voice_id"] or "",
            voice_name=row["voice_name"] or "",
            stability=row["voice_stability"] or 0.5,
            similarity_boost=row["voice_similarity_boost"] or 0.75,
            style_exaggeration=row["voice_style_exaggeration"] or 0.0,
            speaker_boost=bool(row["voice_speaker_boost"]),
            speed=row["voice_speed"] or 1.0
        ),
        text=TextParams(
            source=row["text_source"] or "manual",
            llm_model=row["text_llm_model"] or "",
            llm_temperature=row["text_llm_temperature"] or 0.7,
            llm_prompt=row["text_llm_prompt"] or "",
            speech_text=row["text_speech_text"] or ""
        ),
        mix=MixParams(
            reverb_mix=row["mix_reverb_mix"] or 25.0,
            reverb_decay=row["mix_reverb_decay"] or 1.5,
            compression_ratio=row["mix_compression_ratio"] or 2.0,
            deesser_threshold=row["mix_deesser_threshold"] or -6.0,
            eq_low_cut=row["mix_eq_low_cut"] or 80,
            eq_high_cut=row["mix_eq_high_cut"] or 12000,
            pitch_shift=row["mix_pitch_shift"] or 0,
            normalization_lufs=row["mix_normalization_lufs"] or -16.0
        ),
        prosody=ProsodyParams(
            reference=row["prosody_reference"] or "none",
            intensity=row["prosody_intensity"] or 0.0
        ),
        notes=row["notes"] or ""
    )


def _row_to_template(row) -> TemplateResponse:
    return TemplateResponse(
        id=row["id"],
        name=row["name"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        music=MusicParams(
            track=row["music_track"] or "",
            volume_db=row["music_volume_db"] or -6.0,
            speech_entry_ms=row["music_speech_entry_ms"] or 0,
            crossfade_ms=row["music_crossfade_ms"] or 2000
        ),
        voice=VoiceParams(
            model=row["voice_model"] or "eleven_multilingual_v2",
            voice_id=row["voice_id"] or "",
            voice_name=row["voice_name"] or "",
            stability=row["voice_stability"] or 0.5,
            similarity_boost=row["voice_similarity_boost"] or 0.75,
            style_exaggeration=row["voice_style_exaggeration"] or 0.0,
            speaker_boost=bool(row["voice_speaker_boost"]),
            speed=row["voice_speed"] or 1.0
        ),
        text=TextParams(
            source=row["text_source"] or "manual",
            llm_model=row["text_llm_model"] or "",
            llm_temperature=row["text_llm_temperature"] or 0.7,
            llm_prompt=row["text_llm_prompt"] or "",
            speech_text=""
        ),
        mix=MixParams(
            reverb_mix=row["mix_reverb_mix"] or 25.0,
            reverb_decay=row["mix_reverb_decay"] or 1.5,
            compression_ratio=row["mix_compression_ratio"] or 2.0,
            deesser_threshold=row["mix_deesser_threshold"] or -6.0,
            eq_low_cut=row["mix_eq_low_cut"] or 80,
            eq_high_cut=row["mix_eq_high_cut"] or 12000,
            pitch_shift=row["mix_pitch_shift"] or 0,
            normalization_lufs=row["mix_normalization_lufs"] or -16.0
        ),
        prosody=ProsodyParams(
            reference=row["prosody_reference"] or "none",
            intensity=row["prosody_intensity"] or 0.0
        )
    )


def get_next_stimulus_id() -> str:
    with get_db() as conn:
        row = conn.execute("""
            SELECT id FROM stimuli 
            WHERE id LIKE 'STIM_%' 
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        
        if row:
            try:
                num = int(row["id"].split("_")[1]) + 1
            except (IndexError, ValueError):
                num = 1
        else:
            num = 1
        
        return f"STIM_{num:03d}"


def create_stimulus(stimulus: StimulusCreate) -> str:
    stimulus_id = stimulus.id or get_next_stimulus_id()
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO stimuli (
                id, status,
                music_track, music_volume_db, music_speech_entry_ms, music_crossfade_ms,
                voice_model, voice_id, voice_name, voice_stability, voice_similarity_boost,
                voice_style_exaggeration, voice_speaker_boost, voice_speed,
                text_source, text_llm_model, text_llm_temperature, text_llm_prompt, text_speech_text,
                mix_reverb_mix, mix_reverb_decay, mix_compression_ratio, mix_deesser_threshold,
                mix_eq_low_cut, mix_eq_high_cut, mix_pitch_shift, mix_normalization_lufs,
                prosody_reference, prosody_intensity,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stimulus_id, "draft",
            stimulus.music.track, stimulus.music.volume_db, stimulus.music.speech_entry_ms, stimulus.music.crossfade_ms,
            stimulus.voice.model, stimulus.voice.voice_id, stimulus.voice.voice_name, stimulus.voice.stability,
            stimulus.voice.similarity_boost, stimulus.voice.style_exaggeration, int(stimulus.voice.speaker_boost), stimulus.voice.speed,
            stimulus.text.source, stimulus.text.llm_model, stimulus.text.llm_temperature, stimulus.text.llm_prompt, stimulus.text.speech_text,
            stimulus.mix.reverb_mix, stimulus.mix.reverb_decay, stimulus.mix.compression_ratio, stimulus.mix.deesser_threshold,
            stimulus.mix.eq_low_cut, stimulus.mix.eq_high_cut, stimulus.mix.pitch_shift, stimulus.mix.normalization_lufs,
            stimulus.prosody.reference, stimulus.prosody.intensity,
            stimulus.notes
        ))
    
    return stimulus_id


def get_stimulus(stimulus_id: str) -> Optional[StimulusResponse]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM stimuli WHERE id = ?", (stimulus_id,)).fetchone()
        if row:
            return _row_to_stimulus(row)
    return None


def get_all_stimuli() -> List[StimulusResponse]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM stimuli ORDER BY created_at DESC").fetchall()
        return [_row_to_stimulus(row) for row in rows]


def update_stimulus(stimulus_id: str, stimulus: StimulusCreate) -> bool:
    with get_db() as conn:
        result = conn.execute("""
            UPDATE stimuli SET
                music_track = ?, music_volume_db = ?, music_speech_entry_ms = ?, music_crossfade_ms = ?,
                voice_model = ?, voice_id = ?, voice_name = ?, voice_stability = ?, voice_similarity_boost = ?,
                voice_style_exaggeration = ?, voice_speaker_boost = ?, voice_speed = ?,
                text_source = ?, text_llm_model = ?, text_llm_temperature = ?, text_llm_prompt = ?, text_speech_text = ?,
                mix_reverb_mix = ?, mix_reverb_decay = ?, mix_compression_ratio = ?, mix_deesser_threshold = ?,
                mix_eq_low_cut = ?, mix_eq_high_cut = ?, mix_pitch_shift = ?, mix_normalization_lufs = ?,
                prosody_reference = ?, prosody_intensity = ?,
                notes = ?
            WHERE id = ?
        """, (
            stimulus.music.track, stimulus.music.volume_db, stimulus.music.speech_entry_ms, stimulus.music.crossfade_ms,
            stimulus.voice.model, stimulus.voice.voice_id, stimulus.voice.voice_name, stimulus.voice.stability,
            stimulus.voice.similarity_boost, stimulus.voice.style_exaggeration, int(stimulus.voice.speaker_boost), stimulus.voice.speed,
            stimulus.text.source, stimulus.text.llm_model, stimulus.text.llm_temperature, stimulus.text.llm_prompt, stimulus.text.speech_text,
            stimulus.mix.reverb_mix, stimulus.mix.reverb_decay, stimulus.mix.compression_ratio, stimulus.mix.deesser_threshold,
            stimulus.mix.eq_low_cut, stimulus.mix.eq_high_cut, stimulus.mix.pitch_shift, stimulus.mix.normalization_lufs,
            stimulus.prosody.reference, stimulus.prosody.intensity,
            stimulus.notes,
            stimulus_id
        ))
        return result.rowcount > 0


def update_stimulus_status(stimulus_id: str, status: str, audio_filename: str = None, duration_ms: int = None):
    with get_db() as conn:
        if audio_filename:
            conn.execute(
                "UPDATE stimuli SET status = ?, audio_filename = ?, duration_ms = ? WHERE id = ?",
                (status, audio_filename, duration_ms, stimulus_id)
            )
        else:
            conn.execute(
                "UPDATE stimuli SET status = ? WHERE id = ?",
                (status, stimulus_id)
            )


def delete_stimulus(stimulus_id: str) -> bool:
    with get_db() as conn:
        result = conn.execute("DELETE FROM stimuli WHERE id = ?", (stimulus_id,))
        return result.rowcount > 0


# Template CRUD

def create_template(template: TemplateCreate) -> str:
    template_id = str(uuid.uuid4())[:8]
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO templates (
                id, name,
                music_track, music_volume_db, music_speech_entry_ms, music_crossfade_ms,
                voice_model, voice_id, voice_name, voice_stability, voice_similarity_boost,
                voice_style_exaggeration, voice_speaker_boost, voice_speed,
                text_source, text_llm_model, text_llm_temperature, text_llm_prompt,
                mix_reverb_mix, mix_reverb_decay, mix_compression_ratio, mix_deesser_threshold,
                mix_eq_low_cut, mix_eq_high_cut, mix_pitch_shift, mix_normalization_lufs,
                prosody_reference, prosody_intensity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template_id, template.name,
            template.music.track, template.music.volume_db, template.music.speech_entry_ms, template.music.crossfade_ms,
            template.voice.model, template.voice.voice_id, template.voice.voice_name, template.voice.stability,
            template.voice.similarity_boost, template.voice.style_exaggeration, int(template.voice.speaker_boost), template.voice.speed,
            template.text.source, template.text.llm_model, template.text.llm_temperature, template.text.llm_prompt,
            template.mix.reverb_mix, template.mix.reverb_decay, template.mix.compression_ratio, template.mix.deesser_threshold,
            template.mix.eq_low_cut, template.mix.eq_high_cut, template.mix.pitch_shift, template.mix.normalization_lufs,
            template.prosody.reference, template.prosody.intensity
        ))
    
    return template_id


def get_template(template_id: str) -> Optional[TemplateResponse]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
        if row:
            return _row_to_template(row)
    return None


def get_all_templates() -> List[TemplateResponse]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM templates ORDER BY created_at DESC").fetchall()
        return [_row_to_template(row) for row in rows]


def delete_template(template_id: str) -> bool:
    with get_db() as conn:
        result = conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        return result.rowcount > 0