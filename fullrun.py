# Combined Drowsiness + Heart Rate Detection with LCD, Buzzer, Motor
# Compatible with USB camera and MAX30102, displays to I2C LCD

import cv2
import time
import threading
import numpy as np
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD
import max30102
import hrcalc

# ========== GPIO SETUP ==========
GPIO.setmode(GPIO.BCM)
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
pwm.start(100)

# ========== LCD SETUP ==========
lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
lcd.clear()
lcd.write_string("Initializing...")
time.sleep(1)
lcd.clear()

# ========== SENSOR SETUP ==========
sensor = max30102.MAX30102()
time.sleep(1)  # Let sensor stabilize

# ========== CAMERA SETUP ==========
cap = cv2.VideoCapture(0)  # USB Camera
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# ========== CONSTANTS ==========
EYES_CLOSED_THRESHOLD = 10
DELAY_DURATION = 20
HEART_RATE_MIN = 50

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
    for _ in range(6):
        GPIO.output(BLUE_LED, GPIO.HIGH)
        time.sleep(0.3)
        GPIO.output(BLUE_LED, GPIO.LOW)
        time.sleep(0.3)

def delay_recovery():
    global normal_mode, delay_active
    delay_start = time.time()
    set_led(0, 0, 0)
    blink_blue_led()
    while time.time() - delay_start < DELAY_DURATION:
        time.sleep(1)

    _, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    eyes_open = False
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        if len(eyes) > 0:
            eyes_open = True

    if eyes_open:
        print("Eyes open. Resuming.")
        lcd.clear()
        lcd.write_string("Eyes Open")
        set_led(0, 1, 0)
        pwm.ChangeDutyCycle(100)
        delay_active = False
        normal_mode = True
    else:
        print("Still drowsy. Repeating.")
        lcd.clear()
        lcd.write_string("Still Drowsy")
        set_led(1, 0, 0)
        beep_buzzer()
        pwm.ChangeDutyCycle(0)
        delay_recovery()

normal_mode = True
delay_active = False
eyes_closed_count = 0

try:
    while True:
        # === Get Camera Frame ===
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        eyes_found = False
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) > 0:
                eyes_found = True

        # === Get Heart Rate ===
        red, ir = sensor.read_sequential()
        hr, hr_valid, spo2, spo2_valid = hrcalc.calc_hr_and_spo2(ir, red)

        # === Display on LCD ===
        lcd.clear()
        if hr_valid:
            lcd.write_string(f"HR: {int(hr)}bpm")
        else:
            lcd.write_string("HR: ---")

        lcd.cursor_pos = (1, 0)
        if spo2_valid:
            lcd.write_string(f"SpO2: {int(spo2)}%")
        else:
            lcd.write_string("SpO2: ---")

        # === Terminal Debug ===
        print(f"HR: {int(hr) if hr_valid else '---'} bpm")
        print(f"SpO2: {int(spo2) if spo2_valid else '---'} %")
        print(f"Eyes Found: {eyes_found}")
        print("-"*30)

        # === Main Logic ===
        if normal_mode:
            if eyes_found and hr_valid and hr > HEART_RATE_MIN:
                eyes_closed_count = 0
                set_led(0, 1, 0)
                GPIO.output(BUZZER, 0)
                pwm.ChangeDutyCycle(100)
            else:
                eyes_closed_count += 1
                if eyes_closed_count > EYES_CLOSED_THRESHOLD or (hr_valid and hr < HEART_RATE_MIN):
                    print("Drowsiness or low HR detected!")
                    lcd.clear()
                    lcd.write_string("ALERT!")
                    set_led(1, 0, 0)
                    beep_buzzer()
                    pwm.ChangeDutyCycle(0)
                    GPIO.output(BUZZER, 0)
                    normal_mode = False
                    delay_active = True
                    threading.Thread(target=delay_recovery).start()

        # Optional display (if not headless)
        cv2.imshow("Frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Interrupted by user")

finally:
    pwm.stop()
    GPIO.cleanup()
    cap.release()
    cv2.destroyAllWindows()
    lcd.clear()
