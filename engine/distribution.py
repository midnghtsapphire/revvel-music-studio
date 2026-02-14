"""
Distribution Helper Module
============================

Helps prepare music releases for distribution to DSPs
(Spotify, Apple Music, Amazon, etc.) via aggregators
like LANDR, Ditto, DistroKid, and CD Baby.

Features:
- Metadata validation and formatting
- ISRC code generation (placeholder format)
- Release package preparation
- Distributor-specific format checks
- Export release info in standard formats

Audio processing provided by free and open-source libraries.
"""

import os
import json
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, date


@dataclass
class TrackMetadata:
    """Metadata for a single track."""
    title: str = ""
    artist: str = "Revvel"
    album: str = ""
    track_number: int = 1
    genre: str = "Alt Pop"
    subgenre: str = ""
    isrc: str = ""  # International Standard Recording Code
    duration_seconds: float = 0.0
    bpm: float = 0.0
    key: str = ""
    language: str = "en"
    explicit: bool = False
    lyrics: str = ""
    songwriter: str = ""
    producer: str = ""
    description: str = ""
    seo_words: str = ""  # SEO-maximized words


@dataclass
class ReleaseMetadata:
    """Metadata for a release (single, EP, or album)."""
    title: str = ""
    artist: str = "Revvel"
    label: str = "HOTRS - House of the Rising Sun"
    release_type: str = "single"  # single, ep, album
    upc: str = ""  # Universal Product Code
    release_date: str = ""
    genre: str = "Alt Pop"
    subgenre: str = ""
    copyright_holder: str = "HOTRS - House of the Rising Sun"
    copyright_year: int = 0
    description: str = ""
    seo_words: str = ""
    tracks: List[TrackMetadata] = field(default_factory=list)
    artwork_path: str = ""
    distributor: str = ""


@dataclass
class DistributionReport:
    """Report of distribution preparation."""
    release_title: str = ""
    package_dir: str = ""
    tracks_prepared: int = 0
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


# Supported distributors and their requirements
DISTRIBUTORS = {
    "landr": {
        "name": "LANDR",
        "url": "https://www.landr.com",
        "audio_formats": ["wav", "flac"],
        "min_sample_rate": 44100,
        "min_bit_depth": 16,
        "artwork_min_size": 3000,
        "artwork_formats": ["jpg", "png"],
        "keeps_music_up": True,
        "commission": "15% after cancellation",
        "pricing": "From $89/year",
        "features": ["Distribution", "Mastering", "Samples", "Plugins"],
    },
    "ditto": {
        "name": "Ditto Music",
        "url": "https://dittomusic.com",
        "audio_formats": ["wav", "flac"],
        "min_sample_rate": 44100,
        "min_bit_depth": 16,
        "artwork_min_size": 3000,
        "artwork_formats": ["jpg", "png"],
        "keeps_music_up": False,
        "commission": "0%",
        "pricing": "$19/year per artist",
        "features": ["Unlimited releases", "Label features", "Analytics"],
    },
    "distrokid": {
        "name": "DistroKid",
        "url": "https://distrokid.com",
        "audio_formats": ["wav", "flac"],
        "min_sample_rate": 44100,
        "min_bit_depth": 16,
        "artwork_min_size": 3000,
        "artwork_formats": ["jpg", "png"],
        "keeps_music_up": False,
        "commission": "0%",
        "pricing": "$22.99/year",
        "features": ["Unlimited releases", "Spotify verification", "Lyrics"],
    },
    "cdbaby": {
        "name": "CD Baby",
        "url": "https://cdbaby.com",
        "audio_formats": ["wav"],
        "min_sample_rate": 44100,
        "min_bit_depth": 16,
        "artwork_min_size": 3000,
        "artwork_formats": ["jpg"],
        "keeps_music_up": True,
        "commission": "9%",
        "pricing": "$9.95/single, $29/album (one-time)",
        "features": ["Sync licensing", "Publishing", "Physical distribution"],
    },
    "amuse": {
        "name": "Amuse",
        "url": "https://amuse.io",
        "audio_formats": ["wav", "flac"],
        "min_sample_rate": 44100,
        "min_bit_depth": 16,
        "artwork_min_size": 3000,
        "artwork_formats": ["jpg", "png"],
        "keeps_music_up": True,
        "commission": "15% (free tier)",
        "pricing": "Free / $5.99/mo (Pro)",
        "features": ["Free tier", "Label features", "Analytics"],
    },
}

# DSPs (Digital Service Providers) that distributors deliver to
DSPS = [
    "Spotify", "Apple Music", "Amazon Music", "YouTube Music",
    "Tidal", "Deezer", "Pandora", "iHeartRadio",
    "TikTok", "Instagram/Facebook", "Shazam",
    "SoundCloud (Go+)", "Tencent", "NetEase",
]


def generate_isrc(country: str = "US", registrant: str = "HRS", year: int = 0) -> str:
    """
    Generate an ISRC-format code.
    Format: CC-XXX-YY-NNNNN
    Note: For official ISRCs, register with your national ISRC agency.
    """
    if year == 0:
        year = datetime.now().year % 100

    # Generate a unique 5-digit number based on timestamp
    unique = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:5]
    unique_num = int(unique, 16) % 100000

    return f"{country}{registrant}{year:02d}{unique_num:05d}"


def validate_track(track: TrackMetadata) -> List[str]:
    """Validate track metadata and return list of issues."""
    errors = []

    if not track.title:
        errors.append("Track title is required")
    if not track.artist:
        errors.append("Artist name is required")
    if len(track.title) > 200:
        errors.append("Track title exceeds 200 characters")
    if track.title != track.title.strip():
        errors.append("Track title has leading/trailing whitespace")

    return errors


def validate_release(release: ReleaseMetadata) -> List[str]:
    """Validate release metadata and return list of issues."""
    errors = []

    if not release.title:
        errors.append("Release title is required")
    if not release.artist:
        errors.append("Artist name is required")
    if not release.tracks:
        errors.append("At least one track is required")

    # Check artwork
    if release.artwork_path:
        if not os.path.exists(release.artwork_path):
            errors.append(f"Artwork file not found: {release.artwork_path}")
        else:
            ext = os.path.splitext(release.artwork_path)[1].lower().lstrip('.')
            if ext not in ['jpg', 'jpeg', 'png']:
                errors.append(f"Artwork must be JPG or PNG, got: {ext}")

    # Check release type vs track count
    if release.release_type == "single" and len(release.tracks) > 3:
        errors.append("Singles should have 1-3 tracks")
    elif release.release_type == "ep" and (len(release.tracks) < 2 or len(release.tracks) > 6):
        errors.append("EPs should have 2-6 tracks")

    # Validate each track
    for i, track in enumerate(release.tracks):
        track_errors = validate_track(track)
        for err in track_errors:
            errors.append(f"Track {i + 1}: {err}")

    return errors


def prepare_release_package(
    release: ReleaseMetadata,
    audio_files: List[str],
    output_dir: str,
    distributor: str = "landr",
) -> DistributionReport:
    """
    Prepare a complete release package for distribution.

    Creates a directory with:
    - Audio files (validated format)
    - Metadata JSON
    - Artwork (if provided)
    - Distributor-specific notes
    """
    report = DistributionReport(release_title=release.title)

    os.makedirs(output_dir, exist_ok=True)
    report.package_dir = output_dir

    # Set defaults
    if not release.copyright_year:
        release.copyright_year = datetime.now().year
    if not release.release_date:
        release.release_date = date.today().isoformat()

    # Validate
    errors = validate_release(release)
    report.validation_errors = errors

    if errors:
        report.error = f"Validation failed with {len(errors)} error(s)"
        return report

    try:
        # Generate ISRCs for tracks without them
        for track in release.tracks:
            if not track.isrc:
                track.isrc = generate_isrc()

        # Copy and validate audio files
        import soundfile as sf
        import shutil

        dist_info = DISTRIBUTORS.get(distributor, DISTRIBUTORS["landr"])

        for i, (track, audio_path) in enumerate(zip(release.tracks, audio_files)):
            if not os.path.exists(audio_path):
                report.validation_warnings.append(f"Audio file not found: {audio_path}")
                continue

            # Check audio format
            info = sf.info(audio_path)
            if info.samplerate < dist_info["min_sample_rate"]:
                report.validation_warnings.append(
                    f"Track {i + 1}: Sample rate {info.samplerate}Hz is below "
                    f"minimum {dist_info['min_sample_rate']}Hz for {dist_info['name']}"
                )

            # Copy audio file
            dest = os.path.join(output_dir, f"{i + 1:02d}_{track.title.replace(' ', '_')}.wav")
            shutil.copy2(audio_path, dest)
            report.files_created.append(dest)
            report.tracks_prepared += 1

            # Update track duration
            track.duration_seconds = info.duration

        # Copy artwork
        if release.artwork_path and os.path.exists(release.artwork_path):
            ext = os.path.splitext(release.artwork_path)[1]
            artwork_dest = os.path.join(output_dir, f"artwork{ext}")
            shutil.copy2(release.artwork_path, artwork_dest)
            report.files_created.append(artwork_dest)

        # Save metadata
        metadata = {
            "release": asdict(release),
            "distributor": distributor,
            "distributor_info": dist_info,
            "prepared_at": datetime.now().isoformat(),
            "dsps": DSPS,
        }
        # Remove tracks list from release (saved separately)
        metadata["release"]["tracks"] = [asdict(t) for t in release.tracks]

        meta_path = os.path.join(output_dir, "release_metadata.json")
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        report.files_created.append(meta_path)

        # Create distributor-specific README
        readme = generate_distributor_readme(release, dist_info, distributor)
        readme_path = os.path.join(output_dir, "UPLOAD_INSTRUCTIONS.md")
        with open(readme_path, 'w') as f:
            f.write(readme)
        report.files_created.append(readme_path)

        report.success = True

    except Exception as e:
        report.error = str(e)

    return report


def generate_distributor_readme(
    release: ReleaseMetadata,
    dist_info: Dict,
    distributor: str,
) -> str:
    """Generate upload instructions for a specific distributor."""
    tracks_list = "\n".join(
        f"  {i + 1}. {t.title} (ISRC: {t.isrc})"
        for i, t in enumerate(release.tracks)
    )

    return f"""# Upload Instructions for {dist_info['name']}

## Release: {release.title}
**Artist:** {release.artist}
**Label:** {release.label}
**Type:** {release.release_type.upper()}
**Release Date:** {release.release_date}

## Tracks
{tracks_list}

## Upload Steps

1. Go to [{dist_info['name']}]({dist_info['url']}) and log in
2. Click "New Release" or "Upload"
3. Select release type: {release.release_type}
4. Upload audio files from this package directory
5. Upload artwork (minimum {dist_info.get('artwork_min_size', 3000)}x{dist_info.get('artwork_min_size', 3000)} pixels)
6. Fill in metadata:
   - Title: {release.title}
   - Artist: {release.artist}
   - Label: {release.label}
   - Genre: {release.genre}
   - Copyright: (C) {release.copyright_year} {release.copyright_holder}
7. Enter ISRC codes for each track (provided above)
8. Set release date: {release.release_date}
9. Review and submit

## Distributor Details
- **Pricing:** {dist_info.get('pricing', 'N/A')}
- **Commission:** {dist_info.get('commission', 'N/A')}
- **Keeps music up after cancellation:** {'Yes' if dist_info.get('keeps_music_up') else 'No'}
- **Features:** {', '.join(dist_info.get('features', []))}

## DSPs Your Music Will Reach
{chr(10).join(f'- {dsp}' for dsp in DSPS)}

---
*Package prepared by Revvel Music Studio*
*Audio processing provided by free and open-source libraries*
"""


def list_distributors() -> List[Dict[str, Any]]:
    """List all supported distributors with their details."""
    return [
        {"id": k, **v}
        for k, v in DISTRIBUTORS.items()
    ]


def get_distributor_info(distributor_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed info about a specific distributor."""
    if distributor_id in DISTRIBUTORS:
        return {"id": distributor_id, **DISTRIBUTORS[distributor_id]}
    return None
