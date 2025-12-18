## ESP32 HX711 Scale over Wi‑Fi + MQTT (No Vision)

This project uses an ESP32 with an HX711 load cell amplifier to detect weight changes and publish them over MQTT. Vision (YOLO/OpenCV) has been removed per request.

### What it does
- Reads weight from a load cell via HX711 on ESP32
- Connects ESP32 to Wi‑Fi and publishes `CHANGE:<grams>` to MQTT when weight changes exceed a threshold
- Includes a MicroPython HX711 driver and ready-to-run publisher
- Optional: a PC-side `mqtt_listener.py` to observe messages

---

## Wiring Guide (Detailed)

### 1) HX711 to ESP32 (logic)
Default pins used by the code (`weight_sensor_esp32/main.py`):
- ESP32 `3V3`  → HX711 `VCC`
- ESP32 `GND`  → HX711 `GND`
- ESP32 `GPIO 25` → HX711 `DT` (a.k.a. `DOUT`)
- ESP32 `GPIO 26` → HX711 `SCK` (a.k.a. `PD_SCK`)

Notes:
- Keep wires short and stable to reduce noise.
- Some HX711 boards label pins as `DT/SCK` or `DOUT/PD_SCK` — they are equivalent.
- Power the HX711 from 3.3V (ESP32 logic level).

### 2) Load Cell to HX711 (excitation/signal)
Typical 4-wire load cell:
- Red   → HX711 `E+` (Excitation +)
- Black → HX711 `E-` (Excitation -)
- White → HX711 `A-` (Signal -)
- Green → HX711 `A+` (Signal +)

If wire colors differ, consult your load cell’s datasheet:
- `E+`/`E-` power the load cell bridge
- `A+`/`A-` are the sense/signal lines

---

## ESP32 Firmware (MicroPython)

Files under `weight_sensor_esp32/`:
- `hx711.py`: HX711 MicroPython driver
- `main.py`: Publisher (Wi‑Fi + MQTT + HX711) - **Main script to run**
- `calibrate.py`: Interactive calibration helper (run via Thonny/MicroPython IDE)
- `boot.py`: Optional boot script

### Configure Wi‑Fi/MQTT
Edit in `weight_sensor_esp32/main.py`:
- `WIFI_SSID`, `WIFI_PASSWORD`
- `MQTT_BROKER` (default: `test.mosquitto.org`)
- `MQTT_CLIENT_ID` (any unique string)
- `MQTT_TOPIC` (default: `my-shop/shelf-1/events`)

### Calibration
1. Open `calibrate.py` on the ESP32 via Thonny (or a MicroPython IDE).
2. Run it, follow prompts:
   - Measure empty scale (TARE)
   - Place known weight (e.g., 500g or 1000g) and measure
3. The script prints:
   - `TARE_VALUE`
   - `VALUE_WITH_WEIGHT`
   - Put them (and your `KNOWN_WEIGHT_G`) into `main.py` and compute:
     - `RATIO = (VALUE_WITH_WEIGHT - TARE_VALUE) / KNOWN_WEIGHT_G`
4. Save and run `main.py` on the ESP32.

### Publishing Logic
- Reads stable weight (median of multiple samples).
- Computes `weight_change = current_weight - last_known_weight`.
- If `abs(weight_change) > WEIGHT_CHANGE_THRESHOLD` (default 50 g):
  - Publishes MQTT payload: `CHANGE:<grams>` (rounded)
  - Negative = item taken off the scale; Positive = item placed back
  - Updates `last_known_weight` and waits briefly to avoid spam

---

## PC-Side MQTT (Optional)

Python requirements:
```
paho-mqtt
```

Install:
```bash
python -m venv venv
venv\Scripts\Activate.ps1   # on Windows PowerShell
pip install -r requirements.txt
```

Run a local listener:
```bash
python mqtt_listener.py
```
You should see messages like:
```
📬 Nhận được tin nhắn: 'CHANGE:-350' từ topic 'my-shop/shelf-1/events'
```

Or use Mosquitto (if installed) to subscribe:
```bash
mosquitto_sub -h test.mosquitto.org -t my-shop/shelf-1/events
```

---

## Project Structure
```
clone-amazon-go/
  mqtt_listener.py            # Optional PC-side MQTT listener
  requirements.txt            # Only paho-mqtt now
  .gitignore
  README.md                   # This guide

  weight_sensor_esp32/
    boot.py                   # Optional boot script
    hx711.py                  # MicroPython HX711 driver
    calibrate.py              # Interactive calibration (get TARE/WEIGHT values)
    main.py                   # ESP32 publisher (Wi‑Fi + MQTT + HX711) - Main script
```

---

## Troubleshooting
- No MQTT messages:
  - Verify ESP32 Wi‑Fi SSID/password
  - Check MQTT broker, topic spelling
  - Public brokers may be unstable; use a private broker for production
- Noisy readings / frequent triggers:
  - Improve mechanical mounting and cable management
  - Increase sample count or threshold in code
  - Add small delay between publishes (already present)
- Wrong weight after power cycle:
  - Recheck calibration values (`TARE_VALUE`, `VALUE_WITH_WEIGHT`, `KNOWN_WEIGHT_G`, `RATIO`)

---

## License
Demo/educational use only. Replace the public MQTT broker and harden the setup for real deployments.