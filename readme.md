# 🌡️ Smart Fan — Temperature-Controlled Fan with Real-Time Web Dashboard

A full-stack IoT project that reads sensor data from an **Arduino** over serial, computes a **linear fan speed** based on temperature, sends the PWM value back to the Arduino, and visualizes everything in a **real-time web dashboard** with advanced signal processing.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Setup](#hardware-setup)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [How Fan Speed Works](#how-fan-speed-works)
- [Signal Processing](#signal-processing)
- [Project Structure](#project-structure)
- [Logs & Data Export](#logs--data-export)

---

## Overview

The system consists of two parts:

| Layer | Role |
|---|---|
| **Arduino (C/C++)** | Reads DHT11/DHT22 (temperature/humidity) and HC-SR04 (distance) sensors, sends JSON data over serial, and applies PWM fan speed received from Python. |
| **Python (Flask + SocketIO)** | Reads serial JSON, computes the fan speed linearly from temperature, writes the PWM value back to the Arduino, logs data to CSV, performs signal processing, and serves a real-time web dashboard via WebSocket. |

### Data Flow

```
Arduino                         Python Server                    Browser
  │                                  │                              │
  │── JSON {temp,hum,dist,fan} ────► │                              │
  │                                  │── compute fan PWM ──►        │
  │◄── PWM value (0–255) ─────────── │                              │
  │                                  │── WebSocket emit ──────────► │
  │                                  │                     (real-time charts)
```

---

## Features

- **Linear fan speed control** — PWM is linearly interpolated from temperature (configurable min/max thresholds)
- **Real-time web dashboard** — live charts for temperature, humidity, distance, and fan speed via Socket.IO
- **Signal processing suite**:
  - Moving average filter
  - FFT (Fast Fourier Transform) spectrum analysis
  - Configurable digital filters (lowpass, highpass, bandpass) via Butterworth design
  - Rate-of-change (derivative) computation
  - Pearson correlation between sensor pairs
- **CSV data logging** — timestamped logs saved automatically to `logs/`
- **Download logs** — one-click CSV download from the web interface
- **Pause/Resume** — toggle live dashboard updates without stopping data collection
- **Data validation** — out-of-range sensor readings are automatically dropped

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Arduino Uno                           │
│                                                             │
│  DHT11/DHT22 (Pin 2)  ──►  Read Temp & Humidity             │
│  HC-SR04 (Pin 3/4) ──►  Read Distance                       │
│  Fan (Pin 5, PWM) ◄──  analogWrite(currentFanSpeed)         │
│                                                             │
│  Serial OUT:  {"temp":28,"hum":60,"dist":45,"fan":180}      │
│  Serial IN:   180\n  (PWM value from Python)                │
└────────────────────────┬────────────────────────────────────┘
                         │ USB Serial (115200 baud)
┌────────────────────────▼────────────────────────────────────┐
│                    Python Server                            │
│                                                             │
│  serial_reader.py   ── read JSON, compute fan, write back   │
│  utils.py           ── temp_to_fan_speed() linear mapping   │
│  signal_processing  ── FFT, filters, stats, correlation     │
│  server.py          ── Flask + SocketIO (port 8000)         │
│  state.py           ── shared history buffers & config      │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket (Socket.IO)
┌────────────────────────▼────────────────────────────────────┐
│                    Web Dashboard                            │
│                                                             │
│  Real-time charts (temp, hum, dist, fan)                    │
│  FFT spectrum   ·   Filter controls   ·   Statistics        │
│  Correlation plots  ·  Pause/Resume   ·  CSV Download       │
└─────────────────────────────────────────────────────────────┘
```

---

## Hardware Setup

### Components

| Component | Description |
|---|---|
| Arduino Uno (or compatible) | Microcontroller board |
| DHT11/DHT22 | Temperature & humidity sensor |
| HC-SR04 | Ultrasonic distance sensor |
| DC Fan (5V) | PWM-controlled cooling fan |
| MOSFET / transistor | To drive the fan from a PWM pin (if needed) |
| Breadboard + jumper wires | For wiring |

### Pin Connections

| Arduino Pin | Connected To      | Notes |
|---|---|---|
| **Pin 2** | DHT11/DHT22 data pin    | Add a 10kΩ pull-up resistor to VCC  |
| **Pin 3** | HC-SR04 TRIG      | Trigger (output)                    |
| **Pin 4** | HC-SR04 ECHO      | Echo (input)                        |
| **Pin 5** | Fan (via MOSFET)  | Must be a PWM-capable pin           |
| **5V**    | Sensor VCC        | Power for DHT11/DHT22 and HC-SR04         |
| **GND**   | Common ground     | All components share ground         |

### Wiring Diagram

```
         Arduino Uno
        ┌───────────┐
  5V ───┤ 5V    GND ├─── GND (common)
        │           │
Pin 2 ──┤ D2        │──── DHT11/DHT22 Data (+ 10kΩ pull-up to 5V)
Pin 3 ──┤ D3        │──── HC-SR04 TRIG
Pin 4 ──┤ D4        │──── HC-SR04 ECHO
Pin 5 ──┤ D5 (PWM)  │──── Fan (via MOSFET gate)
        └───────────┘
```

### Detailed Component Wiring

#### DHT11/DHT22 Sensor:
```text
Arduino D2 ────────── Data
                     │
                   [10kΩ] (Optional pull-up)
                     │
                    5V

Arduino 5V ────────── VCC

Arduino GND ───────── GND
```

#### HC-SR04 Ultrasonic Sensor:
```text
Arduino 5V ────────── VCC

Arduino GND ───────── GND

Arduino D3 ────────── TRIG

Arduino D4 ────────── ECHO
```

#### 5V Fan (via MOSFET):
```text
Arduino D5 ──[220Ω]── Gate
                     │
                   [10kΩ]
                     │
                    GND

Source ───────────── GND (Arduino)

Drain ────────────── negatif fan

Positif fan ─────── 5V
```

---

## Software Requirements

- **Python 3.8+**
- **VS Code with PlatformIO** or **Arduino IDE** (to flash the Arduino sketch)
- A modern web browser

### Python Dependencies

| Package | Purpose |
|---|---|
| `flask` | Web server |
| `flask-socketio` | Real-time WebSocket communication |
| `pyserial` | Serial port communication with Arduino |
| `numpy` | Numerical operations and FFT |
| `scipy` | Butterworth digital filter design |

---

## Installation

> **Note:** The C++ firmware for the microcontroller is hosted separately. You can get the complete Arduino code from this repository: 🔗 [Farras000/interface-arduino](https://github.com/Farras000/interface-arduino/)

### 1. Flash the Arduino

**Using PlatformIO (Recommended):**
1. Open the project folder (`PlatformIO/Projects/interface`) in **VS Code** with the **PlatformIO IDE** extension installed.
2. The `platformio.ini` should handle library dependencies (ensure `Adafruit Unified Sensor` and `DHT sensor library` are included).
3. Connect your microcontroller and click **Build** then **Upload** in the PlatformIO panel.

**Using Arduino IDE:**
1. Open the main source file (e.g., `src/main.cpp` renamed to `main.ino`) in the **Arduino IDE**.
2. Go to **Sketch > Include Library > Manage Libraries...** and install `Adafruit Unified Sensor` and `DHT sensor library`.
3. Select your board and port from the **Tools** menu, then click **Upload**.

### 2. Set Up Python

```bash
# Clone or navigate to the project directory
cd interface

# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirement.txt
```

---

## Configuration

All configuration lives in **`config.py`**:

```python
SERIAL_PORT = "COM6"       # Change to your Arduino's port
BAUD_RATE   = 115200       # Must match the Arduino sketch

# Fan speed temperature thresholds
TEMP_MIN = 22              # °C – below this, fan is OFF
TEMP_MAX = 30              # °C – at or above this, fan is at full speed (255)

# Signal processing windows
FILTER_WINDOW = 5          # Moving average window
STATS_WINDOW  = 60         # Statistics window (last N readings)
FFT_WINDOW    = 64         # FFT sample count
```

### Finding Your Serial Port

| OS | Command |
|---|---|
| Windows | Check **Device Manager → Ports (COM & LPT)** |
| Linux | `ls /dev/ttyACM*` or `ls /dev/ttyUSB*` |
| macOS | `ls /dev/cu.usbmodem*` |

---

## Usage

### Start the Server

```bash
python server.py
```

The server will:
1. Initialize CSV logging in `logs/`
2. Connect to the Arduino on the configured serial port
3. Start the Flask web server on **http://localhost:8000**

### Open the Dashboard

Open your browser and navigate to:

```
http://localhost:8000
```

### Dashboard Controls

| Control | Description |
|---|---|
| **Pause / Resume** | Toggle live chart updates (data still logs to CSV) |
| **Filter Type** | Select lowpass, highpass, bandpass, or none |
| **Cutoff Frequency** | Adjust the filter cutoff (0.01–0.49 normalized) |
| **Filter Order** | Set Butterworth filter order (1–6) |
| **Download CSV** | Download the current session's log file |

### Standalone Monitor (Optional)

For a quick matplotlib-based monitor without the web UI:

```bash
python monitor.py
```

---

## How Fan Speed Works

The Python server computes the fan PWM value using a **linear mapping** from temperature and sends it back to the Arduino over serial.

### Linear Mapping Formula

```
if temp ≤ TEMP_MIN (22°C):  fan = 0     (OFF)
if temp ≥ TEMP_MAX (30°C):  fan = 255   (FULL)
otherwise:
    ratio = (temp - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)
    fan   = 100 + ratio × (255 - 100)
```

| Temperature | PWM Value | Fan State |
|---|---|---|
| ≤ 22°C | 0 | Off |
| 24°C | ~149 | Low |
| 26°C | ~197 | Medium |
| 28°C | ~245 | High |
| ≥ 30°C | 255 | Full Speed |

> The minimum non-zero PWM is **100** to ensure the fan actually spins (most DC fans have a minimum startup voltage).

---

## Signal Processing

The dashboard provides several real-time signal processing features powered by NumPy and SciPy:

| Feature | Description |
|---|---|
| **Moving Average** | Smooths sensor readings over a configurable window |
| **FFT Spectrum** | Shows frequency components of sensor data (Hanning window, DC-removed) |
| **Digital Filters** | Butterworth lowpass / highpass / bandpass (adjustable from the frontend) |
| **Derivative** | Rate of change per sample (~1 second intervals) |
| **Correlation** | Pearson coefficient and scatter plots between sensor pairs (temp↔fan, temp↔hum, temp↔dist) |

---

## Project Structure

```
interface/
├── server.py               # Flask + SocketIO entry point (routes, events, startup)
├── serial_reader.py         # Serial reader thread (read JSON, compute fan, send back)
├── config.py                # All configuration constants
├── state.py                 # Shared state (history buffers, CSV, pause flag, filter config)
├── utils.py                 # Utilities (CSV init, validation, temp_to_fan_speed)
├── signal_processing.py     # Signal processing (FFT, filters, stats, correlation)
├── monitor.py               # Standalone matplotlib real-time plotter
├── templates/
│   └── index.html           # Web dashboard (charts, controls)
├── static/
│   └── style.css            # Dashboard styles
│
├── logs/                    # Auto-generated CSV log files (gitignored)
├── requirement.txt          # Python dependencies
├── hardware-setup.md        # Detailed Arduino code explanation
├── Project.md               # Original project documentation
├── .gitignore               # Git ignore rules
└── readme.md                # This file
```

---

## Logs & Data Export

- Logs are saved automatically to `logs/log_YYYYMMDD_HHMMSS.csv` on each server start.
- Each row contains: `timestamp, temp, hum, dist, fan`.
- Data is flushed to disk after every reading, even when the dashboard is paused.
- Download the current log from the dashboard or via `http://localhost:8000/download`.

---

## Arduino Firmware

🔗 **Source Code:** [Farras000/interface-arduino](https://github.com/Farras000/interface-arduino/)

The firmware for the Arduino is written in C++. It can be built and uploaded using **PlatformIO** or the standard **Arduino IDE**. The logic involves:
1. Reading temperature and humidity from the DHT11/DHT22 sensor.
2. Reading distance from the HC-SR04 ultrasonic sensor.
3. Sending the readings as a JSON string over Serial.
4. Receiving a PWM value back from the Python server and applying it to the fan.


