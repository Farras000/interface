from flask import Flask, render_template, send_file
from flask_socketio import SocketIO
import serial
import json
import threading
import time
import csv
import os
from collections import deque
from datetime import datetime
import numpy as np
from scipy.signal import butter, sosfilt

app = Flask(__name__)
app.config["SECRET_KEY"] = "smartfan"
socketio = SocketIO(app, cors_allowed_origins="*")

SERIAL_PORT = "COM5"
BAUD_RATE = 115200
FILTER_WINDOW = 5     # Moving average window size
STATS_WINDOW = 60     # Statistics computed over last N readings
FFT_WINDOW = 64       # Samples used for FFT computation

# ── Linear Fan Speed Config ───────────────────────────
# Fan PWM is linearly mapped from temperature:
#   temp <= TEMP_MIN  → fan = 0   (off)
#   temp >= TEMP_MAX  → fan = 255 (full speed)
#   in between        → linear interpolation
TEMP_MIN = 22   # °C – below this the fan stays off
TEMP_MAX = 30   # °C – at or above this the fan runs at full speed

# Realistic sensor ranges for validation
VALID_RANGES = {
    "temp": (-10, 60),
    "hum":  (0, 100),
    "dist": (-1, 100),
    "fan":  (0, 255),
}

# ── State ──────────────────────────────────────────────
SENSORS = ["temp", "hum", "dist", "fan"]
history = {key: deque(maxlen=max(STATS_WINDOW, FFT_WINDOW * 2)) for key in SENSORS}
paused = False
csv_path = None
csv_file = None
csv_writer = None

# ── Filter Config (adjustable from frontend) ──────────
filter_config = {
    "type": "none",       # "none", "lowpass", "highpass", "bandpass"
    "cutoff": 0.1,        # Normalized cutoff (0–0.5, fraction of Nyquist)
    "cutoff_high": 0.4,   # Upper cutoff for bandpass
    "order": 2,           # Filter order
}


def init_csv():
    """Create a timestamped CSV log file."""
    global csv_path, csv_file, csv_writer
    os.makedirs("logs", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("logs", f"log_{stamp}.csv")
    csv_file = open(csv_path, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["timestamp", "temp", "hum", "dist", "fan"])


def is_valid(data):
    """Reject readings with values outside realistic sensor ranges."""
    for key, (lo, hi) in VALID_RANGES.items():
        val = data.get(key)
        if val is not None and not (lo <= val <= hi):
            return False
    return True


def temp_to_fan_speed(temp):
    """
    Linearly map temperature to PWM fan speed (100–255).

    Returns 0 when temp <= TEMP_MIN, 255 when temp >= TEMP_MAX,
    and a value linearly interpolated between 100 and 255 in between.
    """
    FAN_PWM_MIN = 100
    FAN_PWM_MAX = 255
    if temp is None:
        return 0
    if temp <= TEMP_MIN:
        return 0
    if temp >= TEMP_MAX:
        return FAN_PWM_MAX
    
    ratio = (temp - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)
    return int(round(FAN_PWM_MIN + ratio * (FAN_PWM_MAX - FAN_PWM_MIN)))


def moving_average(sensor_key):
    """Compute moving average of last FILTER_WINDOW values for a sensor."""
    buf = list(history[sensor_key])[-FILTER_WINDOW:]
    valid = [v for v in buf if v is not None]
    if not valid:
        return None
    return round(float(np.mean(valid)), 2)


def compute_stats(sensor_key):
    """Compute statistics over the history window for a sensor."""
    valid = [v for v in history[sensor_key] if v is not None]
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
    raw = [v for v in history[sensor_key] if v is not None]
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
    if filter_config["type"] == "none":
        return None

    raw = [v for v in history[sensor_key] if v is not None]
    if len(raw) < 12:  # Need minimum samples for filter
        return None

    samples = np.array(raw, dtype=float)
    fs = 1.0  # Sampling rate ~1 Hz
    nyquist = fs / 2.0

    try:
        ftype = filter_config["type"]
        order = filter_config["order"]

        if ftype == "lowpass":
            wn = min(filter_config["cutoff"], 0.99)
            sos = butter(order, wn, btype='low', fs=fs, output='sos')
        elif ftype == "highpass":
            wn = max(filter_config["cutoff"], 0.01)
            sos = butter(order, wn, btype='high', fs=fs, output='sos')
        elif ftype == "bandpass":
            low = max(filter_config["cutoff"], 0.01)
            high = min(filter_config["cutoff_high"], 0.99)
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
    raw = [v for v in history[sensor_key] if v is not None]
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
    raw_a = [v for v in history[key_a] if v is not None]
    raw_b = [v for v in history[key_b] if v is not None]
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


def serial_reader():
    """Background thread: reads serial JSON, computes fan speed, sends it
    back to the Arduino, and pushes data to the frontend via WebSocket."""
    global paused
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"[Serial] Connected to {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"[Serial] Could not open {SERIAL_PORT}: {e}")
        return

    while True:
        try:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue
            data = json.loads(raw)
            if not is_valid(data):
                print(f"[Serial] Dropped bad reading: {raw}")
                continue

            # ── Compute and send fan speed back to Arduino ──
            temp = data.get("temp")
            fan_speed = temp_to_fan_speed(temp)
            ser.write(f"{fan_speed}\n".encode())
            print(f"[Fan] temp={temp}°C → PWM={fan_speed}")

            # Override the fan value in data so downstream sees what we sent
            data["fan"] = fan_speed

            # Store raw values in history
            for key in SENSORS:
                history[key].append(data.get(key))

            # Always log to CSV (even when paused)
            now = datetime.now().isoformat()
            if csv_writer:
                csv_writer.writerow([
                    now,
                    data.get("temp"),
                    data.get("hum"),
                    data.get("dist"),
                    data.get("fan"),
                ])
                csv_file.flush()

            # Skip emitting to frontend if paused
            if paused:
                continue

            # ── Build signal processing payload ──
            signal_payload = {}
            for key in SENSORS:
                signal_payload[key] = {
                    "fft": compute_fft(key),
                    "filtered": apply_digital_filter(key),
                    "derivative": compute_derivative(key),
                }

            # Correlations
            correlations = {
                "temp_fan": compute_correlation("temp", "fan"),
                "temp_hum": compute_correlation("temp", "hum"),
                "temp_dist": compute_correlation("temp", "dist"),
            }

            # Build main payload with raw, filtered, stats, and signal processing
            payload = {
                "raw": {k: data.get(k) for k in SENSORS},
                "filtered": {k: moving_average(k) for k in SENSORS},
                "stats": {k: compute_stats(k) for k in SENSORS},
                "signal": signal_payload,
                "correlations": correlations,
                "filter_config": filter_config,
                "timestamp": now,
                "buffer_size": len([v for v in history["temp"] if v is not None]),
            }
            socketio.emit("serial_data", payload)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[Serial] Error: {e}")
            time.sleep(1)


# ── Socket.IO Events ──────────────────────────────────
@socketio.on("toggle_pause")
def handle_pause():
    global paused
    paused = not paused
    socketio.emit("pause_state", {"paused": paused})
    print(f"[Control] {'Paused' if paused else 'Resumed'}")


@socketio.on("set_filter")
def handle_set_filter(config):
    """Receive filter configuration from the frontend."""
    global filter_config
    if "type" in config:
        filter_config["type"] = config["type"]
    if "cutoff" in config:
        filter_config["cutoff"] = max(0.01, min(0.49, float(config["cutoff"])))
    if "cutoff_high" in config:
        filter_config["cutoff_high"] = max(0.01, min(0.49, float(config["cutoff_high"])))
    if "order" in config:
        filter_config["order"] = max(1, min(6, int(config["order"])))
    print(f"[Filter] Config updated: {filter_config}")
    socketio.emit("filter_updated", filter_config)


# ── HTTP Routes ───────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download")
def download():
    if csv_path and os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True)
    return "No log file yet", 404


if __name__ == "__main__":
    init_csv()
    print(f"[CSV] Logging to {csv_path}")
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()
    socketio.run(app, host="0.0.0.0", port=8000, debug=False)