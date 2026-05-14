import serial
import json
import matplotlib.pyplot as plt
from collections import deque

ser = serial.Serial('COM6', 115200, timeout=1)

temp_data = deque(maxlen=50)
fan_data = deque(maxlen=50)

plt.ion()
fig, ax = plt.subplots()

line_temp, = ax.plot([], [], label="Temp (°C)")
line_fan, = ax.plot([], [], label="Fan PWM")

ax.legend()
ax.set_title("Realtime Monitoring")

while True:
    try:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue

        data = json.loads(line)

        temp = data.get("temp")
        fan = data.get("fan")

        if temp is not None:
            temp_data.append(temp)
            fan_data.append(fan)

            line_temp.set_data(range(len(temp_data)), temp_data)
            line_fan.set_data(range(len(fan_data)), fan_data)

            ax.relim()
            ax.autoscale_view()

            plt.pause(0.05)

    except Exception as e:
        print("Error:", e)