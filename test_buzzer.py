import RPi.GPIO as GPIO
import time

BUZZER = 4

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER, GPIO.OUT)

try:
    print("Buzzer ON")
    GPIO.output(BUZZER, GPIO.HIGH)
    time.sleep(1)

    print("Buzzer OFF")
    GPIO.output(BUZZER, GPIO.LOW)
    time.sleep(1)

    print("Buzzer Beeping 3x")
    for _ in range(3):
        GPIO.output(BUZZER, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(BUZZER, GPIO.LOW)
        time.sleep(0.2)

finally:
    GPIO.cleanup()
