"""
Serial reader thread: reads JSON from the Arduino, computes fan speed,
sends it back, and pushes data to the frontend via WebSocket.
"""

import serial
import json
import time
from datetime import datetime

import state
from config import SERIAL_PORT, BAUD_RATE, SENSORS
from utils import is_valid, temp_to_fan_speed
from signal_processing import (
    moving_average,
    compute_stats,
    compute_fft,
    apply_digital_filter,
    compute_derivative,
    compute_correlation,
)


def serial_reader(socketio):
    """Background thread: reads serial JSON, computes fan speed, sends it
    back to the Arduino, and pushes data to the frontend via WebSocket."""
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
                state.history[key].append(data.get(key))

            # Always log to CSV (even when paused)
            now = datetime.now().isoformat()
            if state.csv_writer:
                state.csv_writer.writerow([
                    now,
                    data.get("temp"),
                    data.get("hum"),
                    data.get("dist"),
                    data.get("fan"),
                ])
                state.csv_file.flush()

            # Skip emitting to frontend if paused
            if state.paused:
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
                "filter_config": state.filter_config,
                "timestamp": now,
                "buffer_size": len([v for v in state.history["temp"] if v is not None]),
            }
            socketio.emit("serial_data", payload)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[Serial] Error: {e}")
            time.sleep(1)
