# Temperature-Controlled Smart Fan Code Explanation

This document explains the functionality of the Arduino C++ firmware logic.

## Overview
The code is designed to monitor **room temperature** and the **proximity of an object (or person)**, and control a cooling fan based on serial commands. It uses a DHT11 sensor to read temperature and humidity, and an HC-SR04-style ultrasonic sensor to measure distance. The fan is controlled using Pulse Width Modulation (PWM) dynamically based on commands received from a connected device (e.g., a Python app). Finally, all the collected data is formatted as JSON and sent out over the Serial monitor.

## Hardware Configuration (Pinout)
* **DHT11 Sensor (Temperature/Humidity)**: Connected to Pin 2 (Defined as `DHTPIN`).
* **Ultrasonic distance sensor (HC-SR04)**: 
  * Trigger Pin: Pin 3 (`TRIG`)
  * Echo Pin: Pin 4 (`ECHO`)
* **Cooling Fan**: Connected to Pin 5 (`FAN`). Must be a PWM-compatible pin to support variable speed. Pin configuration for the fan:
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

## How the Code Works

### 1. Distance Calculation (`readDistance()`)
The function `readDistance()` emits an ultrasonic pulse and listens for the echo:
1. It sends a short high pulse (10 microseconds) on the `TRIG` pin.
2. It waits for the `ECHO` pin to go high and measures the duration.
3. It converts the duration into a raw distance using the speed of sound (`duration * 0.034 / 2.0`).
4. A small linear calibration is applied to tweak the raw values (`1.037 * rawDist - 0.115`). If the calibrated distance is below 0, it is snapped to 0.
5. It returns the calculated distance in centimeters. If the sensor times out (no object), it returns `-1.0`.

### 2. Fan Speed Control (Serial Input)
Unlike standalone systems that make their own decisions, this code expects the fan speed to be controlled by an external app (like Python).
* **Serial Reading**: Within the `loop()`, it checks if there is any readable serial data (`Serial.available() > 0`). 
* **Parsing**: It parses an integer from the serial stream using `Serial.parseInt()` and clears out any remaining newline characters.
* **Applying Speed**: The value is constrained between `0` and `255` and saved to the global `currentFanSpeed` variable, which is then used to control the fan.

### 3. Setup and Initialization (`setup()`)
* Starts Serial communication at a baud rate of `115200` to stream data to a computer or connected device.
* Configures pin modes (Inputs/Outputs).
* Initializes the DHT22 sensor.

### 4. Main Event Loop (`loop()`)
Every 1 second (`delay(1000)`), the microcontroller does the following sequence:
1. **Reads Serial input**: Checks for incoming target speeds from the connected application.
2. **Reads sensors**: Captures temperature, humidity, and distance.
3. **Serial Detailed Output**: Prints out detailed distance measurements in multiple units (cm, meters, inches) for debugging.
4. **Applies speed**: Uses `analogWrite(FAN, currentFanSpeed)` to set the physical speed of the motor.
5. **Serial JSON Output**: Packages rounded numbers into a clean JSON string, for instance: `{"temp":24,"hum":45,"dist":50,"fan":200}`. This format is highly optimal for parsing by an external Python script or Web Interface.
