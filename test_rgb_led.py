import RPi.GPIO as GPIO
import time

RED = 19
GREEN = 18
BLUE = 12

GPIO.setmode(GPIO.BCM)
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)

def light_led(r, g, b):
    GPIO.output(RED, r)
    GPIO.output(GREEN, g)
    GPIO.output(BLUE, b)

try:
    print("Red ON")
    light_led(1, 0, 0)
    time.sleep(2)

    print("Green ON")
    light_led(0, 1, 0)
    time.sleep(2)

    print("Blue ON")
    light_led(0, 0, 1)
    time.sleep(2)

    print("White (all ON)")
    light_led(1, 1, 1)
    time.sleep(2)

    print("OFF")
    light_led(0, 0, 0)

finally:
    GPIO.cleanup()
