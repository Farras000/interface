import serial
import json
import time
from datetime import datetime
from statistics import median

import state
from config import SERIAL_PORT, BAUD_RATE, SENSORS
from utils import is_valid, temp_to_fan_speed, _compute_pwm
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
    ser = None
    current_port = None

    while True:
        try:
            # Check if target port has changed
            if state.selected_port != current_port:
                if ser is not None:
                    try:
                        ser.close()
                        print(f"[Serial] Closed port {current_port}")
                    except Exception as e:
                        print(f"[Serial] Error closing port {current_port}: {e}")
                    ser = None
                    current_port = None
                    socketio.emit("port_status", {"status": "disconnected", "port": current_port})

                if state.selected_port:
                    try:
                        ser = serial.Serial(state.selected_port, BAUD_RATE, timeout=1)
                        current_port = state.selected_port
                        print(f"[Serial] Connected to {current_port}")
                        socketio.emit("port_status", {"status": "connected", "port": current_port})
                    except serial.SerialException as e:
                        print(f"[Serial] Could not open {state.selected_port}: {e}")
                        socketio.emit("port_status", {"status": "error", "message": str(e), "port": state.selected_port})
                        ser = None
                        current_port = None
                        time.sleep(2)
                        continue

            if ser is None:
                time.sleep(0.5)
                continue

            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue
            
            # Extract JSON substring in case there is a debug prefix
            json_start = raw.find('{')
            if json_start != -1:
                json_end = raw.rfind('}')
                json_str = raw[json_start:json_end + 1]
                data = json.loads(json_str)
            else:
                data = json.loads(raw)

            if not is_valid(data):
                print(f"[Serial] Dropped bad reading: {raw}")
                continue

            # ── Compute and send fan speed back to Arduino ──
            temp = data.get("temp")
            dist = data.get("dist")

            if dist is not None:
                state.dist_buffer.append(dist)

            stable_dist = median(state.dist_buffer) if len(state.dist_buffer) > 0 else dist

            # ── Check manual override ──
            if getattr(state, "fan_mode", "auto") == "manual":
                fan_speed = getattr(state, "manual_fan_speed", 0)
                ser.write(f"{fan_speed}\n".encode())
                print(f"[Fan] MANUAL OVERRIDE → PWM={fan_speed}")
            else:
                # If stable_dist == -1 (no echo) or > 100 (out of range), turn fan off
                if stable_dist == -1 or stable_dist > 100:
                    fan_speed = 0
                    ser.write(f"{fan_speed}\n".encode())
                    if stable_dist > 100:
                        print(f"[Fan] dist={dist} → out of range (>{100}cm) → PWM=0 (fan off)")
                    elif dist != -1:
                        print(f"[Fan] dist={dist} (raw) → median filtered → PWM=0 (fan off)")
                    else:
                        print(f"[Fan] dist=-1 (no object in range) → PWM=0 (fan off)")
                else:
                    fan_speed = temp_to_fan_speed(temp)
                    ser.write(f"{fan_speed}\n".encode())
                    if temp is None:
                        print(f"[Fan] temp=None → PWM={fan_speed} (held)")
                    elif len(state.temp_buffer) > 1 and fan_speed != _compute_pwm(temp):
                        print(f"[Fan] temp={temp}°C (raw) → median filtered → PWM={fan_speed}")
                    else:
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

        except serial.SerialException as e:
            print(f"[Serial] Connection error on {current_port}: {e}")
            socketio.emit("port_status", {"status": "error", "message": f"Connection lost: {e}", "port": current_port})
            if ser is not None:
                try:
                    ser.close()
                except:
                    pass
            ser = None
            current_port = None
            time.sleep(2)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[Serial] Error: {e}")
            time.sleep(1)
