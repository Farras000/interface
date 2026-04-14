import time
from machine import Pin, time_pulse_us
import dht
import ujson

# ==== PIN SETUP ====
dht_sensor = dht.DHT11(Pin(16))  # disarankan pindah ke 4/16 kalau real hardware

trig = Pin(4, Pin.OUT)
echo = Pin(18, Pin.IN)

# ==== FUNCTION: READ DISTANCE ====
def read_distance():
    trig.off()
    time.sleep_us(2)
    
    trig.on()
    time.sleep_us(10)
    trig.off()
    
    duration = time_pulse_us(echo, 1, 30000)  # timeout 30ms
    
    if duration < 0:
        return -1
    
    distance = (duration * 0.0343) / 2
    return distance

# ==== FUNCTION: LOG ====
def log(msg):
    t = time.localtime()
    timestamp = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    print("[{}] {}".format(timestamp, msg))


# ==== MAIN LOOP ====
while True:
    log("Reading sensors...")

    # --- DHT22 ---
    try:
        dht_sensor.measure()
        suhu = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        
        log("Suhu       : {} °C".format(suhu))
        log("Kelembapan : {} %".format(humidity))
    except:
        suhu = None
        humidity = None
        log("DHT ERROR")

    # --- HC-SR04 ---
    try:
        distance = read_distance()
        
        if distance == -1:
            log("Jarak      : Timeout")
        else:
            log("Jarak      : {:.2f} cm".format(distance))
    except:
        distance = -1
        log("Ultrasonic ERROR")

    # --- JSON ---
    message = ujson.dumps({
        "temperature": suhu,
        "humidity": humidity,
        "distance": distance
    })

    log("Sensor Data: {}".format(message))

    print("-----------------------------")

    # DHT butuh delay minimal
    time.sleep(2)