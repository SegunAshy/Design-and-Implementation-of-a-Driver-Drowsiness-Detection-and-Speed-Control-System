import cv2 
import time
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD

# GPIO pins
RED_LED = 13
GREEN_LED = 18
MOTOR_PIN = 12

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(MOTOR_PIN, GPIO.OUT)

motor_pwm = GPIO.PWM(MOTOR_PIN, 1000)
motor_pwm.start(0)  # Start motor OFF

# LCD setup
lcd = CharLCD('PCF8574', 0x27)
lcd.clear()
lcd.write_string("System Init...")

# Load Haar Cascades
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Camera setup
cam = cv2.VideoCapture(0)
time.sleep(2)

# Counters and thresholds
NO_FACE_LIMIT = 5
EYES_CLOSED_LIMIT = 15
no_face_count = 0
eyes_closed_count = 0
prev_status = None

try:
    while True:
        status =""
        ret, frame = cam.read()
        if not ret:
            print("Camera failed")
            continue

        frame = cv2.resize(frame, (320, 240))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

        if len(faces) >= 1:
            no_face_count = 0
            status = "FACE DETECTED"

            for (x, y, w, h) in faces:
                roi_gray = gray[y:y + h, x:x + w]
                roi_color = frame[y:y + h, x:x + w]
                eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5)

                # Draw rectangle around face and eyes
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (255, 0, 0), 1)

                if len(eyes) == 0:
                    eyes_closed_count += 1
                else:
                    eyes_closed_count = 0

                if eyes_closed_count >= EYES_CLOSED_LIMIT:
                    status = "EYES CLOSED"
                    GPIO.output(RED_LED, GPIO.LOW)
                    GPIO.output(GREEN_LED, GPIO.LOW)
                    motor_pwm.ChangeDutyCycle(0)  # Motor OFF
                else:
                    status = "EYES OPEN"
                    GPIO.output(RED_LED, GPIO.HIGH)
                    GPIO.output(GREEN_LED, GPIO.HIGH)
                    motor_pwm.ChangeDutyCycle(100)  # Motor ON

        else:
            no_face_count += 1
            if no_face_count >= NO_FACE_LIMIT:
                status = "NO FACE"
                GPIO.output(RED_LED, GPIO.LOW)
                GPIO.output(GREEN_LED, GPIO.LOW)
                motor_pwm.ChangeDutyCycle(0)  # Motor OFF

        # LCD status
        if status != prev_status:
            lcd.clear()
            lcd.write_string(f"Status: {status}")
            prev_status = status

        # Status text on video
        cv2.putText(frame, f"Status: {status}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 0, 255) if status in ["NO FACE", "EYES CLOSED"] else (0, 255, 0), 2)

        cv2.imshow("Eye Tracking", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Exiting...")

finally:
    cam.release()
    cv2.destroyAllWindows()
    motor_pwm.stop()
    GPIO.cleanup()
    lcd.clear()
    lcd.write_string("System Off")
