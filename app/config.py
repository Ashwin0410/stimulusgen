import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Detect if running on Render
IS_RENDER = os.getenv("RENDER", "false").lower() == "true"

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent

# On Render, use persistent disk for data that needs to survive deploys
if IS_RENDER:
    PERSISTENT_DIR = Path("/data")
    DATA_DIR = PERSISTENT_DIR / "data"
    UPLOADS_DIR = PERSISTENT_DIR / "uploads"
    OUTPUTS_DIR = PERSISTENT_DIR / "outputs"
else:
    DATA_DIR = BASE_DIR / "data"
    UPLOADS_DIR = BASE_DIR / "uploads"
    OUTPUTS_DIR = DATA_DIR / "outputs"

# Assets stay in app directory (bundled with code)
ASSETS_DIR = BASE_DIR / "assets"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "music").mkdir(exist_ok=True)
(UPLOADS_DIR / "prosody").mkdir(exist_ok=True)
(ASSETS_DIR / "music" / "tracks").mkdir(parents=True, exist_ok=True)
(ASSETS_DIR / "prosody").mkdir(parents=True, exist_ok=True)

# ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# LLM
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Default voices
VOICE_DEFAULT = os.getenv("VOICE_DEFAULT", "qNkzaJoHLLdpvgh5tISm")
VOICE_SEVAN = os.getenv("VOICE_SEVAN", "bTEswxYhpv7UDkQg5VRu")
VOICE_CARTER = os.getenv("VOICE_CARTER", "bU2VfAdiOb2Gv2eZWlFq")
VOICE_JJ = os.getenv("VOICE_JJ", "9DY0k6JS3lZaUAIvDlAA")

# FFmpeg - Render has it pre-installed, Windows needs path
if IS_RENDER:
    FFMPEG_BIN = "ffmpeg"
    FFPROBE_BIN = "ffprobe"
else:
    _ffmpeg_env = os.getenv("FFMPEG_BIN", "")
    _ffprobe_env = os.getenv("FFPROBE_BIN", "")
    
    if _ffmpeg_env and Path(_ffmpeg_env).exists():
        FFMPEG_BIN = _ffmpeg_env
    else:
        FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"
    
    if _ffprobe_env and Path(_ffprobe_env).exists():
        FFPROBE_BIN = _ffprobe_env
    else:
        FFPROBE_BIN = shutil.which("ffprobe") or "ffprobe"

# Database - stored in DATA_DIR (persistent on Render)
DATABASE_PATH = DATA_DIR / "stimuli.db"

# Debug
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
