import RPi.GPIO as GPIO
import mysql.connector
from datetime import datetime
from irrcv.nec import NEC_IR

maxCars = 6

# GPIO setup for two detectors
IR_PIN_1 = 17
IR_PIN_2 = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup([IR_PIN_1, IR_PIN_2], GPIO.IN)

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="pi_user",
    password="yourpassword",
    database="rc_timing"
)
cursor = db.cursor()

# Initialize IR decoders
ir_decoder_1 = NEC_IR(IR_PIN_1)
ir_decoder_2 = NEC_IR(IR_PIN_2)
def log_detection(car_id, detector_id):
    try:
        cursor.execute(
            "INSERT INTO lap_times (car_id, detector_id) VALUES (%s, %s)", 
            (car_id, detector_id)
        )
        db.commit()
        print(f"Car {car_id} detected on sensor {detector_id}")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        db.rollback()
try:
    print("Starting IR detection...")
    while True:
        if ir_decoder_1.decode():
            car_id = ir_decoder_1.command
            if 1 <= car_id <= maxCars:
                log_detection(car_id, 1)

        if ir_decoder_2.decode():
            car_id = ir_decoder_2.command
            if 1 <= car_id <= maxCars:
                log_detection(car_id, 2)

        # The time.sleep(0.01) adds a 10-millisecond delay to prevent the CPU from running at 100% utilization. Without this delay:
        # - The while loop would run as fast as possible
        # - CPU usage would be unnecessarily high
        # - Could potentially make the system less responsive
        # The 10ms delay is a balance between:
        # - Being responsive enough to not miss IR signals (NEC protocol takes ~67ms to transmit)
        # - Keeping CPU usage reasonable
        # - Allowing other system processes to run
        # You could adjust this value based on your needs:
        # - Decrease for faster response time
        # - Increase to reduce CPU usage
        # - Remove entirely if you need absolute minimum latency
        time.sleep(0.01)
except KeyboardInterrupt:
    GPIO.cleanup()
    db.close()
