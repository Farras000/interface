# ESP32 Sensor Interface

This project provides a MicroPython script to read data from a DHT11 temperature/humidity sensor and an HC-SR04 ultrasonic distance sensor, outputting the values via the serial console and formatting them into a JSON string.

## Hardware Requirements

To replicate this setup, you will need the following hardware components:

*   **ESP32 Development Board**: Any standard ESP32 board (e.g., NodeMCU ESP32, WROOM-32) will work.
*   **DHT11 Sensor**: For measuring temperature and humidity. Note: A DHT22 can also be used, but the code currently initializes a DHT11.
*   **HC-SR04 Ultrasonic Distance Sensor**: For measuring distance.
*   **Jumper Wires**: For making connections.
*   **Breadboard** (Optional, but recommended for wiring).
*   **Micro-USB or USB-C Cable**: For power and flashing/programming the ESP32.

## Wiring Diagram

Connect the components to the ESP32 according to the following mapping:

### DHT11 Sensor
*   **VCC** -> `3.3V` (or 5V depending on your specific DHT11 module)
*   **GND** -> `GND`
*   **DATA** -> **`GPIO 16`**

### HC-SR04 Ultrasonic Sensor
*   **VCC** -> `5V` (The HC-SR04 typically requires 5V to operate reliably. Some ESP32 boards have a `VIN` or `5V` pin that outputs USB voltage. If using 5V, you might need a voltage divider on the Echo pin, as ESP32 GPIOs are 3.3V tolerant, though many people use it directly without issues).
*   **GND** -> `GND`
*   **TRIG** -> **`GPIO 4`**
*   **ECHO** -> **`GPIO 18`**

## Software Setup

1.  **MicroPython Firmware**: Ensure your ESP32 has MicroPython installed. You can flash it using tools like `esptool`.
2.  **IDE**: Use an IDE that supports MicroPython, such as Thonny, uPyCraft, or VS Code with the MicroPico/PyMakr extension.
3.  **Upload Code**:
    *   Connect the ESP32 to your computer.
    *   Open `main.py` in your chosen IDE.
    *   Upload or save the `main.py` file to the ESP32's internal storage. If you want it to run automatically on boot, ensure the file is named `main.py`.

## Output

Once the ESP32 is powered on and running the script, open a Serial Monitor (baud rate typically 115200 for MicroPython REPL). You will see output similar to this:

```
[00:00:02] Reading sensors...
[00:00:02] Suhu       : 28 °C
[00:00:02] Kelembapan : 60 %
[00:00:02] Jarak      : 12.50 cm
[00:00:02] Sensor Data: {"humidity": 60, "temperature": 28, "distance": 12.5}
-----------------------------
[00:00:04] Reading sensors...
```

The script measures and prints the variables every 2 seconds. In case of a sensor error, it will log "DHT ERROR" or "Ultrasonic ERROR" respectively.
