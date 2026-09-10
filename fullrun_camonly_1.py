import RPi.GPIO as GPIO
import cv2
import time
import numpy as np
import threading
from RPLCD.i2c import CharLCD
import max30102
import hrcalc
import time
from heart_processor import HeartProcessor



# === GPIO SETUP ===
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

RED_LED = 13
GREEN_LED = 18
BLUE_LED = 19
BUZZER = 4
MOTOR_PWM = 12

GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(BLUE_LED, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)
GPIO.setup(MOTOR_PWM, GPIO.OUT)

pwm = GPIO.PWM(MOTOR_PWM, 1000)
pwm.start(0)  # Initially stop motor

# === LCD SETUP ===
lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
lcd.clear()
lcd.write_string("Initializing...")
time.sleep(1)
lcd.clear()

# === CAMERA SETUP ===
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')

# === HEART RATE SENSOR SETUP ===
sensor = max30102.MAX30102()
heart = HeartProcessor()
hr = 0
spo2 = 0

def update_heart_rate():
    global hr, spo2
    red, ir = sensor.read_sequential()

    if red and ir:
        red_val = red[-1]
        ir_val = ir[-1]
        timestamp = int(time.time() * 1000)

        if ir_val > 7000:
            if heart.last_ir < 7000 and ir_val >= 7000:
                hr = heart.add_beat(timestamp)
            spo2 = heart.update_spo2(red_val, ir_val)

        heart.last_ir = ir_val



def set_led(r, g, b):
    GPIO.output(RED_LED, r)
    GPIO.output(GREEN_LED, g)
    GPIO.output(BLUE_LED, b)

def beep_buzzer():
    for _ in range(5):
        GPIO.output(BUZZER, GPIO.HIGH)
        time.sleep(0.3)
        GPIO.output(BUZZER, GPIO.LOW)
        time.sleep(0.3)

def blink_blue_led():
    for _ in range(5):
        GPIO.output(BLUE_LED, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(BLUE_LED, GPIO.LOW)
        time.sleep(0.2)

normal_mode = True
delay_active = False
delay_start_time = 0

eyes_closed_count = 0
EYES_CLOSED_THRESHOLD = 10
DELAY_DURATION = 5  # Reduced delay duration

def delay_recovery():
    global delay_active, normal_mode, delay_start_time
    while True:
        pwm.ChangeDutyCycle(0)  # Ensure motor stops during recovery
        blink_blue_led()
        update_heart_rate()
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        eyes_open = False
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y + h, x:x + w]
            eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=10, minSize=(30, 30))
            if len(eyes) > 0:
                eyes_open = True

        if eyes_open:
            print("Eyes open. Resuming normal mode.")
            lcd.clear()
            lcd.write_string("Eyes: Open")
            lcd.crlf()
            lcd.write_string(f"HR:{hr} SpO2:{spo2}")
            set_led(0, 1, 0)
            pwm.ChangeDutyCycle(100)
            delay_active = False
            normal_mode = True
            break
        else:
            print("Still drowsy. Checking again...")
            lcd.clear()
            lcd.write_string("Still Drowsy")
            lcd.crlf()
            lcd.write_string(f"HR:{hr} SpO2:{spo2}")
            set_led(1, 0, 0)
            beep_buzzer()
            time.sleep(DELAY_DURATION)

try:
    while True:
        update_heart_rate()
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        eyes_found = False
        eyes_open = False

        if len(faces) == 0:
            print("Face not detected")
            lcd.clear()
            lcd.write_string("Face Not Found")
            lcd.crlf()
            lcd.write_string(f"HR:{hr} SpO2:{spo2}")
            set_led(0, 0, 1)
            pwm.ChangeDutyCycle(0)
            GPIO.output(BUZZER, 0)
        else:
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                roi_gray = gray[y:y + h, x:x + w]
                roi_color = frame[y:y + h, x:x + w]
                eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=10, minSize=(30, 30))
                if len(eyes) > 0:
                    eyes_found = True
                    eyes_open = True
                    for (ex, ey, ew, eh) in eyes:
                        cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

            if normal_mode:
                if eyes_found and eyes_open:
                    eyes_closed_count = 0
                    set_led(0, 1, 0)
                    GPIO.output(BUZZER, 0)
                    pwm.ChangeDutyCycle(100)
                    lcd.clear()
                    lcd.write_string("Eyes: Open")
                    lcd.crlf()
                    lcd.write_string(f"HR:{hr} SpO2:{spo2}")
                else:
                    eyes_closed_count += 1
                    if eyes_closed_count > EYES_CLOSED_THRESHOLD:
                        print("Drowsiness Detected!")
                        lcd.clear()
                        lcd.write_string("Drowsy Detected")
                        lcd.crlf()
                        lcd.write_string(f"HR:{hr} SpO2:{spo2}")
                        normal_mode = False
                        set_led(1, 0, 0)
                        beep_buzzer()
                        pwm.ChangeDutyCycle(0)
                        GPIO.output(BUZZER, 0)
                        delay_active = True
                        threading.Thread(target=delay_recovery).start()

        cv2.imshow("Drowsiness Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Program interrupted by user")

finally:
    pwm.stop()
    GPIO.cleanup()
    cap.release()
    cv2.destroyAllWindows()
    lcd.clear()
