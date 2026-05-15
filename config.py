"""
Application configuration and constants.
"""

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

SENSORS = ["temp", "hum", "dist", "fan"]
