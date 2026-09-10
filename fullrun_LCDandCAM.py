import RPi.GPIO as GPIO
import cv2
import time
import numpy as np
import threading
from RPLCD.i2c import CharLCD

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

pwm = GPIO.PWM(MOTOR_PWM, 100)  # Lower frequency for better motor response
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
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

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

try:
    last_motor_start_time = 0
    motor_running = False
    eyes_open_prev = False

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        eyes_open = False

        if len(faces) == 0:
            print("Face not detected")
            lcd.clear()
            lcd.write_string("Face Not Found")
            set_led(0, 0, 1)
            pwm.ChangeDutyCycle(0)
            GPIO.output(BUZZER, 0)
            motor_running = False
        else:
            for (x, y, w, h) in faces:
                roi_gray = gray[y:y + h, x:x + w]
                roi_color = frame[y:y + h, x:x + w]
                eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.05, minNeighbors=15, minSize=(20, 20))
                if len(eyes) > 0:
                    eyes_open = True
                    for (ex, ey, ew, eh) in eyes:
                        cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

            current_time = time.time()

            if eyes_open:
                if not motor_running:
                    GPIO.output(BUZZER, GPIO.HIGH)
                    time.sleep(0.5)
                    GPIO.output(BUZZER, GPIO.LOW)
    print("Eyes detected: Motor ON")
                    lcd.clear()
                    lcd.write_string("Eyes: Open")
                    set_led(0, 1, 0)
                    pwm.ChangeDutyCycle(100)
                    last_motor_start_time = current_time
                    motor_running = True

            if motor_running and (current_time - last_motor_start_time >= 10):
                print("Motor ran 10s. Checking eyes again")
                if not eyes_open:
                    lcd.clear()
                    lcd.write_string("Eyes: Closed")
                    set_led(1, 0, 0)
                    pwm.ChangeDutyCycle(0)
                    motor_running = False

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
