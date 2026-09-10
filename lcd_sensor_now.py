from RPLCD.i2c import CharLCD
import max30102
import hrcalc
import time

# Initialize LCD (change address if needed using i2cdetect -y 1)
lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
lcd.clear()
lcd.write_string("Initializing...")
time.sleep(1)
lcd.clear()

# Initialize MAX30102 sensor
sensor = max30102.MAX30102()
time.sleep(1)

print("Starting to read Heart Rate and SpO2...")

try:
    while True:
        # Read raw data from sensor
        red, ir = sensor.read_sequential()

        if red and ir:
            # Calculate heart rate and SpO2
            hr, hr_valid, spo2, spo2_valid = hrcalc.calc_hr_and_spo2(ir, red)

            lcd.clear()

            if hr_valid:
                hr_text = f"HR: {int(hr)} bpm"
            else:
                hr_text = "HR: ---"

            if spo2_valid:
                spo2_text = f"SpO2: {int(spo2)}%"
            else:
                spo2_text = "SpO2: ---"

            # Show on LCD
            lcd.write_string(hr_text)
            lcd.cursor_pos = (1, 0)
            lcd.write_string(spo2_text)

            # Debug print to terminal
            print(hr_text)
            print(spo2_text)
            print("-" * 30)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped by user.")
    lcd.clear()
    lcd.write_string("Goodbye :)")
    time.sleep(2)
    lcd.clear()
