# Smart Fan Node Interface

This project is a microcontroller-based interface that collects environmental data (temperature and humidity) and detects object presence using an ultrasonic distance sensor. It receives fan speed control commands over a Serial connection and continuously outputs the system's state in JSON format, making it ideal for integration with a Python backend, IoT gateway, or a web dashboard.

## Features

* **Environmental Monitoring**: Tracks real-time temperature and humidity. *(Note: Supports both **DHT11** and **DHT22** sensors depending on your specific configuration).*
* **Proximity Detection**: Measures the distance of nearby objects using an HC-SR04 ultrasonic sensor.
* **PWM Fan Control**: Dynamically adjusts a cooling fan's speed based on Serial input commands.
* **JSON Data Streaming**: Packages all sensor readings and the current fan state into a clean JSON string sent via Serial (`115200` baud) for easy parsing by external applications.

## Hardware Components & Pinout

| Component | Pin | Note |
| :--- | :--- | :--- |
| **DHT11 / DHT22** Sensor | `2` | Temperature and Humidity (`DHTPIN`) |
| **HC-SR04** Trig | `3` | Ultrasonic emits trigger (`TRIG`) |
| **HC-SR04** Echo | `4` | Ultrasonic reads pulse echo (`ECHO`) |
| **DC Fan** | `5` | Requires a PWM-capable output pin (`FAN`) |

## Data Protocol

### Input (Host -> Microcontroller)
The microcontroller listens on the Serial port for an integer value between `0` and `255`. This value is parsed and directly sets the PWM duty cycle for the fan (where `0` is completely off and `255` is maximum speed).

### Output (Microcontroller -> Host)
Sensor data is transmitted every 1 second continuously in the following JSON format:
```json
{"temp":24,"hum":45,"dist":50,"fan":200}
```
* `temp`: Temperature in degrees Celsius.
* `hum`: Relative humidity percentage.
* `dist`: Object distance in centimeters (`-1` if out of bounds/no echo).
* `fan`: Current fan speed (PWM value `0-255`).

*(Note: Human-readable detailed distance debugging output is also supplied via `DIST_DETAIL_CM:...` before the JSON string for terminal manual inspection).*

## Getting Started

This project is structured for **PlatformIO**, but can also be used with the **Arduino IDE**.

1. Clone or download this repository.
2. **Using PlatformIO:** Open the project folder (`PlatformIO/Projects/interface`) in **VS Code** with the **PlatformIO IDE** extension installed. Your `platformio.ini` should handle library dependencies.
3. **Using Arduino IDE:** Open the main source file (e.g., `src/main.cpp` renamed to `main.ino`) in the **Arduino IDE** and manually install the `Adafruit Unified Sensor` and `DHT sensor library` via the Library Manager.
4. Connect your microcontroller and upload the code (via **Build > Upload** in PlatformIO or **Upload** in Arduino IDE).
5. Open the Serial Monitor (ensure the baud rate is set to `115200`) to view the JSON output and test sending PWM control values.

## Deep Dive
For a detailed explanation of the project's internal code logic and loop sequence, please refer to the [`src/main_explanation.md`](src/main_explanation.md) documentation file.
