import RPi.GPIO as GPIO
import cv2
import time
from picamera2 import Picamera2
import numpy as np
import threading

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

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')

picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()

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
    for _ in range(20):
        GPIO.output(BLUE_LED, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(BLUE_LED, GPIO.LOW)
        time.sleep(0.5)

normal_mode = True
delay_active = False
delay_start_time = 0

eyes_closed_count = 0
EYES_CLOSED_THRESHOLD = 10
DELAY_DURATION = 20

def delay_recovery():
    global delay_active, normal_mode, delay_start_time
    delay_start_time = time.time()
    set_led(0, 0, 0)
    blink_blue_led()
    while time.time() - delay_start_time < DELAY_DURATION:
        time.sleep(1)
    frame = picam2.capture_array()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    eyes_open = False
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        if len(eyes) > 0:
            eyes_open = True

    if eyes_open:
        print("Eyes open. Resuming normal mode.")
        set_led(0, 1, 0)
        pwm.ChangeDutyCycle(100)
        delay_active = False
        normal_mode = True
    else:
        print("Still drowsy. Repeating alert.")
        set_led(1, 0, 0)
        beep_buzzer()
        pwm.ChangeDutyCycle(0)
        delay_recovery()  # Recurse if still drowsy

try:
    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        eyes_found = False
        eyes_open = False

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = frame[y:y + h, x:x + w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
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
            else:
                eyes_closed_count += 1
                if eyes_closed_count > EYES_CLOSED_THRESHOLD:
                    print("Drowsiness Detected!")
                    normal_mode = False
                    set_led(1, 0, 0)
                    beep_buzzer()
                    for duty in range(100, -1, -25):
                        pwm.ChangeDutyCycle(duty)
                        time.sleep(0.3)
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
    cv2.destroyAllWindows()
