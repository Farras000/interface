import time
from machine import Pin, time_pulse_us, PWM
import dht
import ujson

# ==== PIN SETUP ====
dht_sensor = dht.DHT11(Pin(16))  

trig = Pin(4, Pin.OUT)
echo = Pin(18, Pin.IN)

fan = PWM(Pin(23))
fan.freq(25000)

# ==== FUNCTION: READ DISTANCE ====
def read_distance():
    trig.off()
    time.sleep_us(2)
    
    trig.on()
    time.sleep_us(10)
    trig.off()
    
    duration = time_pulse_us(echo, 1, 30000)
    
    if duration < 0:
        return -1
    
    return (duration * 0.0343) / 2

# ==== FUNCTION: FAN ON/OFF ====
def set_fan(dist):
    if dist != -1 and dist < 100:
        fan.duty(1023)  # FULL ON
        return 1
    else:
        fan.duty(0)     # OFF
        return 0

# ==== FUNCTION: LOG ====
def log(msg):
    t = time.localtime()
    timestamp = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    print("[{}] {}".format(timestamp, msg))

# ==== MAIN LOOP ====
while True:
    start_time = time.time()

    log("Reading sensors...")

    # --- DHT (optional, tetap dibaca kalau mau log) ---
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

    # ==== FAN CONTROL ====
    fan_state = set_fan(distance)

    if fan_state:
        log("Fan Status : ON")
    else:
        log("Fan Status : OFF")

    # --- JSON ---
    message = ujson.dumps({
        "temperature": suhu,
        "humidity": humidity,
        "distance": distance,
        "fan": fan_state
    })

    log("Sensor Data: {}".format(message))
    print("-----------------------------")

    # ==== LOOP TIMING ====
    elapsed = time.time() - start_time
    sleep_time = 1 - elapsed
    
    if sleep_time > 0:
        time.sleep(sleep_time)