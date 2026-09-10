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
motor_pwm.start(100)

# LCD setup
lcd = CharLCD('PCF8574', 0x27)  # Use your LCD I2C address if different
lcd.clear()
lcd.write_string("System Init...")

# Face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
cam = cv2.VideoCapture(0)
time.sleep(2)

# Variables
NO_FACE_LIMIT = 5
no_face_count = 0
prev_status = None

try:
    while True:
        ret, frame = cam.read()
        if not ret:
            print("Camera failed")
            continue

        # Resize and grayscale
        frame = cv2.resize(frame, (320, 240))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Face detection
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

        if len(faces) == 0:
            no_face_count += 1
        else:
            no_face_count = 0

        # Determine status
        if no_face_count >= NO_FACE_LIMIT:
            status = "DROWSY"
            GPIO.output(RED_LED, GPIO.HIGH)
            GPIO.output(GREEN_LED, GPIO.LOW)
            motor_pwm.ChangeDutyCycle(0)
        else:
            status = "OK"
            GPIO.output(RED_LED, GPIO.LOW)
            GPIO.output(GREEN_LED, GPIO.HIGH)
            motor_pwm.ChangeDutyCycle(100)

        # Update LCD on status change
        if status != prev_status:
            lcd.clear()
            lcd.write_string(f"Status: {status}")
            prev_status = status

        # Draw rectangles around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Display status on frame
        cv2.putText(frame, f"Status: {status}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 0, 255) if status == "DROWSY" else (0, 255, 0), 2)

        # Show video
        cv2.imshow("Drowsiness Detection", frame)

        # Exit on 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Stopping...")

finally:
    cam.release()
    cv2.destroyAllWindows()
    motor_pwm.stop()
    GPIO.cleanup()
    lcd.clear()
    lcd.write_string("System Off")
