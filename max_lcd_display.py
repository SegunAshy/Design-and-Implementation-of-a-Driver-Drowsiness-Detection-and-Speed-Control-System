from RPLCD.i2c import CharLCD
import max30102
import hrcalc
import time

# === Initialize MAX30102 ===
m = max30102.MAX30102()

# === Initialize I2C LCD (adjust 0x27 if needed) ===
lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
lcd.clear()
lcd.write_string("Initializing...")
time.sleep(2)
lcd.clear()

print("Reading HR and SpO2 from MAX30102... (Press Ctrl+C to stop)")

try:
    while True:
        red, ir = m.read_sequential()

        if red and ir:
            # Calculate HR and SpO2
            hr, hr_valid, spo2, spo2_valid = hrcalc.calc_hr_and_spo2(ir, red)

            lcd.clear()

            if hr_valid:
                hr_text = f"HR: {int(hr)} bpm"
                print(hr_text)
            else:
                hr_text = "HR: ---"
                print("Heart rate not valid")

            if spo2_valid:
                spo2_text = f"SpO2: {int(spo2)}%"
                print(spo2_text)
            else:
                spo2_text = "SpO2: ---"
                print("SpO2 not valid")

            # Display on LCD
            lcd.write_string(hr_text)
            lcd.cursor_pos = (1, 0)
            lcd.write_string(spo2_text)

            print("-" * 40)
            time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    lcd.clear()
    lcd.write_string("Goodbye :)")
    time.sleep(2)
    lcd.clear()
