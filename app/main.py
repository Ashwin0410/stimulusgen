from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import OUTPUTS_DIR, ASSETS_DIR
from app.db.database import create_tables

app = FastAPI(
    title="Chills Stimulus Generator",
    description="Generate and manage audio stimuli for chills research",
    version="1.0.0"
)


@app.on_event("startup")
async def startup():
    create_tables()


# Static files (CSS, JS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve generated outputs
if OUTPUTS_DIR.exists():
    app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# Serve music assets
MUSIC_DIR = ASSETS_DIR / "music" / "tracks"
if MUSIC_DIR.exists():
    app.mount("/assets/music", StaticFiles(directory=MUSIC_DIR), name="music")

# Serve prosody assets
PROSODY_DIR = ASSETS_DIR / "prosody"
if PROSODY_DIR.exists():
    app.mount("/assets/prosody", StaticFiles(directory=PROSODY_DIR), name="prosody")


# Page routes
@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "pages" / "index.html")


@app.get("/generator")
async def generator():
    return FileResponse(STATIC_DIR / "pages" / "generator.html")


@app.get("/library")
async def library():
    return FileResponse(STATIC_DIR / "pages" / "library.html")


@app.get("/settings")
async def settings_page():
    return FileResponse(STATIC_DIR / "pages" / "settings.html")


# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}


# API Routers
from app.routers import voices, music, llm, stimuli, generate, export, templates, prosody

app.include_router(voices.router, prefix="/api", tags=["voices"])
app.include_router(music.router, prefix="/api", tags=["music"])
app.include_router(llm.router, prefix="/api", tags=["llm"])
app.include_router(stimuli.router, prefix="/api", tags=["stimuli"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(templates.router, prefix="/api", tags=["templates"])
app.include_router(prosody.router, prefix="/api", tags=["prosody"])