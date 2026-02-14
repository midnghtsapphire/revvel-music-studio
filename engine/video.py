"""
Video Generation Module
========================

Automatically creates videos for music tracks:
- Static image + audio (album art video)
- Audio waveform visualizer
- Lyric videos (with subtitle overlay)
- Spectrum analyzer videos

Audio processing provided by free and open-source libraries.
"""

import os
import subprocess
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass
class VideoConfig:
    """Configuration for video generation."""
    video_type: str = "visualizer"  # visualizer, static, lyrics, spectrum
    width: int = 1920
    height: int = 1080
    fps: int = 30
    background_color: str = "#0a0a0a"
    accent_color: str = "#ff4444"
    secondary_color: str = "#4444ff"
    font_size: int = 48
    font_color: str = "#ffffff"
    title_font_size: int = 72
    show_title: bool = True
    show_artist: bool = True
    output_format: str = "mp4"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "320k"
    crf: int = 18  # Quality (lower = better, 18 is visually lossless)


@dataclass
class VideoReport:
    """Report of video generation."""
    input_audio: str = ""
    output_video: str = ""
    video_type: str = ""
    duration_seconds: float = 0.0
    resolution: str = ""
    success: bool = False
    error: Optional[str] = None


def create_static_video(
    audio_path: str,
    image_path: str,
    output_path: str,
    title: str = "",
    artist: str = "Revvel",
    config: Optional[VideoConfig] = None,
) -> VideoReport:
    """
    Create a video with a static image and audio track.
    Optionally overlays title and artist name.
    """
    if config is None:
        config = VideoConfig(video_type="static")

    report = VideoReport(
        input_audio=audio_path,
        video_type="static",
        resolution=f"{config.width}x{config.height}",
    )

    if not os.path.exists(audio_path):
        report.error = f"Audio file not found: {audio_path}"
        return report

    try:
        # Build ffmpeg command
        cmd = ["ffmpeg", "-y"]

        if os.path.exists(image_path):
            # Use provided image
            cmd.extend([
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-vf", f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease,"
                       f"pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2:color={config.background_color}",
            ])
        else:
            # Generate solid color background
            cmd.extend([
                "-f", "lavfi",
                "-i", f"color=c={config.background_color}:s={config.width}x{config.height}:d=1",
                "-i", audio_path,
            ])

        # Add text overlays
        filter_complex = []
        if config.show_title and title:
            filter_complex.append(
                f"drawtext=text='{title}':fontsize={config.title_font_size}:"
                f"fontcolor={config.font_color}:x=(w-text_w)/2:y=h/2-{config.title_font_size}"
            )
        if config.show_artist and artist:
            filter_complex.append(
                f"drawtext=text='{artist}':fontsize={config.font_size}:"
                f"fontcolor={config.accent_color}:x=(w-text_w)/2:y=h/2+20"
            )

        if filter_complex:
            cmd.extend(["-vf", ",".join(filter_complex)])

        cmd.extend([
            "-c:v", config.video_codec,
            "-c:a", config.audio_codec,
            "-b:a", config.audio_bitrate,
            "-crf", str(config.crf),
            "-shortest",
            "-pix_fmt", "yuv420p",
            output_path,
        ])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            report.success = True
            report.output_video = output_path
        else:
            report.error = f"FFmpeg failed: {result.stderr[:500]}"

    except Exception as e:
        report.error = str(e)

    return report


def create_waveform_video(
    audio_path: str,
    output_path: str,
    title: str = "",
    artist: str = "Revvel",
    config: Optional[VideoConfig] = None,
) -> VideoReport:
    """
    Create a video with an animated audio waveform visualizer.
    Uses ffmpeg's showwaves filter.
    """
    if config is None:
        config = VideoConfig(video_type="visualizer")

    report = VideoReport(
        input_audio=audio_path,
        video_type="visualizer",
        resolution=f"{config.width}x{config.height}",
    )

    if not os.path.exists(audio_path):
        report.error = f"Audio file not found: {audio_path}"
        return report

    try:
        # Create waveform video with ffmpeg
        filter_complex = (
            f"[0:a]showwaves=s={config.width}x{config.height // 2}:"
            f"mode=cline:rate={config.fps}:"
            f"colors={config.accent_color}|{config.secondary_color}[waves];"
            f"color=c={config.background_color}:s={config.width}x{config.height}[bg];"
            f"[bg][waves]overlay=0:{config.height // 4}[v]"
        )

        # Add title overlay
        if title:
            filter_complex += (
                f";[v]drawtext=text='{title}':"
                f"fontsize={config.title_font_size}:"
                f"fontcolor={config.font_color}:"
                f"x=(w-text_w)/2:y=40[v2]"
            )
            if artist:
                filter_complex += (
                    f";[v2]drawtext=text='{artist}':"
                    f"fontsize={config.font_size}:"
                    f"fontcolor={config.accent_color}:"
                    f"x=(w-text_w)/2:y={40 + config.title_font_size + 10}[vout]"
                )
                output_label = "vout"
            else:
                output_label = "v2"
        else:
            output_label = "v"

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", f"[{output_label}]",
            "-map", "0:a",
            "-c:v", config.video_codec,
            "-c:a", config.audio_codec,
            "-b:a", config.audio_bitrate,
            "-crf", str(config.crf),
            "-pix_fmt", "yuv420p",
            "-r", str(config.fps),
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            report.success = True
            report.output_video = output_path
        else:
            report.error = f"FFmpeg failed: {result.stderr[:500]}"

    except Exception as e:
        report.error = str(e)

    return report


def create_spectrum_video(
    audio_path: str,
    output_path: str,
    title: str = "",
    artist: str = "Revvel",
    config: Optional[VideoConfig] = None,
) -> VideoReport:
    """
    Create a video with an animated spectrum analyzer.
    Uses ffmpeg's showfreqs filter.
    """
    if config is None:
        config = VideoConfig(video_type="spectrum")

    report = VideoReport(
        input_audio=audio_path,
        video_type="spectrum",
        resolution=f"{config.width}x{config.height}",
    )

    if not os.path.exists(audio_path):
        report.error = f"Audio file not found: {audio_path}"
        return report

    try:
        filter_complex = (
            f"[0:a]showfreqs=s={config.width}x{config.height // 2}:"
            f"mode=bar:fscale=log:colors={config.accent_color}|{config.secondary_color}[freq];"
            f"color=c={config.background_color}:s={config.width}x{config.height}[bg];"
            f"[bg][freq]overlay=0:{config.height // 4}[v]"
        )

        if title:
            filter_complex += (
                f";[v]drawtext=text='{title}':"
                f"fontsize={config.title_font_size}:"
                f"fontcolor={config.font_color}:"
                f"x=(w-text_w)/2:y=30[vout]"
            )
            output_label = "vout"
        else:
            output_label = "v"

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", f"[{output_label}]",
            "-map", "0:a",
            "-c:v", config.video_codec,
            "-c:a", config.audio_codec,
            "-b:a", config.audio_bitrate,
            "-crf", str(config.crf),
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            report.success = True
            report.output_video = output_path
        else:
            report.error = f"FFmpeg failed: {result.stderr[:500]}"

    except Exception as e:
        report.error = str(e)

    return report


def create_video(
    audio_path: str,
    output_path: Optional[str] = None,
    title: str = "",
    artist: str = "Revvel",
    image_path: str = "",
    lyrics: str = "",
    config: Optional[VideoConfig] = None,
) -> VideoReport:
    """
    High-level function to create a video for a track.
    Automatically selects the best video type based on available inputs.
    """
    if config is None:
        config = VideoConfig()

    if output_path is None:
        base = os.path.splitext(audio_path)[0]
        output_path = f"{base}_video.{config.output_format}"

    if config.video_type == "static" or (image_path and os.path.exists(image_path)):
        return create_static_video(audio_path, image_path, output_path, title, artist, config)
    elif config.video_type == "spectrum":
        return create_spectrum_video(audio_path, output_path, title, artist, config)
    else:
        return create_waveform_video(audio_path, output_path, title, artist, config)
