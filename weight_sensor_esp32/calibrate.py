# File: calibrate.py
from machine import Pin
from hx711 import HX711
import time

# Cấu hình chân kết nối
DT_PIN = 25   # ESP32 GPIO 25 → HX711 DT (DOUT)
SCK_PIN = 26  # ESP32 GPIO 26 → HX711 SCK (PD_SCK)

# Khởi tạo HX711
hx = HX711(d_out=DT_PIN, pd_sck=SCK_PIN)

print("🔧 BẮT ĐẦU HIỆU CHUẨN CÂN")
print("Đang khởi tạo... Đợi 3 giây")
time.sleep(3)

# BƯỚC 1: Đo giá trị khi không có gì trên cân
print("\n" + "="*40)
print("BƯỚC 1: ĐẢM BẢO CÂN TRỐNG!")
print("Nhấn Enter khi cân đã trống...")
input()

tare_readings = []
for i in range(5):
    reading = hx.read()
    tare_readings.append(reading)
    print(f"Lần đo {i+1}: {reading}")
    time.sleep(1)

tare_value = sum(tare_readings) // len(tare_readings)
print(f"📝 GIÁ TRỊ BÌ (TARE): {tare_value}")

# BƯỚC 2: Đo giá trị khi có vật chuẩn
print("\n" + "="*40)
print("BƯỚC 2: ĐẶT VẬT CHUẨN LÊN CÂN!")
print("Vật chuẩn có thể là:")
print("- Chai nước 500ml = 500g")
print("- Lon nước ngọt = 330g") 
print("- Gói đường 1kg = 1000g")
print("- Hoặc bất kỳ vật nào bạn biết chính xác khối lượng")
print("\nNhấn Enter khi đã đặt vật lên cân...")
input()

weight_readings = []
for i in range(5):
    reading = hx.read()
    weight_readings.append(reading)
    print(f"Lần đo {i+1}: {reading}")
    time.sleep(1)

weight_value = sum(weight_readings) // len(weight_readings)
print(f"📝 GIÁ TRỊ KHI CÓ VẬT: {weight_value}")

print("\n" + "="*50)
print("✅ HIỆU CHUẨN HOÀN TẤT!")
print("Ghi lại 2 giá trị sau để dùng cho bước tiếp theo:")
print(f"TARE_VALUE = {tare_value}")
print(f"VALUE_WITH_WEIGHT = {weight_value}")
print("="*50)
