import RPi.GPIO as GPIO
import time
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from threading import Thread

# Configuration
IR_PIN_1 = 17
IR_PIN_2 = 18
MAX_CARS = 8

START_PULSE_MAX = 0.008
START_PULSE_MIN = 0.003
PULSE_COUNT_WINDOW = 0.02
DETECTION_INTERVAL = 0.02
VALIDATION_READINGS = 2

START_PULSE_MAX_MS = START_PULSE_MAX * 1000
START_PULSE_MIN_MS = START_PULSE_MIN * 1000
INTER_PULSE_DELAY = 0.0002
POST_START_DELAY = 0.001
LOOP_DELAY = 0.0001

GPIO.setmode(GPIO.BCM)
GPIO.setup([IR_PIN_1, IR_PIN_2], GPIO.IN)

# Flask Setup
app = Flask(__name__)

# Global variable to store current car detection details
current_car = {'id': None, 'time': None}

def decode_pulses(pin):
    if GPIO.input(pin):
        return None
        
    start = time.time()
    while not GPIO.input(pin) and (time.time() - start < START_PULSE_MAX):
        pass
    
    pulse_len = (time.time() - start) * 1000
    if not (START_PULSE_MIN_MS <= pulse_len <= START_PULSE_MAX_MS):
        return None
        
    time.sleep(POST_START_DELAY)
    
    pulses = 0
    pulse_start = time.time()
    while time.time() - pulse_start < PULSE_COUNT_WINDOW:
        if not GPIO.input(pin):
            pulses += 1
            while not GPIO.input(pin) and (time.time() - pulse_start < PULSE_COUNT_WINDOW):
                pass
            time.sleep(INTER_PULSE_DELAY)
    
    return pulses if 1 <= pulses <= MAX_CARS else None

def validate_car_id(detector_id, car_id):
    global recent_readings
    if detector_id not in recent_readings:
        recent_readings[detector_id] = []
        
    readings = recent_readings[detector_id]
    readings.append(car_id)
    if len(readings) > VALIDATION_READINGS:
        readings.pop(0)
        
    if len(readings) == VALIDATION_READINGS and readings.count(car_id) >= (VALIDATION_READINGS - 1):
        return car_id
    return None

# Route to display the current car detection
@app.route('/')
def home():
    return render_template_string("""
        <h1>Car Detector</h1>
        <h2>Car ID: <span id="car-id">Loading...</span></h2>
        <p>Detected at: <span id="detection-time">Loading...</span></p>
        <script>
            function updateCarData() {
                fetch('/current_car')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('car-id').textContent = data.id || 'None';
                    document.getElementById('detection-time').textContent = data.time || 'None';
                })
                .catch(err => console.error('Error fetching car data:', err));
            }
            
            setInterval(updateCarData, 1000);  // Update every 1 second
            updateCarData();  // Initial call to load data immediately
        </script>
    """)

# Route to fetch current car data in JSON format
@app.route('/current_car')
def current_car_data():
    return jsonify(current_car)

def update_car_detection(validated_id):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_car['id'] = validated_id
    current_car['time'] = current_time

# Run Flask in a separate thread
def run_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True)

flask_thread = Thread(target=run_flask)
flask_thread.start()

try:
    print("IR Car Detector - High Speed Version")
    print("Press Ctrl+C to exit")
    
    last_detection = {1: 0, 2: 0}
    recent_readings = {}
    
    while True:
        for detector_id, pin in [(1, IR_PIN_1), (2, IR_PIN_2)]:
            car_id = decode_pulses(pin)
            if car_id:
                validated_id = validate_car_id(detector_id, car_id)
                if validated_id:
                    current_time = time.time()
                    if current_time - last_detection[detector_id] > DETECTION_INTERVAL:
                        print(f"Car {validated_id} detected on sensor {detector_id} at {current_time}")
                        last_detection[detector_id] = current_time
                        update_car_detection(validated_id)
        
        time.sleep(LOOP_DELAY)

except KeyboardInterrupt:
    print("\nStopping...")
    GPIO.cleanup()
