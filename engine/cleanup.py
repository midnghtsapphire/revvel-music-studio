"""
Audio Cleanup & Restoration Module
===================================

Provides automated audio restoration including:
- Noise reduction (spectral gating)
- Pop/click removal (transient detection + interpolation)
- De-essing (sibilance reduction)
- Pitch correction (auto-tune)
- Feedback/hum removal

All processing targets lossless stereo output.
Audio processing provided by free and open-source libraries.
"""

import os
import numpy as np
import soundfile as sf
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CleanupConfig:
    """Configuration for the audio cleanup pipeline."""
    # Noise reduction
    noise_reduce: bool = True
    noise_reduce_strength: float = 0.75  # 0.0 to 1.0
    noise_reduce_stationary: bool = True

    # Pop/click removal
    remove_pops: bool = True
    pop_threshold: float = 3.5  # Standard deviations above mean
    pop_window_ms: float = 5.0  # Interpolation window in ms

    # De-essing
    deess: bool = True
    deess_frequency: float = 6000.0  # Center frequency for sibilance
    deess_threshold: float = -20.0  # dB threshold
    deess_ratio: float = 4.0

    # Feedback/hum removal
    remove_hum: bool = True
    hum_frequency: float = 60.0  # 60Hz (US) or 50Hz (EU)
    hum_harmonics: int = 5

    # Pitch correction
    pitch_correct: bool = False
    pitch_correction_strength: float = 0.8  # 0.0 (none) to 1.0 (full snap)
    pitch_scale: str = "chromatic"  # chromatic, major, minor, etc.
    pitch_key: str = "C"  # Key for scale-based correction

    # Output
    target_sample_rate: int = 96000  # ~97kHz target (96kHz is standard)
    output_format: str = "wav"  # wav, flac
    output_bit_depth: int = 24  # 16, 24, 32


@dataclass
class CleanupReport:
    """Report of cleanup operations performed."""
    input_file: str = ""
    output_file: str = ""
    sample_rate: int = 0
    channels: int = 0
    duration_seconds: float = 0.0
    operations: list = field(default_factory=list)
    pops_detected: int = 0
    pitch_corrections: int = 0
    noise_reduction_applied: bool = False
    hum_removed: bool = False
    deessing_applied: bool = False
    success: bool = False
    error: Optional[str] = None


def load_audio(filepath: str) -> Tuple[np.ndarray, int]:
    """Load an audio file and return (samples, sample_rate)."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    audio, sr = sf.read(filepath, dtype='float64')

    # Ensure stereo
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])

    return audio, sr


def save_audio(
    filepath: str,
    audio: np.ndarray,
    sample_rate: int,
    bit_depth: int = 24,
    output_format: str = "wav"
) -> str:
    """Save audio to file in the specified format."""
    subtype_map = {
        16: "PCM_16",
        24: "PCM_24",
        32: "FLOAT",
    }
    subtype = subtype_map.get(bit_depth, "PCM_24")

    if output_format == "flac":
        subtype = subtype if bit_depth <= 24 else "PCM_24"

    # Ensure proper extension
    if not filepath.endswith(f".{output_format}"):
        filepath = os.path.splitext(filepath)[0] + f".{output_format}"

    sf.write(filepath, audio, sample_rate, subtype=subtype)
    return filepath


def reduce_noise(
    audio: np.ndarray,
    sr: int,
    strength: float = 0.75,
    stationary: bool = True
) -> np.ndarray:
    """
    Apply spectral noise reduction.
    Uses noisereduce library for spectral gating.
    """
    try:
        import noisereduce as nr
    except ImportError:
        raise ImportError("noisereduce is required: pip install noisereduce")

    # Process each channel separately for stereo
    if audio.ndim == 2:
        cleaned = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            cleaned[:, ch] = nr.reduce_noise(
                y=audio[:, ch],
                sr=sr,
                stationary=stationary,
                prop_decrease=strength,
                n_fft=2048,
                hop_length=512,
            )
        return cleaned
    else:
        return nr.reduce_noise(
            y=audio,
            sr=sr,
            stationary=stationary,
            prop_decrease=strength,
        )


def remove_pops_clicks(
    audio: np.ndarray,
    sr: int,
    threshold: float = 3.5,
    window_ms: float = 5.0
) -> Tuple[np.ndarray, int]:
    """
    Detect and remove pops/clicks using transient detection
    and cubic interpolation.
    """
    from scipy.interpolate import CubicSpline

    window_samples = int(sr * window_ms / 1000.0)
    cleaned = audio.copy()
    total_pops = 0

    def process_channel(signal: np.ndarray) -> Tuple[np.ndarray, int]:
        pops = 0
        # Compute the first derivative (rate of change)
        diff = np.diff(signal)
        # Compute statistics
        mean_diff = np.mean(np.abs(diff))
        std_diff = np.std(np.abs(diff))
        threshold_val = mean_diff + threshold * std_diff

        # Find pop locations
        pop_indices = np.where(np.abs(diff) > threshold_val)[0]

        if len(pop_indices) == 0:
            return signal, 0

        # Group consecutive indices into pop regions
        groups = []
        current_group = [pop_indices[0]]
        for i in range(1, len(pop_indices)):
            if pop_indices[i] - pop_indices[i - 1] <= window_samples:
                current_group.append(pop_indices[i])
            else:
                groups.append(current_group)
                current_group = [pop_indices[i]]
        groups.append(current_group)

        result = signal.copy()
        for group in groups:
            start = max(0, group[0] - window_samples)
            end = min(len(signal) - 1, group[-1] + window_samples)

            # Create interpolation points (excluding the pop region)
            x_good = np.concatenate([
                np.arange(start, group[0]),
                np.arange(group[-1] + 1, end + 1)
            ])
            if len(x_good) < 4:
                continue

            y_good = signal[x_good]
            x_bad = np.arange(group[0], group[-1] + 1)

            try:
                cs = CubicSpline(x_good, y_good)
                result[x_bad] = cs(x_bad)
                pops += 1
            except Exception:
                continue

        return result, pops

    if audio.ndim == 2:
        for ch in range(audio.shape[1]):
            cleaned[:, ch], ch_pops = process_channel(audio[:, ch])
            total_pops += ch_pops
    else:
        cleaned, total_pops = process_channel(audio)

    return cleaned, total_pops


def remove_hum(
    audio: np.ndarray,
    sr: int,
    fundamental: float = 60.0,
    harmonics: int = 5,
    q_factor: float = 30.0
) -> np.ndarray:
    """
    Remove electrical hum (e.g., 60Hz or 50Hz) and its harmonics
    using notch filters.
    """
    from scipy.signal import iirnotch, sosfilt

    cleaned = audio.copy()

    for h in range(1, harmonics + 1):
        freq = fundamental * h
        if freq >= sr / 2:
            break

        w0 = freq / (sr / 2)
        if w0 >= 1.0:
            break

        b, a = iirnotch(w0, q_factor)
        # Convert to second-order sections for stability
        from scipy.signal import tf2sos
        sos = tf2sos(b, a)

        if audio.ndim == 2:
            for ch in range(audio.shape[1]):
                cleaned[:, ch] = sosfilt(sos, cleaned[:, ch])
        else:
            cleaned = sosfilt(sos, cleaned)

    return cleaned


def deess(
    audio: np.ndarray,
    sr: int,
    center_freq: float = 6000.0,
    threshold_db: float = -20.0,
    ratio: float = 4.0,
    bandwidth: float = 4000.0
) -> np.ndarray:
    """
    Reduce sibilance (harsh 's' and 'sh' sounds) using
    frequency-targeted dynamic compression.
    """
    from scipy.signal import butter, sosfilt

    cleaned = audio.copy()

    # Design bandpass filter for sibilance range
    low = max(100, center_freq - bandwidth / 2) / (sr / 2)
    high = min(0.99, (center_freq + bandwidth / 2) / (sr / 2))

    if low >= high:
        return cleaned

    sos_bp = butter(4, [low, high], btype='bandpass', output='sos')

    threshold_linear = 10 ** (threshold_db / 20.0)

    def process_channel(signal: np.ndarray) -> np.ndarray:
        # Extract sibilance band
        sibilance = sosfilt(sos_bp, signal)

        # Compute envelope
        envelope = np.abs(sibilance)
        # Smooth envelope
        window_size = int(sr * 0.01)  # 10ms window
        if window_size > 0:
            kernel = np.ones(window_size) / window_size
            envelope = np.convolve(envelope, kernel, mode='same')

        # Apply compression where envelope exceeds threshold
        gain = np.ones_like(envelope)
        mask = envelope > threshold_linear
        if np.any(mask):
            gain[mask] = (threshold_linear / envelope[mask]) ** (1 - 1 / ratio)

        # Apply gain to sibilance band only
        reduced_sibilance = sibilance * gain
        result = signal - sibilance + reduced_sibilance
        return result

    if audio.ndim == 2:
        for ch in range(audio.shape[1]):
            cleaned[:, ch] = process_channel(audio[:, ch])
    else:
        cleaned = process_channel(audio)

    return cleaned


def pitch_correct(
    audio: np.ndarray,
    sr: int,
    strength: float = 0.8,
    scale: str = "chromatic",
    key: str = "C"
) -> Tuple[np.ndarray, int]:
    """
    Auto-tune / pitch correction using PYIN pitch detection
    and phase vocoder pitch shifting.
    """
    try:
        import librosa
    except ImportError:
        raise ImportError("librosa is required: pip install librosa")

    corrections = 0

    # Note frequencies for chromatic scale (A4 = 440Hz)
    def freq_to_midi(freq):
        if freq <= 0:
            return 0
        return 69 + 12 * np.log2(freq / 440.0)

    def midi_to_freq(midi):
        return 440.0 * 2 ** ((midi - 69) / 12.0)

    # Scale definitions (semitone intervals from root)
    scales = {
        "chromatic": list(range(12)),
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "pentatonic_major": [0, 2, 4, 7, 9],
        "pentatonic_minor": [0, 3, 5, 7, 10],
        "blues": [0, 3, 5, 6, 7, 10],
    }

    key_offsets = {
        "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
        "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
    }

    scale_intervals = scales.get(scale, scales["chromatic"])
    key_offset = key_offsets.get(key, 0)

    def snap_to_scale(midi_note):
        """Snap a MIDI note to the nearest note in the scale."""
        if scale == "chromatic":
            return round(midi_note)

        note_class = round(midi_note) % 12
        octave = round(midi_note) // 12

        # Find nearest scale degree
        adjusted = (note_class - key_offset) % 12
        best = min(scale_intervals, key=lambda x: min(abs(adjusted - x), 12 - abs(adjusted - x)))
        target = (best + key_offset) % 12 + octave * 12

        # Check if wrapping to next/prev octave is closer
        candidates = [target - 12, target, target + 12]
        return min(candidates, key=lambda x: abs(x - midi_note))

    def process_channel(signal: np.ndarray) -> Tuple[np.ndarray, int]:
        ch_corrections = 0

        # Detect pitch using PYIN
        f0, voiced_flag, voiced_probs = librosa.pyin(
            signal,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr,
            frame_length=2048,
            hop_length=512,
        )

        if f0 is None or len(f0) == 0:
            return signal, 0

        # Calculate correction for each frame
        corrected_f0 = np.copy(f0)
        for i in range(len(f0)):
            if np.isnan(f0[i]) or not voiced_flag[i]:
                continue

            midi = freq_to_midi(f0[i])
            target_midi = snap_to_scale(midi)
            deviation = target_midi - midi

            if abs(deviation) > 0.1:  # More than 10 cents off
                corrected_midi = midi + deviation * strength
                corrected_f0[i] = midi_to_freq(corrected_midi)
                ch_corrections += 1

        # Apply pitch correction using STFT-based approach
        stft = librosa.stft(signal, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft)
        phase = np.angle(stft)

        # Reconstruct with corrected pitch (simplified approach)
        # For each frame, apply frequency scaling
        corrected_stft = stft.copy()
        freq_bins = librosa.fft_frequencies(sr=sr, n_fft=2048)

        for i in range(min(len(f0), stft.shape[1])):
            if np.isnan(f0[i]) or not voiced_flag[i] or np.isnan(corrected_f0[i]):
                continue

            ratio = corrected_f0[i] / f0[i]
            if abs(ratio - 1.0) < 0.001:
                continue

            # Simple spectral shifting
            n_bins = magnitude.shape[0]
            new_mag = np.zeros(n_bins)
            new_phase = np.zeros(n_bins)

            for b in range(n_bins):
                new_bin = int(b * ratio)
                if 0 <= new_bin < n_bins:
                    new_mag[new_bin] += magnitude[b, i]
                    new_phase[new_bin] = phase[b, i]

            # Blend original and corrected based on strength
            corrected_stft[:, i] = (
                (1 - strength) * stft[:, i] +
                strength * new_mag * np.exp(1j * new_phase)
            )

        result = librosa.istft(corrected_stft, hop_length=512, length=len(signal))
        return result, ch_corrections

    if audio.ndim == 2:
        corrected = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            corrected[:, ch], ch_corr = process_channel(audio[:, ch])
            corrections += ch_corr
        return corrected, corrections
    else:
        return process_channel(audio)


def resample_audio(audio: np.ndarray, sr_orig: int, sr_target: int) -> np.ndarray:
    """Resample audio to target sample rate."""
    if sr_orig == sr_target:
        return audio

    try:
        import librosa
    except ImportError:
        raise ImportError("librosa is required: pip install librosa")

    if audio.ndim == 2:
        resampled = np.zeros(
            (int(len(audio) * sr_target / sr_orig), audio.shape[1]),
            dtype=audio.dtype
        )
        for ch in range(audio.shape[1]):
            resampled[:, ch] = librosa.resample(
                audio[:, ch], orig_sr=sr_orig, target_sr=sr_target
            )
        return resampled
    else:
        return librosa.resample(audio, orig_sr=sr_orig, target_sr=sr_target)


def normalize_loudness(
    audio: np.ndarray,
    sr: int,
    target_lufs: float = -14.0
) -> np.ndarray:
    """Normalize audio to target LUFS (Loudness Units Full Scale)."""
    try:
        import pyloudnorm as pyln
    except ImportError:
        # Fallback to simple peak normalization
        peak = np.max(np.abs(audio))
        if peak > 0:
            return audio * (0.9 / peak)
        return audio

    meter = pyln.Meter(sr)

    if audio.ndim == 2:
        loudness = meter.integrated_loudness(audio)
    else:
        loudness = meter.integrated_loudness(audio.reshape(-1, 1))

    if np.isinf(loudness) or np.isnan(loudness):
        return audio

    gain_db = target_lufs - loudness
    gain_linear = 10 ** (gain_db / 20.0)

    normalized = audio * gain_linear

    # Prevent clipping
    peak = np.max(np.abs(normalized))
    if peak > 0.99:
        normalized = normalized * (0.99 / peak)

    return normalized


def run_cleanup_pipeline(
    input_path: str,
    output_path: Optional[str] = None,
    config: Optional[CleanupConfig] = None,
) -> CleanupReport:
    """
    Run the full audio cleanup pipeline on a file.

    Pipeline order:
    1. Load audio
    2. Remove hum/feedback
    3. Reduce noise
    4. Remove pops/clicks
    5. De-ess
    6. Pitch correct (if enabled)
    7. Normalize loudness
    8. Resample to target rate
    9. Save output

    Returns a CleanupReport with details of all operations performed.
    """
    if config is None:
        config = CleanupConfig()

    report = CleanupReport(input_file=input_path)

    try:
        # 1. Load
        audio, sr = load_audio(input_path)
        report.sample_rate = sr
        report.channels = audio.shape[1] if audio.ndim == 2 else 1
        report.duration_seconds = len(audio) / sr
        report.operations.append(f"Loaded: {sr}Hz, {report.channels}ch, {report.duration_seconds:.1f}s")

        # 2. Remove hum
        if config.remove_hum:
            audio = remove_hum(
                audio, sr,
                fundamental=config.hum_frequency,
                harmonics=config.hum_harmonics
            )
            report.hum_removed = True
            report.operations.append(f"Hum removal: {config.hum_frequency}Hz + {config.hum_harmonics} harmonics")

        # 3. Noise reduction
        if config.noise_reduce:
            audio = reduce_noise(
                audio, sr,
                strength=config.noise_reduce_strength,
                stationary=config.noise_reduce_stationary
            )
            report.noise_reduction_applied = True
            report.operations.append(f"Noise reduction: strength={config.noise_reduce_strength}")

        # 4. Pop/click removal
        if config.remove_pops:
            audio, pops = remove_pops_clicks(
                audio, sr,
                threshold=config.pop_threshold,
                window_ms=config.pop_window_ms
            )
            report.pops_detected = pops
            report.operations.append(f"Pop removal: {pops} pops detected and fixed")

        # 5. De-essing
        if config.deess:
            audio = deess(
                audio, sr,
                center_freq=config.deess_frequency,
                threshold_db=config.deess_threshold,
                ratio=config.deess_ratio
            )
            report.deessing_applied = True
            report.operations.append("De-essing applied")

        # 6. Pitch correction
        if config.pitch_correct:
            audio, corrections = pitch_correct(
                audio, sr,
                strength=config.pitch_correction_strength,
                scale=config.pitch_scale,
                key=config.pitch_key
            )
            report.pitch_corrections = corrections
            report.operations.append(f"Pitch correction: {corrections} corrections ({config.pitch_scale} {config.pitch_key})")

        # 7. Normalize loudness
        audio = normalize_loudness(audio, sr, target_lufs=-14.0)
        report.operations.append("Loudness normalization: -14 LUFS")

        # 8. Resample
        if sr != config.target_sample_rate:
            audio = resample_audio(audio, sr, config.target_sample_rate)
            sr = config.target_sample_rate
            report.operations.append(f"Resampled to {sr}Hz")

        # 9. Save
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_cleaned.{config.output_format}"

        output_path = save_audio(
            output_path, audio, sr,
            bit_depth=config.output_bit_depth,
            output_format=config.output_format
        )
        report.output_file = output_path
        report.success = True
        report.operations.append(f"Saved: {output_path}")

    except Exception as e:
        report.success = False
        report.error = str(e)

    return report
