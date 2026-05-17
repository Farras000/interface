"""
Shared application state: history buffers, CSV writer, pause flag, filter config.
"""

from collections import deque
from config import SENSORS, STATS_WINDOW, FFT_WINDOW, FAN_CONFIRM_READINGS

# ── Sensor History ─────────────────────────────────────
history = {key: deque(maxlen=max(STATS_WINDOW, FFT_WINDOW * 2)) for key in SENSORS}

# ── Fan speed hold (last known good PWM) ──────────────
last_fan_speed = 0
fan_mode = "auto"       # "auto" or "manual"
manual_fan_speed = 0    # 0 to 255

# ── Recent buffers for median filtering ───────────
temp_buffer = deque(maxlen=FAN_CONFIRM_READINGS)
dist_buffer = deque(maxlen=FAN_CONFIRM_READINGS)

# ── Pause flag ─────────────────────────────────────────
paused = False

# ── CSV state ──────────────────────────────────────────
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
