#!/usr/bin/env python3
"""
Revvel Music Studio - MCP Server
===================================

Model Context Protocol server for AI-assisted music production.
Exposes all Revvel Music Studio tools to MCP-compatible clients
(Claude, Manus, etc.).

Artist: Revvel
Label: HOTRS (House of the Rising Sun)
Audio processing provided by free and open-source libraries.
"""

import os
import sys
import json
import asyncio
from typing import Any, Dict, List, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource
    HAS_MCP_SDK = True
except ImportError:
    HAS_MCP_SDK = False


# ─── Tool Definitions ───────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "revvel_cleanup",
        "description": (
            "Clean up an audio file: noise reduction, pop/click removal, "
            "de-essing, hum removal, and optional pitch correction. "
            "Outputs 96kHz lossless stereo WAV. "
            "Audio processing provided by free and open-source libraries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to input audio file"},
                "output_path": {"type": "string", "description": "Path for output file (optional)"},
                "noise_reduce": {"type": "boolean", "default": True},
                "noise_strength": {"type": "number", "default": 0.75, "minimum": 0, "maximum": 1},
                "remove_pops": {"type": "boolean", "default": True},
                "pop_threshold": {"type": "number", "default": 3.5},
                "deess": {"type": "boolean", "default": True},
                "remove_hum": {"type": "boolean", "default": True},
                "hum_frequency": {"type": "number", "default": 60.0},
                "pitch_correct": {"type": "boolean", "default": False},
                "pitch_strength": {"type": "number", "default": 0.8},
                "pitch_key": {"type": "string", "default": "C"},
                "sample_rate": {"type": "integer", "default": 96000},
                "output_format": {"type": "string", "default": "wav", "enum": ["wav", "flac"]},
            },
            "required": ["input_path"],
        },
    },
    {
        "name": "revvel_master",
        "description": (
            "Master an audio file with professional-grade processing: "
            "EQ, compression, stereo enhancement, limiting, loudness normalization. "
            "Presets: default, warm, bright, punchy, gentle, kpop, cinematic, indie_folk. "
            "Audio processing provided by free and open-source libraries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to input audio file"},
                "output_path": {"type": "string", "description": "Path for output file (optional)"},
                "preset": {
                    "type": "string", "default": "default",
                    "enum": ["default", "warm", "bright", "punchy", "gentle", "kpop", "cinematic", "indie_folk"],
                },
                "target_lufs": {"type": "number", "default": -14.0},
                "sample_rate": {"type": "integer", "default": 96000},
                "output_format": {"type": "string", "default": "wav"},
                "stereo_width": {"type": "number", "default": 1.2},
            },
            "required": ["input_path"],
        },
    },
    {
        "name": "revvel_separate",
        "description": (
            "Separate an audio file into stems (vocals, drums, bass, other) "
            "using Meta's Demucs model. "
            "Audio processing provided by free and open-source libraries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to input audio file"},
                "output_dir": {"type": "string", "description": "Output directory for stems"},
                "model": {"type": "string", "default": "htdemucs"},
                "two_stems": {"type": "string", "description": "Split into two stems only (e.g., 'vocals')"},
            },
            "required": ["input_path"],
        },
    },
    {
        "name": "revvel_tts",
        "description": (
            "Convert text to speech using Edge TTS (free, no API key needed). "
            "Voices: en-US-GuyNeural, en-US-JennyNeural, en-US-AriaNeural, "
            "en-GB-RyanNeural, ko-KR-InJoonNeural, ko-KR-SunHiNeural. "
            "Audio processing provided by free and open-source libraries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert to speech"},
                "output_path": {"type": "string", "description": "Output file path"},
                "voice": {"type": "string", "default": "en-US-GuyNeural"},
            },
            "required": ["text", "output_path"],
        },
    },
    {
        "name": "revvel_voice_models",
        "description": "List all available voice models for Revvel Music Studio.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "revvel_voice_train",
        "description": (
            "Train a new voice model from audio files. "
            "Provide 10-30 minutes of clean vocal audio for best results."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "audio_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of audio file paths for training",
                },
                "model_name": {"type": "string", "description": "Name for the new model"},
                "description": {"type": "string", "default": ""},
            },
            "required": ["audio_files", "model_name"],
        },
    },
    {
        "name": "revvel_video",
        "description": (
            "Generate a music video from an audio file. "
            "Types: visualizer (waveform), spectrum (frequency bars), static (image + audio). "
            "Audio processing provided by free and open-source libraries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to input audio file"},
                "output_path": {"type": "string", "description": "Output video file path"},
                "title": {"type": "string", "default": ""},
                "artist": {"type": "string", "default": "Revvel"},
                "video_type": {
                    "type": "string", "default": "visualizer",
                    "enum": ["visualizer", "spectrum", "static"],
                },
            },
            "required": ["input_path"],
        },
    },
    {
        "name": "revvel_distribute",
        "description": (
            "Prepare a release package for music distribution. "
            "Creates validated metadata, ISRCs, and upload instructions "
            "for distributors: LANDR, Ditto, DistroKid, CD Baby, Amuse."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "audio_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of audio file paths",
                },
                "title": {"type": "string", "description": "Release title"},
                "artist": {"type": "string", "default": "Revvel"},
                "label": {"type": "string", "default": "HOTRS - House of the Rising Sun"},
                "release_type": {
                    "type": "string", "default": "single",
                    "enum": ["single", "ep", "album"],
                },
                "genre": {"type": "string", "default": "Alt Pop"},
                "distributor": {
                    "type": "string", "default": "landr",
                    "enum": ["landr", "ditto", "distrokid", "cdbaby", "amuse"],
                },
                "track_titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Track titles",
                },
                "output_dir": {"type": "string", "description": "Output directory"},
                "description": {"type": "string", "default": ""},
                "seo_words": {"type": "string", "default": ""},
            },
            "required": ["audio_files", "title"],
        },
    },
    {
        "name": "revvel_distributors",
        "description": "List all supported music distributors with pricing and features.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "revvel_pipeline",
        "description": (
            "Run the full production pipeline: cleanup → mastering → video. "
            "Takes a raw audio file and produces distribution-ready output. "
            "Audio processing provided by free and open-source libraries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to input audio file"},
                "output_path": {"type": "string", "description": "Output file path (optional)"},
                "title": {"type": "string", "default": ""},
                "artist": {"type": "string", "default": "Revvel"},
                "preset": {
                    "type": "string", "default": "default",
                    "enum": ["default", "warm", "bright", "punchy", "gentle", "kpop", "cinematic", "indie_folk"],
                },
                "target_lufs": {"type": "number", "default": -14.0},
                "create_video": {"type": "boolean", "default": True},
                "video_type": {
                    "type": "string", "default": "visualizer",
                    "enum": ["visualizer", "spectrum", "static"],
                },
            },
            "required": ["input_path"],
        },
    },
    {
        "name": "revvel_info",
        "description": "Get Revvel Music Studio system information and dependency status.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ─── Tool Handlers ───────────────────────────────────────────────────────────

def handle_cleanup(args: Dict[str, Any]) -> str:
    from engine.cleanup import run_cleanup_pipeline, CleanupConfig

    config = CleanupConfig(
        noise_reduce=args.get("noise_reduce", True),
        noise_reduce_strength=args.get("noise_strength", 0.75),
        remove_pops=args.get("remove_pops", True),
        pop_threshold=args.get("pop_threshold", 3.5),
        deess=args.get("deess", True),
        remove_hum=args.get("remove_hum", True),
        hum_frequency=args.get("hum_frequency", 60.0),
        pitch_correct=args.get("pitch_correct", False),
        pitch_correction_strength=args.get("pitch_strength", 0.8),
        pitch_key=args.get("pitch_key", "C"),
        target_sample_rate=args.get("sample_rate", 96000),
        output_format=args.get("output_format", "wav"),
    )

    report = run_cleanup_pipeline(
        args["input_path"],
        args.get("output_path"),
        config,
    )

    return json.dumps({
        "success": report.success,
        "output_file": report.output_file,
        "operations": report.operations,
        "pops_detected": report.pops_detected,
        "error": report.error,
    }, indent=2)


def handle_master(args: Dict[str, Any]) -> str:
    from engine.mastering import run_mastering_pipeline, MasteringConfig

    config = MasteringConfig(
        preset=args.get("preset", "default"),
        target_lufs=args.get("target_lufs", -14.0),
        target_sample_rate=args.get("sample_rate", 96000),
        output_format=args.get("output_format", "wav"),
        stereo_width=args.get("stereo_width", 1.2),
    )

    report = run_mastering_pipeline(
        args["input_path"],
        args.get("output_path"),
        config,
    )

    return json.dumps({
        "success": report.success,
        "output_file": report.output_file,
        "operations": report.operations,
        "input_lufs": report.input_lufs,
        "output_lufs": report.output_lufs,
        "peak_db": report.peak_db,
        "error": report.error,
    }, indent=2)


def handle_separate(args: Dict[str, Any]) -> str:
    from engine.separation import separate_stems, SeparationConfig

    config = SeparationConfig(
        model=args.get("model", "htdemucs"),
        two_stems=args.get("two_stems"),
    )

    report = separate_stems(
        args["input_path"],
        args.get("output_dir"),
        config,
    )

    return json.dumps({
        "success": report.success,
        "output_dir": report.output_dir,
        "stems_created": report.stems_created,
        "stem_files": report.stem_files,
        "error": report.error,
    }, indent=2)


def handle_tts(args: Dict[str, Any]) -> str:
    from engine.voice import text_to_speech

    report = text_to_speech(
        args["text"],
        args["output_path"],
        voice=args.get("voice", "en-US-GuyNeural"),
    )

    return json.dumps({
        "success": report.success,
        "output_file": report.output_file,
        "model_used": report.model_used,
        "error": report.error,
    }, indent=2)


def handle_voice_models(args: Dict[str, Any]) -> str:
    from engine.voice import list_voice_models

    models = list_voice_models()
    return json.dumps({
        "models": [
            {"name": m.name, "type": m.model_type, "description": m.description}
            for m in models
        ]
    }, indent=2)


def handle_voice_train(args: Dict[str, Any]) -> str:
    from engine.voice import train_voice_model

    report = train_voice_model(
        args["audio_files"],
        args["model_name"],
        description=args.get("description", ""),
    )

    return json.dumps({
        "success": report.success,
        "output_file": report.output_file,
        "error": report.error,
    }, indent=2)


def handle_video(args: Dict[str, Any]) -> str:
    from engine.video import create_video, VideoConfig

    config = VideoConfig(
        video_type=args.get("video_type", "visualizer"),
    )

    report = create_video(
        args["input_path"],
        args.get("output_path"),
        title=args.get("title", ""),
        artist=args.get("artist", "Revvel"),
        config=config,
    )

    return json.dumps({
        "success": report.success,
        "output_video": report.output_video,
        "video_type": report.video_type,
        "resolution": report.resolution,
        "error": report.error,
    }, indent=2)


def handle_distribute(args: Dict[str, Any]) -> str:
    from engine.distribution import (
        prepare_release_package, ReleaseMetadata, TrackMetadata
    )

    audio_files = args["audio_files"]
    track_titles = args.get("track_titles", [])

    tracks = []
    for i, f in enumerate(audio_files):
        t_title = track_titles[i] if i < len(track_titles) else f"Track {i + 1}"
        tracks.append(TrackMetadata(
            title=t_title,
            artist=args.get("artist", "Revvel"),
            album=args["title"],
            track_number=i + 1,
            genre=args.get("genre", "Alt Pop"),
            description=args.get("description", ""),
            seo_words=args.get("seo_words", ""),
        ))

    release = ReleaseMetadata(
        title=args["title"],
        artist=args.get("artist", "Revvel"),
        label=args.get("label", "HOTRS - House of the Rising Sun"),
        release_type=args.get("release_type", "single"),
        genre=args.get("genre", "Alt Pop"),
        tracks=tracks,
        description=args.get("description", ""),
        seo_words=args.get("seo_words", ""),
    )

    output_dir = args.get("output_dir", "./release")
    report = prepare_release_package(
        release, audio_files, output_dir,
        args.get("distributor", "landr"),
    )

    return json.dumps({
        "success": report.success,
        "package_dir": report.package_dir,
        "tracks_prepared": report.tracks_prepared,
        "files_created": report.files_created,
        "validation_errors": report.validation_errors,
        "validation_warnings": report.validation_warnings,
        "error": report.error,
    }, indent=2)


def handle_distributors(args: Dict[str, Any]) -> str:
    from engine.distribution import list_distributors
    return json.dumps({"distributors": list_distributors()}, indent=2)


def handle_pipeline(args: Dict[str, Any]) -> str:
    from engine.cleanup import run_cleanup_pipeline, CleanupConfig
    from engine.mastering import run_mastering_pipeline, MasteringConfig
    from engine.video import create_video, VideoConfig

    results = {"steps": []}

    # Cleanup
    cleanup_out = args.get("output_path") or args["input_path"].replace(".", "_cleaned.")
    cleanup_report = run_cleanup_pipeline(args["input_path"], cleanup_out, CleanupConfig())
    results["steps"].append({
        "step": "cleanup",
        "success": cleanup_report.success,
        "output": cleanup_report.output_file,
        "error": cleanup_report.error,
    })

    if not cleanup_report.success:
        return json.dumps(results, indent=2)

    # Mastering
    master_out = cleanup_report.output_file.replace("_cleaned", "_mastered")
    master_cfg = MasteringConfig(
        preset=args.get("preset", "default"),
        target_lufs=args.get("target_lufs", -14.0),
    )
    master_report = run_mastering_pipeline(cleanup_report.output_file, master_out, master_cfg)
    results["steps"].append({
        "step": "mastering",
        "success": master_report.success,
        "output": master_report.output_file,
        "output_lufs": master_report.output_lufs,
        "error": master_report.error,
    })

    if not master_report.success:
        return json.dumps(results, indent=2)

    # Video
    if args.get("create_video", True):
        video_out = master_report.output_file.replace(".wav", "_video.mp4")
        video_cfg = VideoConfig(video_type=args.get("video_type", "visualizer"))
        video_report = create_video(
            master_report.output_file, video_out,
            title=args.get("title", ""),
            artist=args.get("artist", "Revvel"),
            config=video_cfg,
        )
        results["steps"].append({
            "step": "video",
            "success": video_report.success,
            "output": video_report.output_video,
            "error": video_report.error,
        })

    results["final_audio"] = master_report.output_file
    results["success"] = all(s["success"] for s in results["steps"])
    return json.dumps(results, indent=2)


def handle_info(args: Dict[str, Any]) -> str:
    import shutil

    deps = {}
    for name, module in [
        ("numpy", "numpy"), ("scipy", "scipy"), ("librosa", "librosa"),
        ("soundfile", "soundfile"), ("noisereduce", "noisereduce"),
        ("pydub", "pydub"), ("edge-tts", "edge_tts"), ("pyloudnorm", "pyloudnorm"),
    ]:
        try:
            __import__(module)
            deps[name] = True
        except ImportError:
            deps[name] = False

    deps["ffmpeg"] = shutil.which("ffmpeg") is not None

    return json.dumps({
        "name": "Revvel Music Studio",
        "version": "1.0.0",
        "artist": "Revvel",
        "label": "HOTRS - House of the Rising Sun",
        "attribution": "Audio processing provided by free and open-source libraries.",
        "dependencies": deps,
    }, indent=2)


HANDLERS = {
    "revvel_cleanup": handle_cleanup,
    "revvel_master": handle_master,
    "revvel_separate": handle_separate,
    "revvel_tts": handle_tts,
    "revvel_voice_models": handle_voice_models,
    "revvel_voice_train": handle_voice_train,
    "revvel_video": handle_video,
    "revvel_distribute": handle_distribute,
    "revvel_distributors": handle_distributors,
    "revvel_pipeline": handle_pipeline,
    "revvel_info": handle_info,
}


# ─── MCP Server (SDK mode) ──────────────────────────────────────────────────

if HAS_MCP_SDK:
    server = Server("revvel-music-studio")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        handler = HANDLERS.get(name)
        if not handler:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            result = handler(arguments)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ─── Fallback STDIO Protocol (no SDK) ───────────────────────────────────────

def run_stdio_fallback():
    """Run a simple JSON-RPC over stdio MCP server without the SDK."""
    import sys

    def send_response(id, result=None, error=None):
        response = {"jsonrpc": "2.0", "id": id}
        if error:
            response["error"] = {"code": -32000, "message": str(error)}
        else:
            response["result"] = result
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            send_response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "revvel-music-studio",
                    "version": "1.0.0",
                },
            })
        elif method == "tools/list":
            send_response(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = HANDLERS.get(tool_name)
            if handler:
                try:
                    result = handler(arguments)
                    send_response(req_id, {
                        "content": [{"type": "text", "text": result}]
                    })
                except Exception as e:
                    send_response(req_id, error=str(e))
            else:
                send_response(req_id, error=f"Unknown tool: {tool_name}")
        elif method == "notifications/initialized":
            pass  # No response needed for notifications
        else:
            send_response(req_id, error=f"Unknown method: {method}")


# ─── Main ────────────────────────────────────────────────────────────────────

async def run_mcp_server():
    """Run the MCP server."""
    if HAS_MCP_SDK:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    else:
        run_stdio_fallback()


def main():
    """Entry point."""
    if HAS_MCP_SDK:
        asyncio.run(run_mcp_server())
    else:
        print("Running in fallback STDIO mode (install mcp SDK for full support)", file=sys.stderr)
        run_stdio_fallback()


if __name__ == "__main__":
    main()
