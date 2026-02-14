#!/usr/bin/env python3
"""
Revvel Music Studio - CLI Tool
================================

Command-line interface for the Revvel Music Studio audio processing engine.

Usage:
    revvel cleanup <input> [options]
    revvel master <input> [options]
    revvel separate <input> [options]
    revvel voice tts <text> [options]
    revvel voice models
    revvel voice train <audio_files...> [options]
    revvel video <input> [options]
    revvel distribute <input_files...> [options]
    revvel pipeline <input> [options]
    revvel info

Artist: Revvel
Label: HOTRS (House of the Rising Sun)
Audio processing provided by free and open-source libraries.
"""

import os
import sys
import json
import argparse
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ███████╗██╗   ██╗██╗   ██╗███████╗██╗             ║
║   ██╔══██╗██╔════╝██║   ██║██║   ██║██╔════╝██║             ║
║   ██████╔╝█████╗  ██║   ██║██║   ██║█████╗  ██║             ║
║   ██╔══██╗██╔══╝  ╚██╗ ██╔╝╚██╗ ██╔╝██╔══╝  ██║             ║
║   ██║  ██║███████╗ ╚████╔╝  ╚████╔╝ ███████╗███████╗        ║
║   ╚═╝  ╚═╝╚══════╝  ╚═══╝    ╚═══╝  ╚══════╝╚══════╝        ║
║                                                              ║
║   M U S I C   S T U D I O                                   ║
║   HOTRS - House of the Rising Sun                            ║
║                                                              ║
║   Audio processing provided by free & open-source libraries  ║
╚══════════════════════════════════════════════════════════════╝
"""


def print_banner():
    print(BANNER)


def print_success(msg):
    print(f"\033[92m✓ {msg}\033[0m")


def print_error(msg):
    print(f"\033[91m✗ {msg}\033[0m")


def print_info(msg):
    print(f"\033[94mℹ {msg}\033[0m")


def print_step(msg):
    print(f"\033[93m→ {msg}\033[0m")


def cmd_cleanup(args):
    """Run audio cleanup pipeline."""
    from engine.cleanup import run_cleanup_pipeline, CleanupConfig

    print_step(f"Cleaning up: {args.input}")

    config = CleanupConfig(
        noise_reduce=not args.no_noise_reduce,
        noise_reduce_strength=args.noise_strength,
        remove_pops=not args.no_pop_remove,
        pop_threshold=args.pop_threshold,
        deess=not args.no_deess,
        remove_hum=not args.no_hum_remove,
        hum_frequency=args.hum_freq,
        pitch_correct=args.pitch_correct,
        pitch_correction_strength=args.pitch_strength,
        pitch_key=args.key,
        target_sample_rate=args.sample_rate,
        output_format=args.format,
    )

    report = run_cleanup_pipeline(args.input, args.output, config)

    if report.success:
        print_success(f"Cleaned audio saved to: {report.output_file}")
        for op in report.operations:
            print_info(f"  {op}")
        if report.pops_detected > 0:
            print_info(f"  Pops/clicks detected and removed: {report.pops_detected}")
    else:
        print_error(f"Cleanup failed: {report.error}")
        sys.exit(1)


def cmd_master(args):
    """Run mastering pipeline."""
    from engine.mastering import run_mastering_pipeline, MasteringConfig

    print_step(f"Mastering: {args.input} (preset: {args.preset})")

    config = MasteringConfig(
        preset=args.preset,
        target_lufs=args.lufs,
        target_sample_rate=args.sample_rate,
        output_format=args.format,
        stereo_width=args.stereo_width,
    )

    report = run_mastering_pipeline(args.input, args.output, config)

    if report.success:
        print_success(f"Mastered audio saved to: {report.output_file}")
        for op in report.operations:
            print_info(f"  {op}")
    else:
        print_error(f"Mastering failed: {report.error}")
        sys.exit(1)


def cmd_separate(args):
    """Run stem separation."""
    from engine.separation import separate_stems, SeparationConfig

    print_step(f"Separating stems: {args.input}")

    config = SeparationConfig(
        model=args.model,
        two_stems=args.two_stems,
    )

    report = separate_stems(args.input, args.output_dir, config)

    if report.success:
        print_success(f"Stems created in: {report.output_dir}")
        for stem, path in report.stem_files.items():
            print_info(f"  {stem}: {path}")
    else:
        print_error(f"Separation failed: {report.error}")
        sys.exit(1)


def cmd_voice_tts(args):
    """Text-to-speech."""
    from engine.voice import text_to_speech

    print_step(f"Generating speech: \"{args.text[:50]}...\"")

    report = text_to_speech(args.text, args.output, voice=args.voice)

    if report.success:
        print_success(f"Speech saved to: {report.output_file}")
        print_info(f"  Engine: {report.model_used}")
    else:
        print_error(f"TTS failed: {report.error}")
        sys.exit(1)


def cmd_voice_models(args):
    """List voice models."""
    from engine.voice import list_voice_models

    models = list_voice_models()
    print_info(f"Available voice models ({len(models)}):")
    for m in models:
        print(f"  • {m.name} [{m.model_type}] - {m.description}")


def cmd_voice_train(args):
    """Train a voice model."""
    from engine.voice import train_voice_model

    print_step(f"Training voice model: {args.name}")

    report = train_voice_model(
        args.audio_files,
        args.name,
        description=args.description,
    )

    if report.success:
        print_success(f"Voice model prepared: {report.output_file}")
    else:
        print_error(f"Training failed: {report.error}")
        sys.exit(1)


def cmd_video(args):
    """Generate video."""
    from engine.video import create_video, VideoConfig

    print_step(f"Creating {args.type} video: {args.input}")

    config = VideoConfig(
        video_type=args.type,
        width=args.width,
        height=args.height,
    )

    report = create_video(
        args.input, args.output,
        title=args.title, artist=args.artist,
        config=config,
    )

    if report.success:
        print_success(f"Video saved to: {report.output_video}")
        print_info(f"  Resolution: {report.resolution}")
    else:
        print_error(f"Video generation failed: {report.error}")
        sys.exit(1)


def cmd_distribute(args):
    """Prepare distribution package."""
    from engine.distribution import (
        prepare_release_package, ReleaseMetadata, TrackMetadata
    )

    print_step(f"Preparing release: {args.title} for {args.distributor}")

    tracks = []
    titles = args.track_titles.split(",") if args.track_titles else []
    for i, f in enumerate(args.input_files):
        t_title = titles[i].strip() if i < len(titles) else f"Track {i + 1}"
        tracks.append(TrackMetadata(
            title=t_title,
            artist=args.artist,
            album=args.title,
            track_number=i + 1,
            genre=args.genre,
            description=args.description or "",
            seo_words=args.seo_words or "",
        ))

    release = ReleaseMetadata(
        title=args.title,
        artist=args.artist,
        label=args.label,
        release_type=args.release_type,
        genre=args.genre,
        tracks=tracks,
        description=args.description or "",
        seo_words=args.seo_words or "",
    )

    report = prepare_release_package(
        release, args.input_files, args.output_dir, args.distributor
    )

    if report.success:
        print_success(f"Release package created: {report.package_dir}")
        print_info(f"  Tracks prepared: {report.tracks_prepared}")
        for f in report.files_created:
            print_info(f"  {f}")
    else:
        print_error(f"Distribution prep failed: {report.error}")
        if report.validation_errors:
            for err in report.validation_errors:
                print_error(f"  {err}")
        sys.exit(1)


def cmd_distributors(args):
    """List distributors."""
    from engine.distribution import list_distributors

    dists = list_distributors()
    print_info(f"Supported distributors ({len(dists)}):")
    for d in dists:
        keeps = "✓ keeps music up" if d.get("keeps_music_up") else "✗ removes on cancel"
        print(f"\n  {d['name']} ({d['id']})")
        print(f"    URL: {d['url']}")
        print(f"    Pricing: {d['pricing']}")
        print(f"    Commission: {d['commission']}")
        print(f"    {keeps}")
        print(f"    Features: {', '.join(d.get('features', []))}")


def cmd_pipeline(args):
    """Run full production pipeline."""
    from engine.cleanup import run_cleanup_pipeline, CleanupConfig
    from engine.mastering import run_mastering_pipeline, MasteringConfig
    from engine.video import create_video, VideoConfig

    print_banner()
    start = time.time()

    # Step 1: Cleanup
    print_step("[1/3] Cleaning audio...")
    cleanup_out = args.output or args.input.replace(".", "_cleaned.")
    cleanup_report = run_cleanup_pipeline(args.input, cleanup_out, CleanupConfig())

    if not cleanup_report.success:
        print_error(f"Cleanup failed: {cleanup_report.error}")
        sys.exit(1)
    print_success(f"Cleaned: {cleanup_report.output_file}")

    # Step 2: Master
    print_step(f"[2/3] Mastering (preset: {args.preset})...")
    master_out = cleanup_report.output_file.replace("_cleaned", "_mastered")
    master_config = MasteringConfig(preset=args.preset, target_lufs=args.lufs)
    master_report = run_mastering_pipeline(cleanup_report.output_file, master_out, master_config)

    if not master_report.success:
        print_error(f"Mastering failed: {master_report.error}")
        sys.exit(1)
    print_success(f"Mastered: {master_report.output_file} ({master_report.output_lufs:.1f} LUFS)")

    # Step 3: Video
    if not args.no_video:
        print_step("[3/3] Generating video...")
        video_out = master_report.output_file.replace(".wav", "_video.mp4").replace(".flac", "_video.mp4")
        video_config = VideoConfig(video_type=args.video_type)
        video_report = create_video(
            master_report.output_file, video_out,
            title=args.title, artist=args.artist,
            config=video_config,
        )
        if video_report.success:
            print_success(f"Video: {video_report.output_video}")
        else:
            print_error(f"Video failed: {video_report.error}")
    else:
        print_info("[3/3] Video generation skipped")

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print_success(f"Pipeline complete in {elapsed:.1f}s")
    print_info(f"Final audio: {master_report.output_file}")


def cmd_info(args):
    """Show system info."""
    print_banner()
    print("  Version:  1.0.0")
    print("  Artist:   Revvel")
    print("  Label:    HOTRS - House of the Rising Sun")
    print("  Engine:   FOSS audio processing")
    print()

    # Check dependencies
    deps = {
        "numpy": "numpy",
        "scipy": "scipy",
        "librosa": "librosa",
        "soundfile": "soundfile",
        "noisereduce": "noisereduce",
        "pydub": "pydub",
        "edge-tts": "edge_tts",
        "pyloudnorm": "pyloudnorm",
        "ffmpeg": None,
    }

    print("  Dependencies:")
    for name, module in deps.items():
        if module:
            try:
                __import__(module)
                print(f"    ✓ {name}")
            except ImportError:
                print(f"    ✗ {name} (not installed)")
        else:
            import shutil
            if shutil.which(name):
                print(f"    ✓ {name}")
            else:
                print(f"    ✗ {name} (not found)")


def main():
    parser = argparse.ArgumentParser(
        prog="revvel",
        description="Revvel Music Studio - Professional Music Production CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  revvel cleanup song.wav -o cleaned.wav
  revvel master song.wav --preset warm --lufs -14
  revvel separate song.wav --output-dir ./stems
  revvel voice tts "Hello world" -o speech.wav
  revvel voice models
  revvel video song.wav --type visualizer --title "My Song"
  revvel distribute song.wav --title "My Single" --distributor ditto
  revvel pipeline song.wav --preset cinematic --title "My Song"
  revvel distributors
  revvel info

Audio processing provided by free and open-source libraries.
HOTRS - House of the Rising Sun
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── cleanup ──
    p_cleanup = subparsers.add_parser("cleanup", help="Clean up audio (noise, pops, hum)")
    p_cleanup.add_argument("input", help="Input audio file")
    p_cleanup.add_argument("-o", "--output", help="Output file path")
    p_cleanup.add_argument("--no-noise-reduce", action="store_true")
    p_cleanup.add_argument("--noise-strength", type=float, default=0.75)
    p_cleanup.add_argument("--no-pop-remove", action="store_true")
    p_cleanup.add_argument("--pop-threshold", type=float, default=3.5)
    p_cleanup.add_argument("--no-deess", action="store_true")
    p_cleanup.add_argument("--no-hum-remove", action="store_true")
    p_cleanup.add_argument("--hum-freq", type=float, default=60.0)
    p_cleanup.add_argument("--pitch-correct", action="store_true")
    p_cleanup.add_argument("--pitch-strength", type=float, default=0.8)
    p_cleanup.add_argument("--key", default="C", help="Musical key for pitch correction")
    p_cleanup.add_argument("--sample-rate", type=int, default=96000)
    p_cleanup.add_argument("--format", default="wav", choices=["wav", "flac"])
    p_cleanup.set_defaults(func=cmd_cleanup)

    # ── master ──
    p_master = subparsers.add_parser("master", help="Master audio")
    p_master.add_argument("input", help="Input audio file")
    p_master.add_argument("-o", "--output", help="Output file path")
    p_master.add_argument("--preset", default="default",
                          choices=["default", "warm", "bright", "punchy", "gentle", "kpop", "cinematic", "indie_folk"])
    p_master.add_argument("--lufs", type=float, default=-14.0)
    p_master.add_argument("--sample-rate", type=int, default=96000)
    p_master.add_argument("--format", default="wav", choices=["wav", "flac"])
    p_master.add_argument("--stereo-width", type=float, default=1.2)
    p_master.set_defaults(func=cmd_master)

    # ── separate ──
    p_sep = subparsers.add_parser("separate", help="Separate audio into stems")
    p_sep.add_argument("input", help="Input audio file")
    p_sep.add_argument("--output-dir", help="Output directory for stems")
    p_sep.add_argument("--model", default="htdemucs",
                       choices=["htdemucs", "htdemucs_ft", "mdx_extra"])
    p_sep.add_argument("--two-stems", help="Split into two stems (e.g., 'vocals')")
    p_sep.set_defaults(func=cmd_separate)

    # ── voice ──
    p_voice = subparsers.add_parser("voice", help="Voice synthesis and management")
    voice_sub = p_voice.add_subparsers(dest="voice_command")

    p_tts = voice_sub.add_parser("tts", help="Text-to-speech")
    p_tts.add_argument("text", help="Text to speak")
    p_tts.add_argument("-o", "--output", default="speech.wav")
    p_tts.add_argument("--voice", default="en-US-GuyNeural")
    p_tts.set_defaults(func=cmd_voice_tts)

    p_models = voice_sub.add_parser("models", help="List voice models")
    p_models.set_defaults(func=cmd_voice_models)

    p_train = voice_sub.add_parser("train", help="Train a voice model")
    p_train.add_argument("audio_files", nargs="+", help="Audio files for training")
    p_train.add_argument("--name", required=True, help="Model name")
    p_train.add_argument("--description", default="")
    p_train.set_defaults(func=cmd_voice_train)

    # ── video ──
    p_video = subparsers.add_parser("video", help="Generate music video")
    p_video.add_argument("input", help="Input audio file")
    p_video.add_argument("-o", "--output", help="Output video file")
    p_video.add_argument("--title", default="")
    p_video.add_argument("--artist", default="Revvel")
    p_video.add_argument("--type", default="visualizer",
                         choices=["visualizer", "spectrum", "static"])
    p_video.add_argument("--width", type=int, default=1920)
    p_video.add_argument("--height", type=int, default=1080)
    p_video.set_defaults(func=cmd_video)

    # ── distribute ──
    p_dist = subparsers.add_parser("distribute", help="Prepare release for distribution")
    p_dist.add_argument("input_files", nargs="+", help="Audio files for the release")
    p_dist.add_argument("--title", required=True, help="Release title")
    p_dist.add_argument("--artist", default="Revvel")
    p_dist.add_argument("--label", default="HOTRS - House of the Rising Sun")
    p_dist.add_argument("--release-type", default="single", choices=["single", "ep", "album"])
    p_dist.add_argument("--genre", default="Alt Pop")
    p_dist.add_argument("--distributor", default="landr",
                        choices=["landr", "ditto", "distrokid", "cdbaby", "amuse"])
    p_dist.add_argument("--track-titles", help="Comma-separated track titles")
    p_dist.add_argument("--output-dir", default="./release")
    p_dist.add_argument("--description", default="")
    p_dist.add_argument("--seo-words", default="")
    p_dist.set_defaults(func=cmd_distribute)

    # ── distributors ──
    p_dists = subparsers.add_parser("distributors", help="List supported distributors")
    p_dists.set_defaults(func=cmd_distributors)

    # ── pipeline ──
    p_pipe = subparsers.add_parser("pipeline", help="Run full production pipeline")
    p_pipe.add_argument("input", help="Input audio file")
    p_pipe.add_argument("-o", "--output", help="Output file path")
    p_pipe.add_argument("--title", default="")
    p_pipe.add_argument("--artist", default="Revvel")
    p_pipe.add_argument("--preset", default="default",
                        choices=["default", "warm", "bright", "punchy", "gentle", "kpop", "cinematic", "indie_folk"])
    p_pipe.add_argument("--lufs", type=float, default=-14.0)
    p_pipe.add_argument("--no-video", action="store_true")
    p_pipe.add_argument("--video-type", default="visualizer",
                        choices=["visualizer", "spectrum", "static"])
    p_pipe.set_defaults(func=cmd_pipeline)

    # ── info ──
    p_info = subparsers.add_parser("info", help="Show system info")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
