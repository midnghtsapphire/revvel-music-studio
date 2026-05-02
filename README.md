# Revvel Music Studio

**Professional Music Production & Distribution Platform**

**Artist:** Revvel | **Label:** HOTRS (House of the Rising Sun)

Audio processing provided by free and open-source libraries: librosa, noisereduce, pydub, demucs, pyloudnorm, and ffmpeg.

---

## Overview

Revvel Music Studio is a comprehensive music production and distribution toolkit designed for independent artists. It provides studio-grade audio processing, voice synthesis, automatic video generation, and distribution preparation — all from a single unified platform available as a CLI tool, REST API, MCP server, or standalone executable.

### Key Features

| Feature | Description |
|---|---|
| **Audio Cleanup** | Noise reduction, pop/click removal, de-essing, hum removal, pitch correction |
| **Mastering** | Professional EQ, compression, stereo enhancement, limiting, loudness normalization |
| **Stem Separation** | Isolate vocals, drums, bass, and instruments using Meta's Demucs |
| **Voice Synthesis** | Text-to-speech, voice model training, voice conversion (RVC) |
| **Video Generation** | Waveform visualizer, spectrum analyzer, static image videos |
| **Distribution** | Package releases for LANDR, Ditto, DistroKid, CD Baby, Amuse |
| **Full Pipeline** | One-command workflow: cleanup → master → video → distribute |

### Output Quality

All audio is processed and exported at **96kHz / 24-bit lossless stereo WAV** by default, exceeding the requirements of all major streaming platforms.

---

## Installation

### Prerequisites

- Python 3.9 or higher
- FFmpeg (for video generation and audio format conversion)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/MIDNGHTSAPPHIRE/revvel-music-studio.git
cd revvel-music-studio

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m cli.main info
```

### Install with pip

```bash
pip install -e .

# With all optional dependencies
pip install -e ".[all]"
```

### Docker

```bash
docker build -t revvel-music-studio .
docker run -p 8000:8000 revvel-music-studio
```

---

## Usage

### 1. CLI Tool

```bash
# Audio cleanup (removes noise, pops, hum)
python -m cli.main cleanup song.wav -o cleaned.wav

# Master with a preset
python -m cli.main master song.wav --preset warm --lufs -14

# Separate stems
python -m cli.main separate song.wav --output-dir ./stems

# Text-to-speech
python -m cli.main voice tts "Hello world" -o speech.wav

# Generate video
python -m cli.main video song.wav --type visualizer --title "My Song"

# Prepare for distribution
python -m cli.main distribute song.wav --title "My Single" --distributor ditto

# Full pipeline (cleanup → master → video)
python -m cli.main pipeline song.wav --preset cinematic --title "My Song"

# List distributors
python -m cli.main distributors

# System info
python -m cli.main info
```

### 2. FastAPI Server

```bash
# Start the API server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# API docs available at http://localhost:8000/docs
```

#### Authentication

```bash
# Get a token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "revvel", "password": "hotrs2026"}'

# Use the token
curl -X POST http://localhost:8000/cleanup \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@song.wav"
```

#### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/token` | Get JWT access token |
| GET | `/auth/me` | Get current user info |
| POST | `/cleanup` | Clean up audio |
| POST | `/master` | Master audio |
| POST | `/separate` | Separate stems |
| POST | `/voice/tts` | Text-to-speech |
| GET | `/voice/models` | List voice models |
| POST | `/voice/train` | Train voice model |
| POST | `/video` | Generate video |
| GET | `/distribution/distributors` | List distributors |
| POST | `/distribution/prepare` | Prepare release |
| POST | `/pipeline/full` | Full production pipeline |
| GET | `/download/{filename}` | Download processed file |

### 3. MCP Server

For use with Claude Desktop, Manus, or other MCP-compatible AI assistants.

```bash
# Run the MCP server
python -m mcp_server.main
```

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "revvel-music-studio": {
      "command": "python3",
      "args": ["-m", "mcp_server.main"],
      "cwd": "/path/to/revvel-music-studio"
    }
  }
}
```

#### Available MCP Tools

| Tool | Description |
|---|---|
| `revvel_cleanup` | Clean up audio files |
| `revvel_master` | Master audio with presets |
| `revvel_separate` | Separate stems |
| `revvel_tts` | Text-to-speech |
| `revvel_voice_models` | List voice models |
| `revvel_voice_train` | Train voice model |
| `revvel_video` | Generate music video |
| `revvel_distribute` | Prepare distribution package |
| `revvel_distributors` | List distributors |
| `revvel_pipeline` | Full production pipeline |
| `revvel_info` | System information |

### 4. Standalone Executable

```bash
# Build the executable
python build_exe.py

# Run
./dist/revvel cleanup song.wav -o cleaned.wav
./dist/revvel pipeline song.wav --preset warm
```

### 5. Token-Based API Access

All API endpoints (except `/auth/token` and `/`) require a JWT bearer token. Tokens are valid for 72 hours.

```python
import requests

# Get token
resp = requests.post("http://localhost:8000/auth/token", json={
    "username": "revvel",
    "password": "hotrs2026"
})
token = resp.json()["access_token"]

# Use token for all requests
headers = {"Authorization": f"Bearer {token}"}

# Upload and clean audio
with open("song.wav", "rb") as f:
    resp = requests.post(
        "http://localhost:8000/cleanup",
        headers=headers,
        files={"audio": f}
    )
print(resp.json())
```

---

## Mastering Presets

| Preset | Best For | Character |
|---|---|---|
| `default` | General purpose | Balanced EQ, moderate compression |
| `warm` | Alt R&B, Soul | Enhanced lows, smooth highs |
| `bright` | Pop, K-pop | Crisp highs, present mids |
| `punchy` | Hip-hop, Electronic | Strong lows, fast compression |
| `gentle` | Folk, Acoustic | Light touch, natural dynamics |
| `kpop` | K-pop, J-pop | Wide stereo, bright and polished |
| `cinematic` | Film scores, Ambient | Deep bass, wide stereo field |
| `indie_folk` | Indie, Folk-rock | Warm and organic |

---

## Distribution Guide

See [DISTRIBUTION_GUIDE.md](DISTRIBUTION_GUIDE.md) for a comprehensive guide on:

- How music distribution works
- Choosing the right distributor
- Preparing your release
- Copyright and royalties
- ISRC and UPC codes
- Recommended recording equipment

---

## Project Structure

```
revvel-music-studio/
├── engine/                 # Core audio processing engine
│   ├── cleanup.py          # Noise reduction, pop removal, de-essing
│   ├── mastering.py        # EQ, compression, limiting, loudness
│   ├── separation.py       # Stem separation (Demucs)
│   ├── voice.py            # Voice synthesis and cloning
│   ├── video.py            # Video generation
│   └── distribution.py     # Distribution preparation
├── api/                    # FastAPI REST server
│   └── main.py             # API endpoints with JWT auth
├── cli/                    # Command-line interface
│   └── main.py             # CLI commands
├── mcp_server/             # MCP server
│   └── main.py             # MCP tool definitions
├── models/                 # Voice models directory
├── data/                   # Upload and output directories
├── setup.py                # pip installation
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── build_exe.py            # PyInstaller build script
├── mcp_config.json         # MCP client configuration
├── DISTRIBUTION_GUIDE.md   # Comprehensive distribution guide
└── README.md               # This file
```

---

## License

MIT License

Copyright (c) 2026 HOTRS - House of the Rising Sun

---

## Attribution

Audio processing provided by free and open-source libraries:

- [librosa](https://librosa.org/) - Audio analysis
- [noisereduce](https://github.com/timsainb/noisereduce) - Noise reduction
- [pydub](https://github.com/jiaaro/pydub) - Audio manipulation
- [Demucs](https://github.com/facebookresearch/demucs) - Stem separation
- [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) - Loudness measurement
- [Edge TTS](https://github.com/rany2/edge-tts) - Text-to-speech
- [FFmpeg](https://ffmpeg.org/) - Audio/video processing
- [SciPy](https://scipy.org/) - Signal processing

---

## Test

| Feature | Status | Notes |
|--------|--------|-------|
| Audio Cleanup | ✅ Ready | Requires FFmpeg |
| Mastering | ✅ Ready | Requires FFmpeg |
| Stem Separation | ✅ Ready | Requires FFmpeg |
| Voice Synthesis | ✅ Ready | Requires FFmpeg |
| Video Generation | ✅ Ready | Requires FFmpeg |
| CLI Tool | ✅ Ready | `python -m revvel_music_studio` |
| Build Exe | ✅ Ready | `python build_exe.py` |

**Requirements:** Python 3.9+, FFmpeg

**Quick Test:**
```bash
pip install -r requirements.txt
python -m revvel_music_studio --help
```

---

## Deployment

**Production:** https://revvel-music-studio.vercel.app (for web UI if deployed)
**CLI:** Available via npm/pip
**MCP Server:** Available via `mcp_config.json`

**Web UIs Available:**
- `index.html` — Main application
- `voice-editor.html` — Voice synthesis
- `status-checker.html` — Distribution status
- `ops-board.html` — Operations dashboard
