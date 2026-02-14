"""
Mastering Engine Module
========================

Professional-grade mastering chain for music production.
Applies EQ, compression, stereo enhancement, limiting,
and loudness normalization.

Audio processing provided by free and open-source libraries.
"""

import os
import numpy as np
import soundfile as sf
from typing import Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class MasteringConfig:
    """Configuration for the mastering chain."""
    # EQ
    eq_enabled: bool = True
    eq_low_shelf_freq: float = 80.0
    eq_low_shelf_gain_db: float = 1.5
    eq_high_shelf_freq: float = 12000.0
    eq_high_shelf_gain_db: float = 2.0
    eq_mid_freq: float = 3000.0
    eq_mid_gain_db: float = -1.0
    eq_mid_q: float = 1.0

    # Compression
    compressor_enabled: bool = True
    compressor_threshold_db: float = -18.0
    compressor_ratio: float = 3.0
    compressor_attack_ms: float = 10.0
    compressor_release_ms: float = 100.0
    compressor_makeup_gain_db: float = 2.0

    # Stereo enhancement
    stereo_enhance: bool = True
    stereo_width: float = 1.2  # 1.0 = no change, >1.0 = wider

    # Limiter
    limiter_enabled: bool = True
    limiter_threshold_db: float = -1.0
    limiter_release_ms: float = 50.0

    # Loudness
    target_lufs: float = -14.0  # Spotify standard
    target_sample_rate: int = 96000
    output_format: str = "wav"
    output_bit_depth: int = 24

    # Preset
    preset: str = "default"  # default, warm, bright, punchy, gentle


@dataclass
class MasteringReport:
    """Report of mastering operations performed."""
    input_file: str = ""
    output_file: str = ""
    preset: str = ""
    operations: list = field(default_factory=list)
    input_lufs: float = 0.0
    output_lufs: float = 0.0
    peak_db: float = 0.0
    success: bool = False
    error: Optional[str] = None


# Preset configurations
PRESETS = {
    "default": {},
    "warm": {
        "eq_low_shelf_gain_db": 2.5,
        "eq_high_shelf_gain_db": -0.5,
        "eq_mid_freq": 2500.0,
        "eq_mid_gain_db": -1.5,
        "compressor_threshold_db": -16.0,
        "compressor_ratio": 2.5,
    },
    "bright": {
        "eq_low_shelf_gain_db": 0.5,
        "eq_high_shelf_gain_db": 3.5,
        "eq_mid_freq": 4000.0,
        "eq_mid_gain_db": 1.0,
        "compressor_threshold_db": -20.0,
        "compressor_ratio": 3.5,
    },
    "punchy": {
        "eq_low_shelf_gain_db": 3.0,
        "eq_high_shelf_gain_db": 1.0,
        "eq_mid_freq": 2000.0,
        "eq_mid_gain_db": 0.5,
        "compressor_threshold_db": -14.0,
        "compressor_ratio": 4.0,
        "compressor_attack_ms": 5.0,
        "compressor_release_ms": 80.0,
    },
    "gentle": {
        "eq_low_shelf_gain_db": 1.0,
        "eq_high_shelf_gain_db": 1.0,
        "eq_mid_gain_db": 0.0,
        "compressor_threshold_db": -22.0,
        "compressor_ratio": 2.0,
        "compressor_attack_ms": 20.0,
        "compressor_release_ms": 150.0,
        "stereo_width": 1.1,
    },
    "kpop": {
        "eq_low_shelf_gain_db": 2.0,
        "eq_high_shelf_gain_db": 3.0,
        "eq_mid_freq": 3500.0,
        "eq_mid_gain_db": 1.5,
        "compressor_threshold_db": -15.0,
        "compressor_ratio": 3.5,
        "stereo_width": 1.3,
    },
    "cinematic": {
        "eq_low_shelf_gain_db": 3.0,
        "eq_high_shelf_gain_db": 2.0,
        "eq_mid_freq": 1000.0,
        "eq_mid_gain_db": -0.5,
        "compressor_threshold_db": -20.0,
        "compressor_ratio": 2.5,
        "stereo_width": 1.4,
    },
    "indie_folk": {
        "eq_low_shelf_gain_db": 1.5,
        "eq_high_shelf_gain_db": 1.5,
        "eq_mid_freq": 2500.0,
        "eq_mid_gain_db": 0.5,
        "compressor_threshold_db": -20.0,
        "compressor_ratio": 2.0,
        "stereo_width": 1.15,
    },
}


def apply_preset(config: MasteringConfig, preset: str) -> MasteringConfig:
    """Apply a preset to the mastering config."""
    if preset in PRESETS:
        for key, value in PRESETS[preset].items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.preset = preset
    return config


def eq_shelf(
    audio: np.ndarray,
    sr: int,
    freq: float,
    gain_db: float,
    shelf_type: str = "low"
) -> np.ndarray:
    """Apply a shelving EQ filter."""
    from scipy.signal import butter, sosfilt

    if abs(gain_db) < 0.1:
        return audio

    gain_linear = 10 ** (gain_db / 20.0)
    nyquist = sr / 2
    normalized_freq = min(freq / nyquist, 0.99)

    if shelf_type == "low":
        sos = butter(2, normalized_freq, btype='low', output='sos')
    else:
        sos = butter(2, normalized_freq, btype='high', output='sos')

    # Extract the shelf band
    if audio.ndim == 2:
        filtered = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            band = sosfilt(sos, audio[:, ch])
            filtered[:, ch] = audio[:, ch] + band * (gain_linear - 1)
    else:
        band = sosfilt(sos, audio)
        filtered = audio + band * (gain_linear - 1)

    return filtered


def eq_parametric(
    audio: np.ndarray,
    sr: int,
    freq: float,
    gain_db: float,
    q: float = 1.0
) -> np.ndarray:
    """Apply a parametric EQ band."""
    from scipy.signal import iirpeak, sosfilt, tf2sos

    if abs(gain_db) < 0.1:
        return audio

    nyquist = sr / 2
    w0 = freq / nyquist
    if w0 >= 1.0:
        return audio

    gain_linear = 10 ** (gain_db / 20.0)

    b, a = iirpeak(w0, q)
    sos = tf2sos(b, a)

    if audio.ndim == 2:
        result = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            band = sosfilt(sos, audio[:, ch])
            result[:, ch] = audio[:, ch] + (band - audio[:, ch]) * (gain_linear - 1)
    else:
        band = sosfilt(sos, audio)
        result = audio + (band - audio) * (gain_linear - 1)

    return result


def compress(
    audio: np.ndarray,
    sr: int,
    threshold_db: float = -18.0,
    ratio: float = 3.0,
    attack_ms: float = 10.0,
    release_ms: float = 100.0,
    makeup_gain_db: float = 2.0
) -> np.ndarray:
    """Apply dynamic range compression."""
    threshold_linear = 10 ** (threshold_db / 20.0)
    attack_samples = int(sr * attack_ms / 1000.0)
    release_samples = int(sr * release_ms / 1000.0)
    makeup_linear = 10 ** (makeup_gain_db / 20.0)

    def process_channel(signal: np.ndarray) -> np.ndarray:
        envelope = np.abs(signal)

        # Smooth envelope with attack/release
        smoothed = np.zeros_like(envelope)
        smoothed[0] = envelope[0]
        for i in range(1, len(envelope)):
            if envelope[i] > smoothed[i - 1]:
                coeff = 1 - np.exp(-1.0 / max(attack_samples, 1))
            else:
                coeff = 1 - np.exp(-1.0 / max(release_samples, 1))
            smoothed[i] = smoothed[i - 1] + coeff * (envelope[i] - smoothed[i - 1])

        # Calculate gain reduction
        gain = np.ones_like(smoothed)
        mask = smoothed > threshold_linear
        if np.any(mask):
            gain[mask] = (threshold_linear / smoothed[mask]) ** (1 - 1 / ratio)

        return signal * gain * makeup_linear

    if audio.ndim == 2:
        result = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            result[:, ch] = process_channel(audio[:, ch])
        return result
    else:
        return process_channel(audio)


def enhance_stereo(audio: np.ndarray, width: float = 1.2) -> np.ndarray:
    """Enhance stereo width using mid-side processing."""
    if audio.ndim != 2 or audio.shape[1] != 2:
        return audio

    # Convert to mid-side
    mid = (audio[:, 0] + audio[:, 1]) / 2.0
    side = (audio[:, 0] - audio[:, 1]) / 2.0

    # Adjust width
    side = side * width

    # Convert back to left-right
    result = np.zeros_like(audio)
    result[:, 0] = mid + side
    result[:, 1] = mid - side

    return result


def limit(
    audio: np.ndarray,
    sr: int,
    threshold_db: float = -1.0,
    release_ms: float = 50.0
) -> np.ndarray:
    """Apply a brickwall limiter."""
    threshold_linear = 10 ** (threshold_db / 20.0)
    release_samples = int(sr * release_ms / 1000.0)

    def process_channel(signal: np.ndarray) -> np.ndarray:
        result = signal.copy()
        gain = 1.0

        for i in range(len(result)):
            level = abs(result[i])
            if level > threshold_linear:
                target_gain = threshold_linear / level
                gain = min(gain, target_gain)
            else:
                # Release
                gain = min(1.0, gain + (1.0 - gain) / max(release_samples, 1))

            result[i] *= gain

        return result

    if audio.ndim == 2:
        result = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            result[:, ch] = process_channel(audio[:, ch])
        return result
    else:
        return process_channel(audio)


def measure_lufs(audio: np.ndarray, sr: int) -> float:
    """Measure integrated loudness in LUFS."""
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        return meter.integrated_loudness(audio)
    except ImportError:
        # Fallback: estimate from RMS
        rms = np.sqrt(np.mean(audio ** 2))
        if rms > 0:
            return 20 * np.log10(rms) - 0.691
        return -70.0


def run_mastering_pipeline(
    input_path: str,
    output_path: Optional[str] = None,
    config: Optional[MasteringConfig] = None,
) -> MasteringReport:
    """
    Run the full mastering chain on an audio file.

    Pipeline order:
    1. Load audio
    2. Apply EQ (low shelf, mid parametric, high shelf)
    3. Apply compression
    4. Enhance stereo width
    5. Apply limiter
    6. Normalize loudness to target LUFS
    7. Resample to target rate
    8. Save output

    Returns a MasteringReport.
    """
    if config is None:
        config = MasteringConfig()

    # Apply preset if specified
    if config.preset != "default":
        config = apply_preset(config, config.preset)

    report = MasteringReport(input_file=input_path, preset=config.preset)

    try:
        # 1. Load
        from engine.cleanup import load_audio, save_audio, resample_audio
        audio, sr = load_audio(input_path)
        report.input_lufs = measure_lufs(audio, sr)
        report.operations.append(f"Loaded: {sr}Hz, input LUFS: {report.input_lufs:.1f}")

        # 2. EQ
        if config.eq_enabled:
            audio = eq_shelf(audio, sr, config.eq_low_shelf_freq, config.eq_low_shelf_gain_db, "low")
            audio = eq_parametric(audio, sr, config.eq_mid_freq, config.eq_mid_gain_db, config.eq_mid_q)
            audio = eq_shelf(audio, sr, config.eq_high_shelf_freq, config.eq_high_shelf_gain_db, "high")
            report.operations.append(
                f"EQ: low={config.eq_low_shelf_gain_db:+.1f}dB@{config.eq_low_shelf_freq}Hz, "
                f"mid={config.eq_mid_gain_db:+.1f}dB@{config.eq_mid_freq}Hz, "
                f"high={config.eq_high_shelf_gain_db:+.1f}dB@{config.eq_high_shelf_freq}Hz"
            )

        # 3. Compression
        if config.compressor_enabled:
            audio = compress(
                audio, sr,
                threshold_db=config.compressor_threshold_db,
                ratio=config.compressor_ratio,
                attack_ms=config.compressor_attack_ms,
                release_ms=config.compressor_release_ms,
                makeup_gain_db=config.compressor_makeup_gain_db,
            )
            report.operations.append(
                f"Compression: {config.compressor_ratio}:1 @ {config.compressor_threshold_db}dB"
            )

        # 4. Stereo enhancement
        if config.stereo_enhance and audio.ndim == 2:
            audio = enhance_stereo(audio, config.stereo_width)
            report.operations.append(f"Stereo width: {config.stereo_width:.1f}")

        # 5. Limiter
        if config.limiter_enabled:
            audio = limit(audio, sr, config.limiter_threshold_db, config.limiter_release_ms)
            report.operations.append(f"Limiter: {config.limiter_threshold_db}dB ceiling")

        # 6. Loudness normalization
        try:
            import pyloudnorm as pyln
            meter = pyln.Meter(sr)
            current_lufs = meter.integrated_loudness(audio if audio.ndim == 2 else audio.reshape(-1, 1))
            if not np.isinf(current_lufs) and not np.isnan(current_lufs):
                audio = pyln.normalize.loudness(
                    audio if audio.ndim == 2 else audio.reshape(-1, 1),
                    current_lufs,
                    config.target_lufs
                )
        except ImportError:
            # Fallback normalization
            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio * (0.9 / peak)
        report.operations.append(f"Loudness target: {config.target_lufs} LUFS")

        # 7. Resample
        if sr != config.target_sample_rate:
            audio = resample_audio(audio, sr, config.target_sample_rate)
            sr = config.target_sample_rate
            report.operations.append(f"Resampled to {sr}Hz")

        # Measure output
        report.output_lufs = measure_lufs(audio, sr)
        report.peak_db = 20 * np.log10(max(np.max(np.abs(audio)), 1e-10))

        # 8. Save
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_mastered.{config.output_format}"

        output_path = save_audio(
            output_path, audio, sr,
            bit_depth=config.output_bit_depth,
            output_format=config.output_format
        )
        report.output_file = output_path
        report.success = True
        report.operations.append(f"Output: {report.output_lufs:.1f} LUFS, peak {report.peak_db:.1f}dB")

    except Exception as e:
        report.success = False
        report.error = str(e)

    return report
