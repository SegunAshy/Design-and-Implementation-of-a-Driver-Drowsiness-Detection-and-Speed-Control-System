import RPi.GPIO as GPIO
import time

MOTOR_PWM = 13

GPIO.setmode(GPIO.BCM)
GPIO.setup(MOTOR_PWM, GPIO.OUT)

pwm = GPIO.PWM(MOTOR_PWM, 1000)  # 1 kHz frequency
pwm.start(100)  # Full speed (100% duty)

try:
    print("Motor running at full speed...")
    time.sleep(2)

    print("Slowing down...")
    for duty in range(100, -1, -20):  # 100 → 0 in steps of 20
        pwm.ChangeDutyCycle(duty)
        print(f"Speed: {duty}%")
        time.sleep(1)

    print("Motor OFF")
    pwm.ChangeDutyCycle(0)
    time.sleep(1)

finally:
    pwm.stop()
    GPIO.cleanup()
