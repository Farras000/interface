"""
Signal processing functions: moving average, statistics, FFT,
digital filtering, derivative, and correlation.
"""

import numpy as np
from scipy.signal import butter, sosfilt

import state
from config import FILTER_WINDOW, STATS_WINDOW, FFT_WINDOW


def moving_average(sensor_key):
    """Compute moving average of last FILTER_WINDOW values for a sensor."""
    buf = list(state.history[sensor_key])[-FILTER_WINDOW:]
    valid = [v for v in buf if v is not None]
    if not valid:
        return None
    return round(float(np.mean(valid)), 2)


def compute_stats(sensor_key):
    """Compute statistics over the history window for a sensor."""
    valid = [v for v in state.history[sensor_key] if v is not None]
    if not valid:
        return {"mean": None, "std": None, "min": None, "max": None}
    arr = np.array(valid)
    return {
        "mean": round(float(np.mean(arr)), 2),
        "std":  round(float(np.std(arr)), 2),
        "min":  round(float(np.min(arr)), 2),
        "max":  round(float(np.max(arr)), 2),
    }


# ── Signal Processing Functions ───────────────────────

def compute_fft(sensor_key):
    """
    Compute FFT magnitude spectrum of the last FFT_WINDOW samples.
    Returns { freqs: [...], magnitudes: [...] } or None if not enough data.
    Sampling rate is ~1 Hz (Arduino sends data every ~1 second).
    """
    raw = [v for v in state.history[sensor_key] if v is not None]
    if len(raw) < FFT_WINDOW:
        return None

    samples = np.array(raw[-FFT_WINDOW:], dtype=float)
    # Remove DC offset (mean) for cleaner spectrum
    samples = samples - np.mean(samples)
    # Apply Hanning window to reduce spectral leakage
    window = np.hanning(len(samples))
    samples = samples * window

    fft_vals = np.fft.rfft(samples)
    magnitudes = np.abs(fft_vals) / len(samples) * 2  # Normalize
    freqs = np.fft.rfftfreq(len(samples), d=1.0)       # d=1s (1 Hz sampling)

    return {
        "freqs": [round(float(f), 4) for f in freqs],
        "magnitudes": [round(float(m), 4) for m in magnitudes],
    }


def apply_digital_filter(sensor_key):
    """
    Apply the configured digital filter (lowpass/highpass/bandpass)
    to the sensor history. Returns filtered values list or None.
    """
    if state.filter_config["type"] == "none":
        return None

    raw = [v for v in state.history[sensor_key] if v is not None]
    if len(raw) < 12:  # Need minimum samples for filter
        return None

    samples = np.array(raw, dtype=float)
    fs = 1.0  # Sampling rate ~1 Hz

    try:
        ftype = state.filter_config["type"]
        order = state.filter_config["order"]

        if ftype == "lowpass":
            wn = min(state.filter_config["cutoff"], 0.99)
            sos = butter(order, wn, btype='low', fs=fs, output='sos')
        elif ftype == "highpass":
            wn = max(state.filter_config["cutoff"], 0.01)
            sos = butter(order, wn, btype='high', fs=fs, output='sos')
        elif ftype == "bandpass":
            low = max(state.filter_config["cutoff"], 0.01)
            high = min(state.filter_config["cutoff_high"], 0.99)
            if low >= high:
                return None
            sos = butter(order, [low, high], btype='band', fs=fs, output='sos')
        else:
            return None

        filtered = sosfilt(sos, samples)
        # Return only the last STATS_WINDOW values for charting
        result = filtered[-STATS_WINDOW:].tolist()
        return [round(float(v), 2) for v in result]

    except Exception as e:
        print(f"[Filter] Error: {e}")
        return None


def compute_derivative(sensor_key):
    """
    Compute rate of change (Δ/sample) for the sensor.
    Returns list of derivative values or None.
    """
    raw = [v for v in state.history[sensor_key] if v is not None]
    if len(raw) < 3:
        return None

    samples = np.array(raw[-STATS_WINDOW:], dtype=float)
    deriv = np.diff(samples)  # Δ per sample (1 sample = ~1 second)
    return [round(float(d), 3) for d in deriv]


def compute_correlation(key_a, key_b):
    """
    Compute Pearson correlation coefficient and cross-correlation
    between two sensor signals.
    """
    raw_a = [v for v in state.history[key_a] if v is not None]
    raw_b = [v for v in state.history[key_b] if v is not None]
    min_len = min(len(raw_a), len(raw_b))

    if min_len < 5:
        return {"pearson": None, "scatter_x": [], "scatter_y": []}

    a = np.array(raw_a[-min_len:], dtype=float)
    b = np.array(raw_b[-min_len:], dtype=float)

    # Pearson correlation
    if np.std(a) == 0 or np.std(b) == 0:
        pearson = 0.0
    else:
        pearson = float(np.corrcoef(a, b)[0, 1])

    # Return scatter data (last N points)
    n = min(min_len, STATS_WINDOW)
    return {
        "pearson": round(pearson, 4),
        "scatter_x": [round(float(v), 2) for v in a[-n:]],
        "scatter_y": [round(float(v), 2) for v in b[-n:]],
    }
