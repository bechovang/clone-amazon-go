## Clone Amazon Go – Vision + Weight Sensor (ESP32 + HX711)

A demo that tracks people with YOLOv8, listens to weight-change events from an ESP32 weight sensor (HX711), and assigns “took item” to the nearest person to the shelf zone. Includes a draggable on-screen shelf zone editor and per-person cart counts.

## Features
- Person tracking with YOLOv8 (ultralytics), persistent IDs per person
- Shelf Zone: draggable/resize UI; press S to save, loads on next run
- MQTT integration with ESP32 scale (HX711); message format: `CHANGE:<grams>`
- Assignment policy: when a weight event arrives, the nearest tracked person to the zone is credited
- Visual highlight: taker’s box turns orange briefly
- Per-person cart count based on weight change and your configured item weight

## Architecture
- PC (Python):
  - `main.py`: camera pipeline, YOLO tracking, draggable zone UI, MQTT client, assignment logic
  - `mqtt_listener.py`: minimal MQTT sample (for testing only)
  - `yolov8n.pt`: YOLO model (nano) used by `main.py`
- ESP32 (MicroPython):
  - `weight_sensor_esp32/`: HX711 driver + Wi-Fi + MQTT publisher for weight changes
  - Publishes to topic `my-shop/shelf-1/events` on `test.mosquitto.org`

## Requirements
- Windows 10/11 or Linux/macOS (Windows: turn off “Studio/Camera effects” like Auto Framing and Background Blur)
- Python 3.9+ recommended
- Webcam
- Internet for MQTT (default uses public broker)
- ESP32 with HX711 (optional if you only simulate MQTT)

Install Python deps:
```bash
python -m venv venv
# Windows PowerShell:
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Quick Start (PC Vision App)
1. Ensure `yolov8n.pt` is in the project root (already included).
2. Configure (optional) in `main.py`:
   - `MQTT_BROKER` (default: `test.mosquitto.org`)
   - `MQTT_TOPIC` (default: `my-shop/shelf-1/events`)
   - `WEIGHT_PER_BOTTLE` (grams per item, default 350)
   - `HIGHLIGHT_DURATION_SEC` (default 2.0s)
3. Run:
```bash
python main.py
```
4. On-screen controls:
   - Drag inside blue rectangle to move the shelf zone
   - Drag corner dots to resize
   - Press `S` to save to `zone_config.json`
   - Press `Q` to quit
5. When a weight decrease event arrives via MQTT (e.g., `CHANGE:-350`):
   - The nearest person to the shelf zone is credited
   - Their box turns orange briefly and their cart count increases

## ESP32 + HX711 Setup (MicroPython)
1. Flash MicroPython to ESP32.
2. Set your Wi-Fi and MQTT settings in:
   - `weight_sensor_esp32/main.py` (or `use_weight.py`)
     - `WIFI_SSID`, `WIFI_PASSWORD`
     - `MQTT_BROKER` (must match PC), `MQTT_TOPIC` (must match PC)
3. Calibrate the scale (optional but recommended):
   - Use `weight_sensor_esp32/calibrate.py` (or your own method) to get:
     - `TARE_VALUE`, `VALUE_WITH_WEIGHT`, and known `KNOWN_WEIGHT_G`
   - Compute:
     - `RATIO = (VALUE_WITH_WEIGHT - TARE_VALUE) / KNOWN_WEIGHT_G`
   - Put those values into ESP32 code:
     - `TARE_VALUE`, `VALUE_WITH_WEIGHT`, `KNOWN_WEIGHT_G`, `RATIO`
4. Deploy files (`hx711.py`, `main.py` or `use_weight.py`) to ESP32 using Thonny/rshell/ampy.
5. Run ESP32 code; it will:
   - Connect to Wi-Fi
   - Connect to MQTT broker
   - Continuously read HX711 and publish when weight changes exceed threshold:
     - Payload: `CHANGE:<grams>` (negative = item taken, positive = put back)

## Simulate Without Hardware
- Using Mosquitto (install separately):
```bash
# Subscribe
mosquitto_sub -h test.mosquitto.org -t my-shop/shelf-1/events

# Publish a “take” event (~350g)
mosquitto_pub -h test.mosquitto.org -t my-shop/shelf-1/events -m "CHANGE:-350"
```
- You should see the nearest person highlighted and their cart increment in the app.

## Configuration Notes
- `main.py`:
  - `MQTT_BROKER`, `MQTT_TOPIC`: must match ESP32 publisher
  - `WEIGHT_PER_BOTTLE`: adjust to your product
  - `HIGHLIGHT_DURATION_SEC`: highlight duration for the taker
- `zone_config.json`:
  - Automatically created/updated by pressing `S` in the app
  - Stores `x`, `y`, `w`, `h` of the shelf zone (pixels)

## Behavior Details
- Person detection/tracking: YOLOv8 (ultralytics) with `model.track(..., persist=True, classes=[0])`
- Assignment on weight event:
  - For each person’s bbox center, compute distance to the shelf zone rectangle (0 if center is inside)
  - Pick nearest person; if weight change < 0, increment their cart by `round(abs(change)/WEIGHT_PER_BOTTLE)`
  - Positive changes (put back) are logged but not subtracted by default (can be enabled)
- Visuals:
  - Shelf zone: blue rectangle with draggable handles
  - Person boxes: green normally, orange for last taker during highlight window
  - Labels show `Person #ID | Cart: N`

## Troubleshooting
- Camera opens but looks zoomed or blurred:
  - On Windows, disable Studio/Camera effects (Auto Framing, Background Blur) via Win+A → Studio effects, or Settings → Bluetooth & devices → Cameras
- Camera won’t open:
  - Close other apps using the camera; try different USB port
  - The app tries multiple backends (CAP_DSHOW/MSMF/VFW) and indices (0/1)
- MQTT not receiving:
  - Check Wi-Fi on ESP32 and broker/topic values
  - Public broker may have rate limits; consider a private broker for production
- Slow FPS:
  - Close other CPU/GPU heavy apps; consider a lower-res camera or faster model

## Project Structure
```
clone-amazon-go/
  main.py                     # Vision app: YOLO tracking + MQTT + zone UI
  mqtt_listener.py            # Simple MQTT listener demo
  yolov8n.pt                  # YOLOv8 nano model
  requirements.txt            # Python dependencies
  .gitignore                  # Git ignore rules
  README.md                   # This file

  weight_sensor_esp32/
    boot.py
    hx711.py                  # MicroPython HX711 driver
    calibrate.py              # Interactive calibration
    main.py                   # ESP32 publisher (Wi-Fi + MQTT + HX711)
    use_weight.py             # Variant publisher
```

## License
Demo/educational use only. Replace public MQTT and tune the pipeline before any real deployment.

---

## Clone Amazon Go – Thị giác máy tính + Cân (ESP32 + HX711)

Demo theo dõi người bằng YOLOv8, lắng nghe sự kiện thay đổi khối lượng từ cân ESP32 (HX711), và gán “lấy hàng” cho người gần vùng kệ nhất. Có UI kéo-thả vùng kệ và đếm số hàng theo từng người.

## Tính năng
- Tracking người bằng YOLOv8 (ultralytics), ID người ổn định theo thời gian
- Vùng kệ: kéo-thả/resize trực tiếp; nhấn S để lưu, tự load khi chạy lại
- MQTT với ESP32 (HX711); định dạng tin: `CHANGE:<grams>`
- Chính sách gán: khi cân báo, gán cho người gần vùng kệ nhất
- Highlight: khung người vừa “lấy hàng” đổi sang màu cam trong thời gian ngắn
- Đếm giỏ theo từng người dựa trên thay đổi khối lượng và trọng lượng chuẩn mỗi mặt hàng

## Kiến trúc
- PC (Python):
  - `main.py`: camera, YOLO, UI zone kéo-thả, MQTT, logic gán
  - `mqtt_listener.py`: ví dụ MQTT tối giản (test)
  - `yolov8n.pt`: model YOLO dùng trong `main.py`
- ESP32 (MicroPython):
  - `weight_sensor_esp32/`: driver HX711 + Wi-Fi + MQTT publisher gửi thay đổi khối lượng
  - Publish tới `my-shop/shelf-1/events` trên `test.mosquitto.org`

## Yêu cầu
- Windows 10/11 hoặc Linux/macOS (Windows: tắt “Studio/Camera effects” như Auto Framing, Background Blur)
- Python 3.9+ khuyến nghị
- Webcam
- Internet cho MQTT (mặc định dùng broker công cộng)
- ESP32 + HX711 (tùy chọn nếu chỉ mô phỏng MQTT)

Cài thư viện Python:
```bash
python -m venv venv
# Windows PowerShell:
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Chạy nhanh (Ứng dụng PC)
1. Đảm bảo `yolov8n.pt` có ở thư mục gốc (đã kèm sẵn).
2. Tuỳ chọn cấu hình trong `main.py`:
   - `MQTT_BROKER` (mặc định: `test.mosquitto.org`)
   - `MQTT_TOPIC` (mặc định: `my-shop/shelf-1/events`)
   - `WEIGHT_PER_BOTTLE` (gram/mặt hàng, mặc định 350)
   - `HIGHLIGHT_DURATION_SEC` (mặc định 2.0s)
3. Chạy:
```bash
python main.py
```
4. Điều khiển trên màn hình:
   - Kéo bên trong khung xanh để di chuyển vùng kệ
   - Kéo các chấm góc để thay đổi kích thước
   - Nhấn `S` để lưu vào `zone_config.json`
   - Nhấn `Q` để thoát
5. Khi nhận được sự kiện giảm khối lượng (ví dụ `CHANGE:-350`):
   - Người gần vùng kệ nhất sẽ được ghi nhận
   - Khung của họ đổi sang màu cam trong chốc lát và giỏ tăng

## Thiết lập ESP32 + HX711 (MicroPython)
1. Nạp MicroPython cho ESP32.
2. Sửa Wi-Fi và MQTT trong:
   - `weight_sensor_esp32/main.py` (hoặc `use_weight.py`)
     - `WIFI_SSID`, `WIFI_PASSWORD`
     - `MQTT_BROKER` (trùng với PC), `MQTT_TOPIC` (trùng với PC)
3. Hiệu chuẩn cân (khuyến nghị):
   - Dùng `weight_sensor_esp32/calibrate.py` (hoặc cách riêng) để lấy:
     - `TARE_VALUE`, `VALUE_WITH_WEIGHT`, và `KNOWN_WEIGHT_G`
   - Tính:
     - `RATIO = (VALUE_WITH_WEIGHT - TARE_VALUE) / KNOWN_WEIGHT_G`
   - Điền các giá trị vào code ESP32:
     - `TARE_VALUE`, `VALUE_WITH_WEIGHT`, `KNOWN_WEIGHT_G`, `RATIO`
4. Upload file (`hx711.py`, `main.py` hoặc `use_weight.py`) lên ESP32 bằng Thonny/rshell/ampy.
5. Chạy code ESP32; thiết bị sẽ:
   - Kết nối Wi-Fi
   - Kết nối MQTT
   - Đọc HX711 và publish khi thay đổi lớn hơn ngưỡng:
     - Payload: `CHANGE:<grams>` (âm = lấy hàng, dương = đặt lại)

## Mô phỏng nếu không có phần cứng
- Dùng Mosquitto (cài riêng):
```bash
# Subscribe
mosquitto_sub -h test.mosquitto.org -t my-shop/shelf-1/events

# Publish sự kiện “lấy hàng” (~350g)
mosquitto_pub -h test.mosquitto.org -t my-shop/shelf-1/events -m "CHANGE:-350"
```
- Ứng dụng sẽ highlight người gần vùng kệ và tăng giỏ của họ.

## Cấu hình
- `main.py`:
  - `MQTT_BROKER`, `MQTT_TOPIC`: trùng với ESP32
  - `WEIGHT_PER_BOTTLE`: chỉnh theo sản phẩm
  - `HIGHLIGHT_DURATION_SEC`: thời lượng tô màu người vừa thao tác
- `zone_config.json`:
  - Tự tạo/cập nhật khi nhấn `S`
  - Lưu `x`, `y`, `w`, `h` của vùng kệ (pixel)

## Chi tiết hoạt động
- Nhận diện/Tracking người: YOLOv8 với `model.track(..., persist=True, classes=[0])`
- Gán khi cân báo:
  - Với tâm bbox của từng người, tính khoảng cách tới vùng kệ (0 nếu tâm nằm trong vùng)
  - Chọn người gần nhất; nếu thay đổi < 0, cộng vào giỏ theo `round(abs(change)/WEIGHT_PER_BOTTLE)`
  - Thay đổi dương (đặt lại) hiện chỉ log, chưa trừ giỏ (có thể bật)
- Hiển thị:
  - Vùng kệ: khung xanh có tay nắm kéo-thả
  - Bbox người: xanh lá bình thường, cam cho người vừa “lấy hàng”
  - Nhãn: `Person #ID | Cart: N`

## Lỗi thường gặp
- Hình bị zoom/làm mờ:
  - Trên Windows, tắt Studio/Camera effects (Auto Framing, Background Blur) ở Win+A → Studio effects hoặc Settings → Bluetooth & devices → Cameras
- Camera không mở:
  - Tắt ứng dụng khác đang dùng camera; đổi cổng USB
  - Ứng dụng tự thử nhiều backend (CAP_DSHOW/MSMF/VFW) và index (0/1)
- MQTT không nhận:
  - Kiểm tra Wi-Fi ESP32 và cấu hình broker/topic
  - Broker công cộng có giới hạn; cân nhắc broker riêng cho production
- FPS thấp:
  - Đóng app nặng; dùng camera độ phân giải thấp hơn hoặc model nhanh hơn

## Cấu trúc dự án
```
clone-amazon-go/
  main.py                     # Vision: YOLO + MQTT + UI zone kéo-thả
  mqtt_listener.py            # Ví dụ MQTT đơn giản (test)
  yolov8n.pt                  # Model YOLOv8 nano
  requirements.txt            # Thư viện Python
  .gitignore                  # Ignored files
  README.md                   # Tài liệu này

  weight_sensor_esp32/
    boot.py
    hx711.py                  # Driver HX711 cho MicroPython
    calibrate.py              # Hiệu chuẩn (lấy TARE/WEIGHT)
    main.py                   # ESP32 publisher (Wi-Fi + MQTT + HX711)
    use_weight.py             # Biến thể publisher (tương tự main.py)
```

## Ghi chú
Dự án mang tính demo. Không dùng broker công cộng cho sản phẩm thực tế; hãy chuyển sang broker riêng và tinh chỉnh pipeline trước khi triển khai.