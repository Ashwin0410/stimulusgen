from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MusicParams(BaseModel):
    track: str = ""
    volume_db: float = -6.0
    speech_entry_ms: int = 0
    crossfade_ms: int = 2000


class VoiceParams(BaseModel):
    model: str = "eleven_multilingual_v2"
    voice_id: str = ""
    voice_name: str = ""
    stability: float = 0.5
    similarity_boost: float = 0.75
    style_exaggeration: float = 0.0
    speaker_boost: bool = True
    speed: float = 1.0


class TextParams(BaseModel):
    source: str = "manual"
    llm_model: str = ""
    llm_temperature: float = 0.7
    llm_prompt: str = ""
    speech_text: str = ""
    target_words: Optional[int] = None  # NEW: Target word count for LLM generation


class MixParams(BaseModel):
    reverb_mix: float = 25.0
    reverb_decay: float = 1.5
    compression_ratio: float = 2.0
    deesser_threshold: float = -6.0
    eq_low_cut: int = 80
    eq_high_cut: int = 12000
    pitch_shift: int = 0
    normalization_lufs: float = -16.0


class ProsodyParams(BaseModel):
    reference: str = "none"
    intensity: float = 0.0


class StimulusCreate(BaseModel):
    id: Optional[str] = None
    music: MusicParams = MusicParams()
    voice: VoiceParams = VoiceParams()
    text: TextParams = TextParams()
    mix: MixParams = MixParams()
    prosody: ProsodyParams = ProsodyParams()
    notes: str = ""


class StimulusResponse(BaseModel):
    id: str
    created_at: datetime
    status: str
    audio_url: Optional[str] = None
    duration_ms: Optional[int] = None
    music: MusicParams
    voice: VoiceParams
    text: TextParams
    mix: MixParams
    prosody: ProsodyParams
    notes: str

    class Config:
        from_attributes = True


class StimulusList(BaseModel):
    stimuli: List[StimulusResponse]
    total: int


class LLMRequest(BaseModel):
    model: str = "claude-3-sonnet-20240229"
    prompt: str
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 500


class LLMResponse(BaseModel):
    text: str
    model: str
    tokens_used: int


class VoiceInfo(BaseModel):
    voice_id: str
    name: str
    category: str
    description: str = ""
    preview_url: str = ""


class VoiceList(BaseModel):
    voices: List[VoiceInfo]


class MusicTrack(BaseModel):
    id: str
    name: str
    folder: str
    path: str
    duration_ms: Optional[int] = None


class MusicList(BaseModel):
    tracks: List[MusicTrack]
    total: int


class ProsodyProfile(BaseModel):
    id: str
    name: str
    source_file: str
    duration_ms: int
    pitch_mean: float
    pitch_std: float
    energy_mean: float
    energy_std: float


class TemplateCreate(BaseModel):
    name: str
    music: MusicParams = MusicParams()
    voice: VoiceParams = VoiceParams()
    text: TextParams = TextParams()
    mix: MixParams = MixParams()
    prosody: ProsodyParams = ProsodyParams()


class TemplateResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    music: MusicParams
    voice: VoiceParams
    text: TextParams
    mix: MixParams
    prosody: ProsodyParams


class GenerateRequest(BaseModel):
    stimulus_id: str


class GenerateResponse(BaseModel):
    stimulus_id: str
    status: str
    audio_url: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None