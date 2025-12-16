## Cân ESP32 HX711 qua Wi‑Fi + MQTT (Không dùng Vision)

Dự án dùng ESP32 + HX711 để đọc khối lượng và publish sự kiện qua MQTT với payload `CHANGE:<grams>`. Phần thị giác máy tính (YOLO/OpenCV) đã được loại bỏ theo yêu cầu.

---

## Tính năng
- Đọc cân từ load cell qua HX711 trên ESP32
- Kết nối Wi‑Fi và publish MQTT khi khối lượng thay đổi vượt ngưỡng
- Định dạng tin nhắn: `CHANGE:<grams>` (âm = lấy vật ra; dương = đặt vật vào)
- Có sẵn driver HX711 (MicroPython) và script publish mẫu
- Tùy chọn: script trên PC `mqtt_listener.py` để xem tin nhắn

---

## Sơ đồ đấu dây chi tiết

### 1) Nối HX711 ↔ ESP32 (logic)
Các chân mặc định trong `weight_sensor_esp32/main.py` (và `use_weight.py`):
- ESP32 `3V3`  → HX711 `VCC`
- ESP32 `GND`  → HX711 `GND`
- ESP32 `GPIO25` → HX711 `DT` (hoặc `DOUT`)
- ESP32 `GPIO26` → HX711 `SCK` (hoặc `PD_SCK`)

Ghi chú:
- Dây càng ngắn càng ổn định, tránh nhiễu.
- Một số board HX711 in nhãn `DT/SCK` hoặc `DOUT/PD_SCK` (tương đương).
- HX711 hoạt động 3.3V phù hợp với ESP32.

### 2) Nối Load Cell ↔ HX711 (nguồn/signal)
Với load cell 4 dây thường gặp:
- Đỏ   → HX711 `E+` (nguồn + cho cầu đo)
- Đen  → HX711 `E-` (nguồn -)
- Trắng → HX711 `A-` (tín hiệu -)
- Xanh lá → HX711 `A+` (tín hiệu +)

Nếu màu dây khác, hãy xem datasheet của load cell:
- `E+`/`E-`: cấp nguồn cho cầu đo
- `A+`/`A-`: cặp tín hiệu cảm biến

---

## Firmware cho ESP32 (MicroPython)

Thư mục `weight_sensor_esp32/`:
- `hx711.py`: driver HX711 cho MicroPython
- `main.py`: publisher (Wi‑Fi + MQTT + HX711)
- `use_weight.py`: biến thể publisher (tương tự `main.py`)
- `calibrate.py`: hỗ trợ hiệu chuẩn (chạy qua Thonny, nhập liệu)
- `boot.py`: script chạy khi boot (tùy chọn)

### Cấu hình Wi‑Fi/MQTT
Sửa trong `weight_sensor_esp32/main.py` (hoặc `use_weight.py`):
- `WIFI_SSID`, `WIFI_PASSWORD`
- `MQTT_BROKER` (mặc định: `test.mosquitto.org`)
- `MQTT_CLIENT_ID` (chuỗi duy nhất)
- `MQTT_TOPIC` (mặc định: `my-shop/shelf-1/events`)

### Hiệu chuẩn cân
1) Mở `calibrate.py` trên ESP32 (Thonny/IDE MicroPython) và chạy.
2) Làm theo hướng dẫn:
   - Đo khi cân trống (TARE)
   - Đặt vật chuẩn (vd 500g/1000g) và đo
3) Script in ra:
   - `TARE_VALUE`
   - `VALUE_WITH_WEIGHT`
4) Tính:
   - `RATIO = (VALUE_WITH_WEIGHT - TARE_VALUE) / KNOWN_WEIGHT_G`
5) Ghi các giá trị vào `main.py`/`use_weight.py` (các hằng `TARE_VALUE`, `VALUE_WITH_WEIGHT`, `KNOWN_WEIGHT_G`, `RATIO`) rồi chạy.

### Logic publish
- Đọc nhiều mẫu và lấy median để ổn định.
- `weight_change = current_weight - last_known_weight`.
- Nếu `abs(weight_change) > WEIGHT_CHANGE_THRESHOLD` (mặc định 50g):
  - Publish: `CHANGE:<grams>` (làm tròn số)
  - Giá trị âm: lấy bớt vật khỏi cân; dương: đặt thêm vật lên cân
  - Cập nhật `last_known_weight` và chờ ngắn để tránh spam.

---

## Theo dõi MQTT trên PC (tùy chọn)

Yêu cầu Python:
```
paho-mqtt
```

Cài đặt:
```bash
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

Chạy listener đơn giản:
```bash
python mqtt_listener.py
```
Kỳ vọng output ví dụ:
```
📬 Nhận được tin nhắn: 'CHANGE:-350' từ topic 'my-shop/shelf-1/events'
```

Hoặc dùng Mosquitto (nếu đã cài):
```bash
mosquitto_sub -h test.mosquitto.org -t my-shop/shelf-1/events
```

---

## Cấu trúc dự án
```
clone-amazon-go/
  mqtt_listener.py            # Script PC xem tin MQTT (tùy chọn)
  requirements.txt            # Hiện chỉ còn paho-mqtt
  .gitignore
  README.md                   # Tài liệu tiếng Anh
  README.vie.md               # Tài liệu tiếng Việt (file này)

  weight_sensor_esp32/
    boot.py
    hx711.py                  # Driver HX711 cho MicroPython
    calibrate.py              # Hiệu chuẩn (lấy TARE/WEIGHT)
    main.py                   # ESP32 publisher (Wi‑Fi + MQTT + HX711)
    use_weight.py             # Biến thể publisher
```

---

## Lỗi thường gặp & cách xử lý
- Không thấy tin MQTT:
  - Kiểm tra SSID/mật khẩu Wi‑Fi cho ESP32
  - Kiểm tra địa chỉ broker, tên topic
  - Broker công cộng có thể quá tải; nên dùng broker riêng cho sản phẩm thật
- Đọc nhiễu/trigger liên tục:
  - Gắn cơ khí chắc chắn, đi dây gọn gàng
  - Tăng số mẫu đọc/trung vị hoặc tăng ngưỡng `WEIGHT_CHANGE_THRESHOLD`
  - Giữ độ trễ giữa các lần publish (đã có sẵn)
- Sai số sau mỗi lần bật lại:
  - Kiểm tra lại giá trị hiệu chuẩn (`TARE_VALUE`, `VALUE_WITH_WEIGHT`, `KNOWN_WEIGHT_G`, `RATIO`)

---

## Giấy phép
Dự án phục vụ mục đích demo/học tập. Khi triển khai thực tế, hãy dùng broker riêng và gia cố đầy đủ (cả phần cứng lẫn phần mềm).


