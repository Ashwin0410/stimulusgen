import sqlite3
from contextlib import contextmanager
from app.config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_tables():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stimuli (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'draft',
                audio_filename TEXT,
                duration_ms INTEGER,
                
                music_track TEXT,
                music_volume_db REAL DEFAULT -6,
                music_speech_entry_ms INTEGER DEFAULT 0,
                music_crossfade_ms INTEGER DEFAULT 2000,
                
                voice_model TEXT DEFAULT 'eleven_multilingual_v2',
                voice_id TEXT,
                voice_name TEXT,
                voice_stability REAL DEFAULT 0.5,
                voice_similarity_boost REAL DEFAULT 0.75,
                voice_style_exaggeration REAL DEFAULT 0,
                voice_speaker_boost INTEGER DEFAULT 1,
                voice_speed REAL DEFAULT 1.0,
                
                text_source TEXT DEFAULT 'manual',
                text_llm_model TEXT,
                text_llm_temperature REAL,
                text_llm_prompt TEXT,
                text_speech_text TEXT,
                
                mix_reverb_mix REAL DEFAULT 25,
                mix_reverb_decay REAL DEFAULT 1.5,
                mix_compression_ratio REAL DEFAULT 2,
                mix_deesser_threshold REAL DEFAULT -6,
                mix_eq_low_cut INTEGER DEFAULT 80,
                mix_eq_high_cut INTEGER DEFAULT 12000,
                mix_pitch_shift INTEGER DEFAULT 0,
                mix_normalization_lufs REAL DEFAULT -16,
                
                prosody_reference TEXT DEFAULT 'none',
                prosody_intensity REAL DEFAULT 0,
                
                notes TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                music_track TEXT,
                music_volume_db REAL DEFAULT -6,
                music_speech_entry_ms INTEGER DEFAULT 0,
                music_crossfade_ms INTEGER DEFAULT 2000,
                
                voice_model TEXT DEFAULT 'eleven_multilingual_v2',
                voice_id TEXT,
                voice_name TEXT,
                voice_stability REAL DEFAULT 0.5,
                voice_similarity_boost REAL DEFAULT 0.75,
                voice_style_exaggeration REAL DEFAULT 0,
                voice_speaker_boost INTEGER DEFAULT 1,
                voice_speed REAL DEFAULT 1.0,
                
                text_source TEXT DEFAULT 'manual',
                text_llm_model TEXT,
                text_llm_temperature REAL,
                text_llm_prompt TEXT,
                
                mix_reverb_mix REAL DEFAULT 25,
                mix_reverb_decay REAL DEFAULT 1.5,
                mix_compression_ratio REAL DEFAULT 2,
                mix_deesser_threshold REAL DEFAULT -6,
                mix_eq_low_cut INTEGER DEFAULT 80,
                mix_eq_high_cut INTEGER DEFAULT 12000,
                mix_pitch_shift INTEGER DEFAULT 0,
                mix_normalization_lufs REAL DEFAULT -16,
                
                prosody_reference TEXT DEFAULT 'none',
                prosody_intensity REAL DEFAULT 0
            )
        """)