import csv
import os
from datetime import datetime
from statistics import median

import state
from config import VALID_RANGES, TEMP_MIN, TEMP_MAX


def init_csv():
    """Create a timestamped CSV log file."""
    os.makedirs("logs", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    state.csv_path = os.path.join("logs", f"log_{stamp}.csv")
    state.csv_file = open(state.csv_path, "w", newline="")
    state.csv_writer = csv.writer(state.csv_file)
    state.csv_writer.writerow(["timestamp", "temp", "hum", "dist", "fan"])


def is_valid(data):
    """Reject readings with values outside realistic sensor ranges."""
    for key, (lo, hi) in VALID_RANGES.items():
        val = data.get(key)
        if val is not None and not (lo <= val <= hi):
            return False
    return True


def _compute_pwm(temp):
    """Pure linear mapping from a single temperature value to PWM."""
    FAN_PWM_MIN = 100
    FAN_PWM_MAX = 255
    if temp <= TEMP_MIN:
        return 0
    if temp >= TEMP_MAX:
        return FAN_PWM_MAX
    ratio = (temp - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)
    return int(round(FAN_PWM_MIN + ratio * (FAN_PWM_MAX - FAN_PWM_MIN)))


def temp_to_fan_speed(temp):
    """
    Compute fan PWM using a **median filter** over recent readings.

    The raw temp is appended to a small rolling buffer (default 5 readings).
    The median of that buffer is used to compute the actual fan speed.
    This means:
      - A single corrupt value (e.g. 25→5 due to serial glitch) cannot
        move the median, so the fan stays stable.
      - When temp is None, it is simply skipped (buffer unchanged).
      - The fan only changes speed when the temperature genuinely and
        consistently shifts over several readings.
    """
    # Skip None — don't let missing data pollute the buffer
    if temp is not None:
        state.temp_buffer.append(temp)

    # Not enough data yet — hold whatever we had before
    if len(state.temp_buffer) == 0:
        return state.last_fan_speed

    # Use the median of the buffer to decide the fan speed
    stable_temp = median(state.temp_buffer)
    speed = _compute_pwm(stable_temp)

    state.last_fan_speed = speed
    return speed
