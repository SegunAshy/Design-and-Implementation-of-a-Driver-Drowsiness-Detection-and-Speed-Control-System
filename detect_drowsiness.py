import RPi.GPIO as GPIO
import cv2
import time
from picamera2 import Picamera2
import numpy as np

# Setup GPIO
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

# Camera setup
picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()

# Helper to set LED state
def set_led(r, g, b):
    GPIO.output(RED_LED, r)
    GPIO.output(GREEN_LED, g)
    GPIO.output(BLUE_LED, b)

# Helper to blink Blue LED when searching for a face
def blink_blue_led():
    for _ in range(5):  # Blink Blue LED 5 times
        GPIO.output(BLUE_LED, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(BLUE_LED, GPIO.LOW)
        time.sleep(0.5)

# Drowsiness tracking
normal_mode = True
last_eye_time = time.time()

# Helper function for buzzer beep sequence
def beep_buzzer():
    for _ in range(5):  # Beep 5 times
        GPIO.output(BUZZER, GPIO.HIGH)
        time.sleep(0.3)
        GPIO.output(BUZZER, GPIO.LOW)
        time.sleep(0.3)

# Check if we are running in desktop mode
desktop_mode = True  # Change this to False for embedded mode

try:
    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        eyes_found = False
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) > 0:
                eyes_found = True
                break  # One pair of eyes is enough

        if len(faces) == 0:  # No face detected
            print("Searching for face... Blue LED blinking.")
            blink_blue_led()  # Blink blue LED while searching for face
            set_led(0, 0, 1)  # Blue LED on while searching
        else:  # Face detected
            print("Face detected. Blue LED off.")
            set_led(0, 1, 0)  # Green LED on when face is detected
            
            if normal_mode:
                if eyes_found:
                    GPIO.output(BUZZER, 0)  # Buzzer off
                    pwm.ChangeDutyCycle(100)  # Motor full speed
                    last_eye_time = time.time()
                else:  # Eyes closed
                    if time.time() - last_eye_time > 5:
                        print("Drowsiness Detected!")
                        normal_mode = False
                        set_led(1, 0, 0)  # Red LED on for drowsiness
                        beep_buzzer()  # Start buzzer beep sequence
                        for duty in range(100, -1, -25):  # Gradually reduce motor speed
                            pwm.ChangeDutyCycle(duty)
                            time.sleep(0.3)
                        pwm.ChangeDutyCycle(0)  # Motor off
                        time.sleep(5)  # Wait for 5 seconds for drowsiness alert
            else:  # Drowsiness alert, waiting 20 seconds
                set_led(0, 0, 1)  # Blue LED on while waiting
                print("Waiting 20s...")
                time.sleep(20)

                frame = picam2.capture_array()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)

                eyes_open = False
                for (x, y, w, h) in faces:
                    roi_gray = gray[y:y+h, x:x+w]
                    eyes = eye_cascade.detectMultiScale(roi_gray)
                    if len(eyes) > 0:
                        eyes_open = True
                        break

                if eyes_open:
                    print("Eyes open. Resuming normal mode.")
                    normal_mode = True
                    set_led(0, 1, 0)  # Green LED on
                    GPIO.output(BUZZER, 0)  # Buzzer off
                    pwm.ChangeDutyCycle(100)  # Motor full speed
                    last_eye_time = time.time()
                else:
                    print("Still drowsy. Repeating alarm and 20s delay.")
                    set_led(1, 0, 0)  # Red LED on
                    GPIO.output(BUZZER, 1)  # Buzzer on
                    pwm.ChangeDutyCycle(0)  # Motor off
                    time.sleep(1)
                    GPIO.output(BUZZER, 0)  # Buzzer off

        # Desktop Mode - Show live face detection and eye status
        if desktop_mode:
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            if eyes_found:
                cv2.putText(frame, 'Eyes Open', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, 'Eyes Closed', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            cv2.imshow("Drowsiness Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break  # Press 'q' to exit desktop mode

except KeyboardInterrupt:
    print("Program terminated by user.")

finally:
    pwm.stop()
    GPIO.cleanup()
    cv2.destroyAllWindows()

