"""
Voice Synthesis & Cloning Module
==================================

Provides voice model management, text-to-speech,
and voice-to-voice conversion capabilities.

Supports:
- Voice model training from audio samples
- Text-to-speech with custom voice models
- Voice conversion (change voice in existing audio)
- Voice model management (save, load, list)

Audio processing provided by free and open-source libraries.
"""

import os
import json
import subprocess
import shutil
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VoiceModel:
    """Represents a trained voice model."""
    name: str
    model_type: str = "rvc"  # rvc, gpt-sovits, coqui
    model_path: str = ""
    index_path: str = ""
    config_path: str = ""
    sample_rate: int = 40000
    created_at: str = ""
    description: str = ""
    training_audio_hours: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceConfig:
    """Configuration for voice operations."""
    # TTS settings
    tts_engine: str = "edge"  # edge, coqui, bark
    tts_language: str = "en"
    tts_speed: float = 1.0
    tts_pitch: float = 1.0

    # Voice conversion
    rvc_pitch_shift: int = 0  # Semitones
    rvc_filter_radius: int = 3
    rvc_index_rate: float = 0.75
    rvc_protect: float = 0.33

    # Output
    output_format: str = "wav"
    output_sample_rate: int = 96000


@dataclass
class VoiceReport:
    """Report of voice operations."""
    operation: str = ""
    input_file: str = ""
    output_file: str = ""
    model_used: str = ""
    duration_seconds: float = 0.0
    success: bool = False
    error: Optional[str] = None


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


def get_models_dir() -> str:
    """Get the models directory, creating it if needed."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    return MODELS_DIR


def list_voice_models() -> List[VoiceModel]:
    """List all available voice models."""
    models = []
    models_dir = get_models_dir()

    # Check for model metadata files
    for item in os.listdir(models_dir):
        meta_path = os.path.join(models_dir, item, "model_meta.json")
        if os.path.isdir(os.path.join(models_dir, item)) and os.path.exists(meta_path):
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                model = VoiceModel(
                    name=meta.get("name", item),
                    model_type=meta.get("model_type", "rvc"),
                    model_path=meta.get("model_path", ""),
                    index_path=meta.get("index_path", ""),
                    config_path=meta.get("config_path", ""),
                    sample_rate=meta.get("sample_rate", 40000),
                    created_at=meta.get("created_at", ""),
                    description=meta.get("description", ""),
                    training_audio_hours=meta.get("training_audio_hours", 0.0),
                    metadata=meta.get("metadata", {}),
                )
                models.append(model)
            except Exception:
                continue

    # Add built-in placeholder models
    builtins = [
        VoiceModel(
            name="revvel-default",
            model_type="builtin",
            description="Default Revvel voice model (train with your audio to activate)",
        ),
        VoiceModel(
            name="edge-tts-male",
            model_type="edge",
            description="Microsoft Edge TTS - Male voice (en-US-GuyNeural)",
        ),
        VoiceModel(
            name="edge-tts-female",
            model_type="edge",
            description="Microsoft Edge TTS - Female voice (en-US-JennyNeural)",
        ),
    ]

    return builtins + models


def save_voice_model(model: VoiceModel) -> str:
    """Save voice model metadata."""
    models_dir = get_models_dir()
    model_dir = os.path.join(models_dir, model.name)
    os.makedirs(model_dir, exist_ok=True)

    meta = {
        "name": model.name,
        "model_type": model.model_type,
        "model_path": model.model_path,
        "index_path": model.index_path,
        "config_path": model.config_path,
        "sample_rate": model.sample_rate,
        "created_at": model.created_at or datetime.now().isoformat(),
        "description": model.description,
        "training_audio_hours": model.training_audio_hours,
        "metadata": model.metadata,
    }

    meta_path = os.path.join(model_dir, "model_meta.json")
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    return meta_path


def text_to_speech(
    text: str,
    output_path: str,
    voice: str = "en-US-GuyNeural",
    config: Optional[VoiceConfig] = None,
) -> VoiceReport:
    """
    Convert text to speech using Edge TTS (free, no API key needed).

    Available voices include:
    - en-US-GuyNeural (male)
    - en-US-JennyNeural (female)
    - en-US-AriaNeural (female)
    - en-GB-RyanNeural (male, British)
    - ko-KR-InJoonNeural (male, Korean)
    - ko-KR-SunHiNeural (female, Korean)
    """
    if config is None:
        config = VoiceConfig()

    report = VoiceReport(operation="text_to_speech", output_file=output_path)

    try:
        # Try edge-tts first (free, high quality)
        try:
            import edge_tts
            import asyncio

            async def _generate():
                communicate = edge_tts.Communicate(
                    text,
                    voice=voice,
                    rate=f"{int((config.tts_speed - 1) * 100):+d}%",
                    pitch=f"{int((config.tts_pitch - 1) * 50):+d}Hz",
                )
                await communicate.save(output_path)

            asyncio.run(_generate())
            report.success = True
            report.model_used = f"edge-tts:{voice}"

        except ImportError:
            # Fallback: use subprocess with edge-tts CLI
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                report.success = True
                report.model_used = f"edge-tts-cli:{voice}"
            else:
                # Final fallback: use pyttsx3 or espeak
                try:
                    subprocess.run(
                        ["espeak", "-w", output_path, text],
                        capture_output=True, text=True, timeout=30
                    )
                    report.success = True
                    report.model_used = "espeak"
                except Exception:
                    report.error = "No TTS engine available. Install edge-tts: pip install edge-tts"

    except Exception as e:
        report.error = str(e)

    return report


def voice_convert(
    input_path: str,
    output_path: str,
    model_name: str,
    config: Optional[VoiceConfig] = None,
) -> VoiceReport:
    """
    Convert voice in an audio file using a trained RVC model.

    This requires an RVC model to be trained and saved in the models directory.
    """
    if config is None:
        config = VoiceConfig()

    report = VoiceReport(
        operation="voice_conversion",
        input_file=input_path,
        output_file=output_path,
        model_used=model_name,
    )

    if not os.path.exists(input_path):
        report.error = f"Input file not found: {input_path}"
        return report

    # Find the model
    models_dir = get_models_dir()
    model_dir = os.path.join(models_dir, model_name)
    meta_path = os.path.join(model_dir, "model_meta.json")

    if not os.path.exists(meta_path):
        report.error = (
            f"Voice model '{model_name}' not found. "
            f"Train a model first with: revvel voice train --name {model_name} --audio <audio_files>"
        )
        return report

    try:
        with open(meta_path, 'r') as f:
            meta = json.load(f)

        model_path = meta.get("model_path", "")
        if not model_path or not os.path.exists(model_path):
            report.error = f"Model file not found at: {model_path}"
            return report

        # RVC inference command
        cmd = [
            "python3", "-m", "rvc_infer",
            "--model", model_path,
            "--input", input_path,
            "--output", output_path,
            "--pitch", str(config.rvc_pitch_shift),
            "--filter-radius", str(config.rvc_filter_radius),
            "--index-rate", str(config.rvc_index_rate),
            "--protect", str(config.rvc_protect),
        ]

        index_path = meta.get("index_path", "")
        if index_path and os.path.exists(index_path):
            cmd.extend(["--index", index_path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            report.success = True
        else:
            report.error = f"RVC inference failed: {result.stderr}"

    except Exception as e:
        report.error = str(e)

    return report


def train_voice_model(
    audio_files: List[str],
    model_name: str,
    model_type: str = "rvc",
    description: str = "",
    epochs: int = 100,
) -> VoiceReport:
    """
    Train a new voice model from audio files.

    For best results, provide 10-30 minutes of clean vocal audio.
    """
    report = VoiceReport(operation="train_voice_model", model_used=model_name)

    models_dir = get_models_dir()
    model_dir = os.path.join(models_dir, model_name)
    os.makedirs(model_dir, exist_ok=True)

    # Validate audio files
    valid_files = [f for f in audio_files if os.path.exists(f)]
    if not valid_files:
        report.error = "No valid audio files provided"
        return report

    try:
        # Calculate total audio duration
        import soundfile as sf
        total_duration = 0.0
        for f in valid_files:
            info = sf.info(f)
            total_duration += info.duration

        # Copy training audio to model directory
        training_dir = os.path.join(model_dir, "training_audio")
        os.makedirs(training_dir, exist_ok=True)
        for f in valid_files:
            shutil.copy2(f, training_dir)

        # Save model metadata
        model = VoiceModel(
            name=model_name,
            model_type=model_type,
            model_path=os.path.join(model_dir, f"{model_name}.pth"),
            index_path=os.path.join(model_dir, f"{model_name}.index"),
            config_path=os.path.join(model_dir, "config.json"),
            created_at=datetime.now().isoformat(),
            description=description or f"Voice model for {model_name}",
            training_audio_hours=total_duration / 3600.0,
            metadata={
                "training_files": [os.path.basename(f) for f in valid_files],
                "epochs": epochs,
                "status": "ready_to_train",
            },
        )
        save_voice_model(model)

        # Save training config
        train_config = {
            "model_name": model_name,
            "model_type": model_type,
            "training_files": valid_files,
            "epochs": epochs,
            "sample_rate": 40000,
            "batch_size": 8,
            "status": "ready_to_train",
            "instructions": (
                "To complete training, install RVC and run:\n"
                f"  python3 -m rvc_train --config {os.path.join(model_dir, 'config.json')}\n\n"
                "Or use the Revvel CLI:\n"
                f"  revvel voice train-execute --name {model_name}\n\n"
                "Training requires a GPU for best results."
            ),
        }

        config_path = os.path.join(model_dir, "config.json")
        with open(config_path, 'w') as f:
            json.dump(train_config, f, indent=2)

        report.success = True
        report.output_file = config_path

    except Exception as e:
        report.error = str(e)

    return report


def create_voice_from_song(
    song_path: str,
    model_name: str,
    description: str = "",
) -> VoiceReport:
    """
    Create a voice model from a song by first separating vocals,
    then using the isolated vocals for training.

    This is a convenience function that combines stem separation
    with voice model training.
    """
    report = VoiceReport(operation="create_voice_from_song", input_file=song_path)

    try:
        # First, separate vocals
        from engine.separation import separate_vocals
        sep_report = separate_vocals(song_path)

        if not sep_report.success:
            report.error = f"Vocal separation failed: {sep_report.error}"
            return report

        vocals_path = sep_report.stem_files.get("vocals", "")
        if not vocals_path or not os.path.exists(vocals_path):
            report.error = "Vocals stem not found after separation"
            return report

        # Train voice model from isolated vocals
        train_report = train_voice_model(
            audio_files=[vocals_path],
            model_name=model_name,
            description=description or f"Voice extracted from {os.path.basename(song_path)}",
        )

        report.success = train_report.success
        report.output_file = train_report.output_file
        report.error = train_report.error
        report.model_used = model_name

    except Exception as e:
        report.error = str(e)

    return report
