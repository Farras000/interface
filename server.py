"""
Flask + SocketIO entry point.
Routes, WebSocket events, and application startup.
"""

import os
import threading
from flask import Flask, render_template, send_file
from flask_socketio import SocketIO

import state
from utils import init_csv
from serial_reader import serial_reader

app = Flask(__name__)
app.config["SECRET_KEY"] = "smartfan"
socketio = SocketIO(app, cors_allowed_origins="*")


# ── Socket.IO Events ──────────────────────────────────
@socketio.on("toggle_pause")
def handle_pause():
    state.paused = not state.paused
    socketio.emit("pause_state", {"paused": state.paused})
    print(f"[Control] {'Paused' if state.paused else 'Resumed'}")


@socketio.on("set_filter")
def handle_set_filter(config):
    """Receive filter configuration from the frontend."""
    if "type" in config:
        state.filter_config["type"] = config["type"]
    if "cutoff" in config:
        state.filter_config["cutoff"] = max(0.01, min(0.49, float(config["cutoff"])))
    if "cutoff_high" in config:
        state.filter_config["cutoff_high"] = max(0.01, min(0.49, float(config["cutoff_high"])))
    if "order" in config:
        state.filter_config["order"] = max(1, min(6, int(config["order"])))
    print(f"[Filter] Config updated: {state.filter_config}")
    socketio.emit("filter_updated", state.filter_config)


@socketio.on("set_fan_mode")
def handle_set_fan_mode(data):
    if "mode" in data:
        state.fan_mode = data["mode"]
    if "speed" in data:
        state.manual_fan_speed = int(data["speed"])
    print(f"[Control] Fan mode: {state.fan_mode}, Speed: {state.manual_fan_speed}")


# ── HTTP Routes ────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download")
def download():
    if state.csv_path and os.path.exists(state.csv_path):
        return send_file(state.csv_path, as_attachment=True)
    return "No log file yet", 404


# ── Main ───────────────────────────────────────────────
if __name__ == "__main__":
    init_csv()
    print(f"[CSV] Logging to {state.csv_path}")
    t = threading.Thread(target=serial_reader, args=(socketio,), daemon=True)
    t.start()
    socketio.run(app, host="0.0.0.0", port=8000, debug=False, allow_unsafe_werkzeug=True)