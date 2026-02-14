"""
Stem Separation Module
=======================

Separates audio tracks into individual stems using
Meta's Demucs model (state-of-the-art source separation).

Stems: vocals, drums, bass, other (instruments)

Audio processing provided by free and open-source libraries.
"""

import os
import subprocess
import shutil
from typing import Optional, List, Dict
from dataclasses import dataclass, field


@dataclass
class SeparationConfig:
    """Configuration for stem separation."""
    model: str = "htdemucs"  # htdemucs, htdemucs_ft, mdx_extra
    stems: List[str] = field(default_factory=lambda: ["vocals", "drums", "bass", "other"])
    output_format: str = "wav"
    sample_rate: int = 44100
    two_stems: Optional[str] = None  # e.g., "vocals" to split into vocals + no_vocals
    mp3_bitrate: int = 320
    float32: bool = True
    shifts: int = 1  # Number of random shifts for better quality (higher = slower)
    overlap: float = 0.25


@dataclass
class SeparationReport:
    """Report of stem separation."""
    input_file: str = ""
    output_dir: str = ""
    model: str = ""
    stems_created: List[str] = field(default_factory=list)
    stem_files: Dict[str, str] = field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None


def check_demucs_installed() -> bool:
    """Check if demucs is available."""
    try:
        result = subprocess.run(
            ["python3", "-c", "import demucs"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def install_demucs() -> bool:
    """Attempt to install demucs."""
    try:
        result = subprocess.run(
            ["pip3", "install", "demucs"],
            capture_output=True, text=True, timeout=300
        )
        return result.returncode == 0
    except Exception:
        return False


def separate_stems(
    input_path: str,
    output_dir: Optional[str] = None,
    config: Optional[SeparationConfig] = None,
) -> SeparationReport:
    """
    Separate an audio file into stems using Demucs.

    Args:
        input_path: Path to the input audio file
        output_dir: Directory for output stems (default: same dir as input)
        config: Separation configuration

    Returns:
        SeparationReport with paths to all created stems
    """
    if config is None:
        config = SeparationConfig()

    report = SeparationReport(input_file=input_path, model=config.model)

    if not os.path.exists(input_path):
        report.error = f"Input file not found: {input_path}"
        return report

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(input_path), "stems")

    os.makedirs(output_dir, exist_ok=True)
    report.output_dir = output_dir

    try:
        # Build demucs command
        cmd = [
            "python3", "-m", "demucs",
            "--out", output_dir,
            "--name", config.model,
            "--shifts", str(config.shifts),
            "--overlap", str(config.overlap),
        ]

        if config.two_stems:
            cmd.extend(["--two-stems", config.two_stems])

        if config.float32:
            cmd.append("--float32")

        if config.output_format == "mp3":
            cmd.extend(["--mp3", "--mp3-bitrate", str(config.mp3_bitrate)])
        elif config.output_format == "flac":
            cmd.append("--flac")

        cmd.append(input_path)

        # Run demucs
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            report.error = f"Demucs failed: {result.stderr}"
            return report

        # Find output files
        track_name = os.path.splitext(os.path.basename(input_path))[0]
        stems_dir = os.path.join(output_dir, config.model, track_name)

        if os.path.exists(stems_dir):
            for stem_file in os.listdir(stems_dir):
                stem_name = os.path.splitext(stem_file)[0]
                stem_path = os.path.join(stems_dir, stem_file)
                report.stems_created.append(stem_name)
                report.stem_files[stem_name] = stem_path

        report.success = len(report.stems_created) > 0
        if not report.success:
            report.error = "No stems were created"

    except subprocess.TimeoutExpired:
        report.error = "Stem separation timed out (10 minutes)"
    except FileNotFoundError:
        report.error = "Demucs not installed. Install with: pip install demucs"
    except Exception as e:
        report.error = str(e)

    return report


def separate_vocals(
    input_path: str,
    output_dir: Optional[str] = None,
) -> SeparationReport:
    """
    Quick helper to separate just vocals from a track.
    Returns vocals and instrumental (no_vocals) stems.
    """
    config = SeparationConfig(two_stems="vocals")
    return separate_stems(input_path, output_dir, config)


def recombine_stems(
    stem_files: Dict[str, str],
    output_path: str,
    exclude_stems: Optional[List[str]] = None,
    sample_rate: int = 44100,
) -> str:
    """
    Recombine selected stems back into a single audio file.
    Useful for creating versions without certain elements
    (e.g., karaoke version without vocals).
    """
    import numpy as np
    import soundfile as sf

    if exclude_stems is None:
        exclude_stems = []

    combined = None

    for stem_name, stem_path in stem_files.items():
        if stem_name in exclude_stems:
            continue

        if not os.path.exists(stem_path):
            continue

        audio, sr = sf.read(stem_path, dtype='float64')

        if combined is None:
            combined = audio
        else:
            # Ensure same length
            min_len = min(len(combined), len(audio))
            combined = combined[:min_len] + audio[:min_len]

    if combined is not None:
        sf.write(output_path, combined, sample_rate, subtype='PCM_24')
        return output_path
    else:
        raise ValueError("No stems to combine")
