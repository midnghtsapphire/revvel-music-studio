# Coding & Organization Standards

## 1. Folder Structure

/scripts              # Reusable automation, CLI, helper scripts
/api                  # REST API endpoints, FastAPI code
/cli                  # Command-line tools and wrappers
/engine               # Core processing logic (audio, pipeline, main)
/data                 # Sample, demo, input/output data
/models               # ML models, neural nets, etc.
/tests                # Unit/integration tests, test wavs/mp3s
/docs                 # Developer docs, API docs, standards, guides

## 2. Filename Standards

- Use lower_snake_case.py for all Python scripts
- Prefix scripts for clarity: noise_remove.py, pitchfix.py, profanity_remove.py, quickfix_cli.py, fastapi_quickfix.py
- Name test scripts with test_*.py
- Include 'api' in REST endpoint scripts (fastapi_quickfix.py)
- CLI entry points named for their major function

## 3. Extra Features & Reusability

- Accept arguments via CLI (argparse/click)
- Document each function with docstrings
- Scripts should be self-contained, composable
- Support batch input/output, folder mode
- Provide --help flag in CLI scripts
- Modularize shared logic (audio_util.py)
- Log progress/errors
- Output to separate file/folder by default
- Add fallback checks for missing dependencies
- Test scripts: verify before/after effects

## 4. Example Feature: Batch CLI Usage
import glob
import os
from noise_remove import remove_noise

def batch_remove_noise(input_folder, output_folder):
    for wav_path in glob.glob(os.path.join(input_folder, '*.wav')):
        out_path = os.path.join(output_folder, os.path.basename(wav_path).replace('.wav', '_clean.wav'))
        remove_noise(wav_path, out_path)

## 5. Example Utility Script Standard
import librosa

def load_audio(filename):
    """
    Load an audio file and return samples and sample rate.
    Args:
        filename (str): Path to file
    Returns:
        y (np.ndarray): Audio samples
        sr (int): Sample rate
    """ 
    y, sr = librosa.load(filename, sr=None)
    return y, sr

---

Please adhere to these standards for all new and modified scripts.