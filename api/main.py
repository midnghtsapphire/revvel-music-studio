"""
Revvel Music Studio - FastAPI Server
======================================

RESTful API for the Revvel Music Studio audio processing engine.
Provides endpoints for cleanup, mastering, stem separation,
voice synthesis, video generation, and distribution preparation.

Token-based authentication (JWT) protects all endpoints.

Artist: Revvel
Label: HOTRS (House of the Rising Sun)
Audio processing provided by free and open-source libraries.
"""

import os
import sys
import uuid
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# JWT
from jose import JWTError, jwt
from passlib.context import CryptContext

# Add parent to path for engine imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Configuration ───────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get("REVVEL_SECRET_KEY", "hotrs-revvel-studio-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "output")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Default credentials (change in production)
DEFAULT_USERS = {
    "revvel": {
        "username": "revvel",
        "hashed_password": "",  # Will be set on first run
        "full_name": "Revvel",
        "label": "HOTRS - House of the Rising Sun",
        "role": "admin",
    }
}

# ─── App Setup ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Revvel Music Studio API",
    description=(
        "Comprehensive music production and distribution API for artist Revvel "
        "and label HOTRS (House of the Rising Sun). "
        "Audio processing provided by free and open-source libraries."
    ),
    version="1.0.0",
    contact={
        "name": "HOTRS - House of the Rising Sun",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash default password on startup
DEFAULT_USERS["revvel"]["hashed_password"] = pwd_context.hash("hotrs2026")

# ─── Auth Models ─────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    artist: str
    label: str

class UserInfo(BaseModel):
    username: str
    full_name: str
    label: str
    role: str

# ─── Request/Response Models ─────────────────────────────────────────────────

class CleanupRequest(BaseModel):
    noise_reduce: bool = True
    noise_reduce_strength: float = Field(0.75, ge=0.0, le=1.0)
    remove_pops: bool = True
    pop_threshold: float = Field(3.5, ge=1.0, le=10.0)
    deess: bool = True
    remove_hum: bool = True
    hum_frequency: float = Field(60.0, description="60Hz (US) or 50Hz (EU)")
    pitch_correct: bool = False
    pitch_correction_strength: float = Field(0.8, ge=0.0, le=1.0)
    pitch_scale: str = "chromatic"
    pitch_key: str = "C"
    target_sample_rate: int = Field(96000, description="Target sample rate (96kHz for ~97kHz lossless)")
    output_format: str = Field("wav", description="wav or flac")

class MasteringRequest(BaseModel):
    preset: str = Field("default", description="Preset: default, warm, bright, punchy, gentle, kpop, cinematic, indie_folk")
    target_lufs: float = Field(-14.0, description="Target loudness in LUFS")
    target_sample_rate: int = 96000
    output_format: str = "wav"
    stereo_width: float = Field(1.2, ge=0.5, le=2.0)

class SeparationRequest(BaseModel):
    model: str = Field("htdemucs", description="Demucs model: htdemucs, htdemucs_ft, mdx_extra")
    two_stems: Optional[str] = Field(None, description="Split into two stems only (e.g., 'vocals')")

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    voice: str = Field("en-US-GuyNeural", description="Voice name for TTS")
    speed: float = Field(1.0, ge=0.5, le=2.0)

class VideoRequest(BaseModel):
    title: str = Field("", description="Video title overlay")
    artist: str = Field("Revvel", description="Artist name overlay")
    video_type: str = Field("visualizer", description="Video type: visualizer, static, spectrum")
    width: int = Field(1920, description="Video width")
    height: int = Field(1080, description="Video height")

class DistributionRequest(BaseModel):
    title: str = Field(..., description="Release title")
    artist: str = Field("Revvel", description="Artist name")
    label: str = Field("HOTRS - House of the Rising Sun", description="Label name")
    release_type: str = Field("single", description="single, ep, or album")
    genre: str = Field("Alt Pop", description="Primary genre")
    distributor: str = Field("landr", description="Target distributor: landr, ditto, distrokid, cdbaby, amuse")
    release_date: str = Field("", description="Release date (YYYY-MM-DD)")
    track_titles: List[str] = Field(default_factory=list, description="List of track titles")
    description: str = Field("", description="Release description")
    seo_words: str = Field("", description="SEO-maximized keywords")

class ProcessingResponse(BaseModel):
    success: bool
    message: str
    output_file: Optional[str] = None
    download_url: Optional[str] = None
    details: dict = {}

# ─── Auth Functions ──────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None or username not in DEFAULT_USERS:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = DEFAULT_USERS[username]
        return UserInfo(
            username=user["username"],
            full_name=user["full_name"],
            label=user["label"],
            role=user["role"],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def save_upload(upload: UploadFile) -> str:
    """Save an uploaded file and return its path."""
    file_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(upload.filename or "audio.wav")[1]
    filepath = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    with open(filepath, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return filepath

# ─── Auth Endpoints ──────────────────────────────────────────────────────────

@app.post("/auth/token", response_model=TokenResponse, tags=["Authentication"])
async def login(request: TokenRequest):
    """
    Obtain a JWT access token.

    Default credentials:
    - Username: revvel
    - Password: hotrs2026
    """
    user = DEFAULT_USERS.get(request.username)
    if not user or not pwd_context.verify(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": request.username})
    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        artist=user["full_name"],
        label=user["label"],
    )


@app.get("/auth/me", response_model=UserInfo, tags=["Authentication"])
async def get_current_user(user: UserInfo = Depends(verify_token)):
    """Get current authenticated user info."""
    return user

# ─── Health & Info ───────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
async def root():
    return {
        "name": "Revvel Music Studio API",
        "version": "1.0.0",
        "artist": "Revvel",
        "label": "HOTRS - House of the Rising Sun",
        "attribution": "Audio processing provided by free and open-source libraries: "
                       "librosa, noisereduce, pydub, demucs, moviepy, and ffmpeg.",
    }


@app.get("/health", tags=["Info"])
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# ─── Audio Cleanup ───────────────────────────────────────────────────────────

@app.post("/cleanup", response_model=ProcessingResponse, tags=["Audio Processing"])
async def cleanup_audio(
    audio: UploadFile = File(..., description="Audio file to clean up"),
    config: str = Form("{}"),
    user: UserInfo = Depends(verify_token),
):
    """
    Clean up an audio file: noise reduction, pop/click removal,
    de-essing, hum removal, and optional pitch correction.

    Upload an audio file (WAV, FLAC, MP3) and receive a cleaned version
    at 96kHz lossless stereo.
    """
    import json
    from engine.cleanup import run_cleanup_pipeline, CleanupConfig

    filepath = save_upload(audio)

    try:
        cfg_dict = json.loads(config)
        cfg = CleanupConfig(**{k: v for k, v in cfg_dict.items() if hasattr(CleanupConfig, k)})
    except Exception:
        cfg = CleanupConfig()

    output_path = os.path.join(OUTPUT_DIR, f"cleaned_{os.path.basename(filepath)}")
    report = run_cleanup_pipeline(filepath, output_path, cfg)

    if report.success:
        return ProcessingResponse(
            success=True,
            message="Audio cleaned successfully",
            output_file=report.output_file,
            download_url=f"/download/{os.path.basename(report.output_file)}",
            details={
                "operations": report.operations,
                "pops_detected": report.pops_detected,
                "duration_seconds": report.duration_seconds,
            },
        )
    else:
        raise HTTPException(status_code=500, detail=report.error)


# ─── Mastering ───────────────────────────────────────────────────────────────

@app.post("/master", response_model=ProcessingResponse, tags=["Audio Processing"])
async def master_audio(
    audio: UploadFile = File(..., description="Audio file to master"),
    preset: str = Form("default"),
    target_lufs: float = Form(-14.0),
    user: UserInfo = Depends(verify_token),
):
    """
    Master an audio file with professional-grade processing.

    Presets: default, warm, bright, punchy, gentle, kpop, cinematic, indie_folk
    """
    from engine.mastering import run_mastering_pipeline, MasteringConfig

    filepath = save_upload(audio)
    cfg = MasteringConfig(preset=preset, target_lufs=target_lufs)

    output_path = os.path.join(OUTPUT_DIR, f"mastered_{os.path.basename(filepath)}")
    report = run_mastering_pipeline(filepath, output_path, cfg)

    if report.success:
        return ProcessingResponse(
            success=True,
            message=f"Audio mastered with '{preset}' preset",
            output_file=report.output_file,
            download_url=f"/download/{os.path.basename(report.output_file)}",
            details={
                "operations": report.operations,
                "input_lufs": report.input_lufs,
                "output_lufs": report.output_lufs,
                "peak_db": report.peak_db,
            },
        )
    else:
        raise HTTPException(status_code=500, detail=report.error)


# ─── Stem Separation ────────────────────────────────────────────────────────

@app.post("/separate", response_model=ProcessingResponse, tags=["Audio Processing"])
async def separate_audio(
    audio: UploadFile = File(..., description="Audio file to separate into stems"),
    model: str = Form("htdemucs"),
    two_stems: Optional[str] = Form(None),
    user: UserInfo = Depends(verify_token),
):
    """
    Separate an audio file into stems (vocals, drums, bass, other).
    Uses Meta's Demucs model.
    """
    from engine.separation import separate_stems, SeparationConfig

    filepath = save_upload(audio)
    output_dir = os.path.join(OUTPUT_DIR, f"stems_{uuid.uuid4().hex[:8]}")

    cfg = SeparationConfig(model=model, two_stems=two_stems)
    report = separate_stems(filepath, output_dir, cfg)

    if report.success:
        return ProcessingResponse(
            success=True,
            message=f"Separated into {len(report.stems_created)} stems",
            output_file=report.output_dir,
            details={
                "stems": report.stems_created,
                "stem_files": report.stem_files,
            },
        )
    else:
        raise HTTPException(status_code=500, detail=report.error)


# ─── Voice ───────────────────────────────────────────────────────────────────

@app.post("/voice/tts", response_model=ProcessingResponse, tags=["Voice"])
async def text_to_speech(
    text: str = Form(..., description="Text to speak"),
    voice: str = Form("en-US-GuyNeural"),
    user: UserInfo = Depends(verify_token),
):
    """
    Convert text to speech using Edge TTS.

    Available voices: en-US-GuyNeural, en-US-JennyNeural,
    en-US-AriaNeural, en-GB-RyanNeural, ko-KR-InJoonNeural
    """
    from engine.voice import text_to_speech as tts

    output_path = os.path.join(OUTPUT_DIR, f"tts_{uuid.uuid4().hex[:8]}.wav")
    report = tts(text, output_path, voice=voice)

    if report.success:
        return ProcessingResponse(
            success=True,
            message="Text-to-speech generated",
            output_file=report.output_file,
            download_url=f"/download/{os.path.basename(report.output_file)}",
            details={"model_used": report.model_used},
        )
    else:
        raise HTTPException(status_code=500, detail=report.error)


@app.get("/voice/models", tags=["Voice"])
async def list_models(user: UserInfo = Depends(verify_token)):
    """List all available voice models."""
    from engine.voice import list_voice_models
    models = list_voice_models()
    return {
        "models": [
            {
                "name": m.name,
                "type": m.model_type,
                "description": m.description,
            }
            for m in models
        ]
    }


@app.post("/voice/train", response_model=ProcessingResponse, tags=["Voice"])
async def train_voice(
    audio_files: List[UploadFile] = File(..., description="Audio files for training"),
    model_name: str = Form(..., description="Name for the new voice model"),
    description: str = Form("", description="Model description"),
    user: UserInfo = Depends(verify_token),
):
    """
    Train a new voice model from audio files.
    Provide 10-30 minutes of clean vocal audio for best results.
    """
    from engine.voice import train_voice_model

    saved_files = [save_upload(f) for f in audio_files]
    report = train_voice_model(saved_files, model_name, description=description)

    if report.success:
        return ProcessingResponse(
            success=True,
            message=f"Voice model '{model_name}' prepared for training",
            output_file=report.output_file,
            details={"model_name": model_name},
        )
    else:
        raise HTTPException(status_code=500, detail=report.error)


# ─── Video Generation ────────────────────────────────────────────────────────

@app.post("/video", response_model=ProcessingResponse, tags=["Video"])
async def create_video(
    audio: UploadFile = File(..., description="Audio file"),
    title: str = Form(""),
    artist: str = Form("Revvel"),
    video_type: str = Form("visualizer"),
    user: UserInfo = Depends(verify_token),
):
    """
    Generate a video for a music track.

    Types: visualizer (waveform), spectrum (frequency bars), static (image + audio)
    """
    from engine.video import create_video as gen_video, VideoConfig

    filepath = save_upload(audio)
    output_path = os.path.join(OUTPUT_DIR, f"video_{uuid.uuid4().hex[:8]}.mp4")

    cfg = VideoConfig(video_type=video_type)
    report = gen_video(filepath, output_path, title=title, artist=artist, config=cfg)

    if report.success:
        return ProcessingResponse(
            success=True,
            message=f"Video created ({video_type})",
            output_file=report.output_video,
            download_url=f"/download/{os.path.basename(report.output_video)}",
            details={"video_type": video_type, "resolution": report.resolution},
        )
    else:
        raise HTTPException(status_code=500, detail=report.error)


# ─── Distribution ────────────────────────────────────────────────────────────

@app.get("/distribution/distributors", tags=["Distribution"])
async def get_distributors(user: UserInfo = Depends(verify_token)):
    """List all supported music distributors with details."""
    from engine.distribution import list_distributors
    return {"distributors": list_distributors()}


@app.post("/distribution/prepare", response_model=ProcessingResponse, tags=["Distribution"])
async def prepare_distribution(
    audio_files: List[UploadFile] = File(..., description="Audio files for the release"),
    title: str = Form(...),
    artist: str = Form("Revvel"),
    label: str = Form("HOTRS - House of the Rising Sun"),
    release_type: str = Form("single"),
    genre: str = Form("Alt Pop"),
    distributor: str = Form("landr"),
    track_titles: str = Form("", description="Comma-separated track titles"),
    description: str = Form(""),
    seo_words: str = Form(""),
    user: UserInfo = Depends(verify_token),
):
    """
    Prepare a release package for distribution.
    Creates validated metadata, ISRCs, and upload instructions.
    """
    from engine.distribution import (
        prepare_release_package, ReleaseMetadata, TrackMetadata
    )

    saved_files = [save_upload(f) for f in audio_files]
    titles = [t.strip() for t in track_titles.split(",") if t.strip()] if track_titles else []

    # Build track metadata
    tracks = []
    for i, f in enumerate(saved_files):
        t_title = titles[i] if i < len(titles) else f"Track {i + 1}"
        tracks.append(TrackMetadata(
            title=t_title,
            artist=artist,
            album=title,
            track_number=i + 1,
            genre=genre,
            description=description,
            seo_words=seo_words,
        ))

    release = ReleaseMetadata(
        title=title,
        artist=artist,
        label=label,
        release_type=release_type,
        genre=genre,
        tracks=tracks,
        description=description,
        seo_words=seo_words,
    )

    output_dir = os.path.join(OUTPUT_DIR, f"release_{uuid.uuid4().hex[:8]}")
    report = prepare_release_package(release, saved_files, output_dir, distributor)

    if report.success:
        return ProcessingResponse(
            success=True,
            message=f"Release package prepared for {distributor}",
            output_file=report.package_dir,
            details={
                "tracks_prepared": report.tracks_prepared,
                "files_created": report.files_created,
                "warnings": report.validation_warnings,
            },
        )
    else:
        raise HTTPException(
            status_code=400,
            detail={
                "message": report.error,
                "validation_errors": report.validation_errors,
            },
        )


# ─── File Download ───────────────────────────────────────────────────────────

@app.get("/download/{filename}", tags=["Files"])
async def download_file(filename: str, user: UserInfo = Depends(verify_token)):
    """Download a processed file."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, filename=filename)


# ─── Full Pipeline ───────────────────────────────────────────────────────────

@app.post("/pipeline/full", response_model=ProcessingResponse, tags=["Pipeline"])
async def full_pipeline(
    audio: UploadFile = File(..., description="Audio file"),
    title: str = Form(""),
    artist: str = Form("Revvel"),
    mastering_preset: str = Form("default"),
    create_video_flag: bool = Form(True),
    prepare_distribution_flag: bool = Form(False),
    distributor: str = Form("landr"),
    user: UserInfo = Depends(verify_token),
):
    """
    Run the full production pipeline:
    1. Audio cleanup (noise, pops, hum)
    2. Mastering (EQ, compression, limiting)
    3. Video generation (optional)
    4. Distribution preparation (optional)

    This is the one-stop endpoint for taking a raw track
    to distribution-ready quality.
    """
    from engine.cleanup import run_cleanup_pipeline, CleanupConfig
    from engine.mastering import run_mastering_pipeline, MasteringConfig
    from engine.video import create_video as gen_video, VideoConfig
    from engine.distribution import (
        prepare_release_package, ReleaseMetadata, TrackMetadata
    )

    filepath = save_upload(audio)
    results = {"steps": []}

    # Step 1: Cleanup
    cleanup_output = os.path.join(OUTPUT_DIR, f"cleaned_{os.path.basename(filepath)}")
    cleanup_report = run_cleanup_pipeline(filepath, cleanup_output, CleanupConfig())
    results["steps"].append({
        "step": "cleanup",
        "success": cleanup_report.success,
        "operations": cleanup_report.operations,
    })

    if not cleanup_report.success:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {cleanup_report.error}")

    # Step 2: Mastering
    master_output = os.path.join(OUTPUT_DIR, f"mastered_{os.path.basename(filepath)}")
    master_cfg = MasteringConfig(preset=mastering_preset)
    master_report = run_mastering_pipeline(cleanup_report.output_file, master_output, master_cfg)
    results["steps"].append({
        "step": "mastering",
        "success": master_report.success,
        "operations": master_report.operations,
        "output_lufs": master_report.output_lufs,
    })

    if not master_report.success:
        raise HTTPException(status_code=500, detail=f"Mastering failed: {master_report.error}")

    final_audio = master_report.output_file

    # Step 3: Video (optional)
    if create_video_flag:
        video_output = os.path.join(OUTPUT_DIR, f"video_{uuid.uuid4().hex[:8]}.mp4")
        video_report = gen_video(
            final_audio, video_output,
            title=title, artist=artist,
            config=VideoConfig(video_type="visualizer"),
        )
        results["steps"].append({
            "step": "video",
            "success": video_report.success,
            "output": video_report.output_video,
        })

    # Step 4: Distribution prep (optional)
    if prepare_distribution_flag:
        track = TrackMetadata(title=title or "Untitled", artist=artist, genre="Alt Pop")
        release = ReleaseMetadata(
            title=title or "Untitled",
            artist=artist,
            tracks=[track],
        )
        dist_dir = os.path.join(OUTPUT_DIR, f"release_{uuid.uuid4().hex[:8]}")
        dist_report = prepare_release_package(release, [final_audio], dist_dir, distributor)
        results["steps"].append({
            "step": "distribution",
            "success": dist_report.success,
            "package_dir": dist_report.package_dir,
        })

    return ProcessingResponse(
        success=True,
        message="Full pipeline completed",
        output_file=final_audio,
        download_url=f"/download/{os.path.basename(final_audio)}",
        details=results,
    )


# ─── Run Server ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
