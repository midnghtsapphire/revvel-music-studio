"""
Tests for engine.cleanup module.

Synthetic audio fixtures are generated programmatically using numpy/soundfile
so no binary test assets are required.
"""

import os
import tempfile

import numpy as np
import pytest
import soundfile as sf

from engine.cleanup import load_audio, save_audio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sine_wave(
    sample_rate: int = 44100,
    duration: float = 0.1,
    frequency: float = 440.0,
    channels: int = 1,
) -> np.ndarray:
    """Return a synthetic sine-wave array."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    if channels == 2:
        wave = np.column_stack([wave, wave])
    return wave


def _write_wav(path: str, audio: np.ndarray, sample_rate: int = 44100) -> None:
    """Write a numpy array as a WAV file."""
    sf.write(path, audio, sample_rate)


# ---------------------------------------------------------------------------
# load_audio tests
# ---------------------------------------------------------------------------

class TestLoadAudio:
    def test_raises_file_not_found_for_missing_file(self, tmp_path):
        missing = str(tmp_path / "does_not_exist.wav")
        with pytest.raises(FileNotFoundError):
            load_audio(missing)

    def test_mono_audio_is_converted_to_stereo(self, tmp_path):
        wav_path = str(tmp_path / "mono.wav")
        mono = _make_sine_wave(channels=1)
        _write_wav(wav_path, mono)

        audio, sr = load_audio(wav_path)

        assert audio.ndim == 2, "Expected 2-D (stereo) array"
        assert audio.shape[1] == 2, "Expected exactly 2 channels"

    def test_stereo_audio_remains_stereo(self, tmp_path):
        wav_path = str(tmp_path / "stereo.wav")
        stereo = _make_sine_wave(channels=2)
        _write_wav(wav_path, stereo)

        audio, sr = load_audio(wav_path)

        assert audio.ndim == 2
        assert audio.shape[1] == 2

    def test_returns_correct_sample_rate(self, tmp_path):
        wav_path = str(tmp_path / "rate.wav")
        sr_expected = 22050
        wave = _make_sine_wave(sample_rate=sr_expected, channels=1)
        sf.write(wav_path, wave, sr_expected)

        audio, sr = load_audio(wav_path)

        assert sr == sr_expected

    def test_mono_stereo_channels_are_identical(self, tmp_path):
        """When mono is upmixed, both channels should be the same."""
        wav_path = str(tmp_path / "mono_stereo.wav")
        mono = _make_sine_wave(channels=1)
        _write_wav(wav_path, mono)

        audio, _ = load_audio(wav_path)

        np.testing.assert_array_equal(audio[:, 0], audio[:, 1])


# ---------------------------------------------------------------------------
# save_audio tests
# ---------------------------------------------------------------------------

class TestSaveAudio:
    def test_writes_file_to_disk(self, tmp_path):
        out = str(tmp_path / "output.wav")
        audio = _make_sine_wave(channels=2)

        save_audio(out, audio, sample_rate=44100)

        assert os.path.exists(out)

    def test_saved_file_is_readable(self, tmp_path):
        out = str(tmp_path / "roundtrip.wav")
        audio = _make_sine_wave(channels=2)
        sr = 44100

        save_audio(out, audio, sample_rate=sr)
        loaded, loaded_sr = sf.read(out)

        assert loaded_sr == sr
        assert loaded.shape == audio.shape

    def test_audio_values_are_preserved(self, tmp_path):
        out = str(tmp_path / "values.wav")
        audio = _make_sine_wave(channels=2)

        save_audio(out, audio, sample_rate=44100, bit_depth=16)
        loaded, _ = sf.read(out)

        # PCM_16 has limited precision; allow small floating-point tolerance
        np.testing.assert_allclose(loaded, audio, atol=1e-4)

    def test_extension_is_corrected(self, tmp_path):
        """save_audio should fix the extension to match output_format."""
        out_wrong_ext = str(tmp_path / "output.mp3")
        audio = _make_sine_wave(channels=2)

        result_path = save_audio(out_wrong_ext, audio, sample_rate=44100, output_format="wav")

        assert result_path.endswith(".wav")
        assert os.path.exists(result_path)

    def test_returns_filepath(self, tmp_path):
        out = str(tmp_path / "check.wav")
        audio = _make_sine_wave(channels=2)

        result = save_audio(out, audio, sample_rate=44100)

        assert isinstance(result, str)
        assert os.path.exists(result)
