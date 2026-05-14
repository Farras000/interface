"""
Utility functions: CSV logging, data validation, fan speed mapping.
"""

import csv
import os
from datetime import datetime

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
