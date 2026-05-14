# Temperature-Controlled Smart Fan Code Explanation

This document explains the functionality of the C++ code found in `src/main.cpp`.

## Overview
The code is designed to control a cooling fan based on two factors: **room temperature** and the **proximity of an object (or person)**. It uses a DHT11 sensor to read temperature and humidity, and an HC-SR04-style ultrasonic sensor to measure distance. The fan is controlled using Pulse Width Modulation (PWM) to adjust its speed dynamically. Finally, all the collected data is formatted as JSON and sent over the Serial monitor.

## Hardware Configuration (Pinout)
* **DHT11 Sensor (Temperature/Humidity)**: Connected to Pin 2 (Defined as `DHTPIN`).
* **Ultrasonic distance sensor (HC-SR04)**: 
  * Trigger Pin: Pin 3 (`TRIG`)
  * Echo Pin: Pin 4 (`ECHO`)
* **Cooling Fan**: Connected to Pin 5 (`FAN`). Must be a PWM-compatible pin to support variable speed.

## How the Code Works

### 1. Distance Calculation (`readDistance()`)
The function `readDistance()` emits an ultrasonic pulse and listens for the echo:
1. It sends a short high pulse (10 microseconds) on the `TRIG` pin.
2. It waits for the `ECHO` pin to go high and measures the duration.
3. It converts the duration into a raw distance using the speed of sound (`duration * 0.034 / 2.0`).
4. A small linear calibration is applied to tweak the raw values (`1.037 * rawDist - 0.115`).
5. It returns the calculated distance in centimeters. If the sensor times out (no object), it returns `-1.0`.

### 2. Fan Speed Logic (`getFanSpeed()`)
The `getFanSpeed(temp, dist)` function decides how fast the fan should spin:
* **Distance Check**: If the distance is `-1` (no object found) or greater than `100` cm (object/user is too far away), it immediately returns `0`, turning the fan completely off to save energy.
* **Temperature Check** (assuming an object *is* close by):
  * **Temp < 22°C**: Fan is set to `90` PWM (A very low baseline speed, but marked as "OFF" in comments).
  * **22°C ≤ Temp ≤ 23°C**: Fan is set to `150` PWM (LOW speed).
  * **23°C < Temp ≤ 24°C**: Fan is set to `200` PWM (MEDIUM speed).
  * **Temp > 24°C**: Fan is set to `255` PWM (HIGH speed, maximum output).

### 3. Setup and Initialization (`setup()`)
* Starts Serial communication at a baud rate of `115200` to stream data to a computer or connected device.
* Configures pin modes (Inputs/Outputs).
* Initializes the DHT11 sensor.

### 4. Main Event Loop (`loop()`)
Every 1 second (`delay(1000)`), the microcontroller does the following sequence:
1. **Reads sensors**: Captures temperature, humidity, and distance.
2. **Determines state**: Calls `getFanSpeed()` to determine the required fan speed based on current readings.
3. **Applies speed**: Uses `analogWrite(FAN, fanSpeed)` to set the physical speed of the motor.
4. **Serial Detailed Output**: Prints out detailed distance measurements in multiple units (cm, meters, inches) for debugging.
5. **Serial JSON Output**: Packages rounded numbers into a clean JSON string, for instance: `{"temp":24,"hum":45,"dist":50,"fan":200}`. This format is highly optimal for parsing by an external Python script or Web Interface.
