# ================== CÁC THƯ VIỆN CẦN THIẾT ==================
from machine import Pin
from hx711 import HX711
import time
import network
from umqtt.simple import MQTTClient

# ================== CẤU HÌNH MẠNG VÀ MQTT ==================
WIFI_SSID = "thinkbook 14 g7+"         # <-- ĐÃ SỬA THEO HÌNH CỦA BẠN
WIFI_PASSWORD = "12345678"             # <-- ĐÃ SỬA THEO HÌNH CỦA BẠN

MQTT_BROKER = "test.mosquitto.org" # Dùng broker công cộng để test
MQTT_CLIENT_ID = "esp32-shelf-1"   # Đặt tên riêng cho thiết bị của bạn
MQTT_TOPIC = "my-shop/shelf-1/events" # Chủ đề để gửi dữ liệu

# ================== CẤU HÌNH CHÂN (Giữ nguyên) ==================
DT_PIN = 25
SCK_PIN = 26

# ================== GIÁ TRỊ HIỆU CHUẨN (Giữ nguyên) ==================
TARE_VALUE = 477803
VALUE_WITH_WEIGHT = 328882
KNOWN_WEIGHT_G = 350
RATIO = (VALUE_WITH_WEIGHT - TARE_VALUE) / KNOWN_WEIGHT_G

# ================== KHỞI TẠO CẢM BIẾN (Giữ nguyên) ==================
hx = HX711(d_out=DT_PIN, pd_sck=SCK_PIN)
print("🚀 Khởi động cân...")
time.sleep(1)

# ================== KẾT NỐI WIFI ==================
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print(f"📡 Đang kết nối tới Wi-Fi: {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
print(f"✅ Đã kết nối Wi-Fi! IP: {wlan.ifconfig()[0]}")

# ================== KẾT NỐI MQTT BROKER ==================
print(f"🧠 Đang kết nối tới MQTT Broker: {MQTT_BROKER}...")
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
client.connect()
print("✅ Đã kết nối MQTT Broker!")

# ================== CÁC HÀM XỬ LÝ (Giữ nguyên) ==================
def read_weight_stable(samples=10):
    readings = []
    # Bỏ qua vài lần đọc đầu tiên có thể không ổn định
    for _ in range(3):
        hx.read()
        time.sleep_ms(10)
        
    for _ in range(samples):
        readings.append(hx.read())
        time.sleep_ms(10)
    return sorted(readings)[len(readings) // 2]

def convert_to_weight(reading):
    return (reading - TARE_VALUE) / RATIO

# ================== VÒNG LẶP CHÍNH ĐÃ NÂNG CẤP ==================
last_known_weight = 0
WEIGHT_CHANGE_THRESHOLD = 50  # Chỉ gửi tín hiệu nếu trọng lượng thay đổi > 50g

# Đọc khối lượng ban đầu để làm mốc so sánh
initial_raw = read_weight_stable()
last_known_weight = convert_to_weight(initial_raw)
print(f"⚖️  Khối lượng ban đầu ổn định: {last_known_weight:.1f} g")

while True:
    try:
        raw = read_weight_stable()
        current_weight = convert_to_weight(raw)
        
        weight_change = current_weight - last_known_weight
        
        # KIỂM TRA SỰ THAY ĐỔI ĐÁNG KỂ
        if abs(weight_change) > WEIGHT_CHANGE_THRESHOLD:
            # Làm tròn giá trị thay đổi
            change_to_report = round(weight_change)
            
            print(f"❗ Phát hiện thay đổi: {change_to_report} g. Đang gửi tín hiệu...")
            
            # Tạo payload và gửi qua MQTT
            payload = f"CHANGE:{change_to_report}"
            client.publish(MQTT_TOPIC, payload)
            
            print(f"✅ Đã gửi: '{payload}' tới topic '{MQTT_TOPIC}'")
            
            # Cập nhật lại khối lượng đã biết để so sánh cho lần sau
            last_known_weight = current_weight
            
            # Chờ một chút để tránh gửi liên tục
            time.sleep(2) 
            
    except Exception as e:
        print(f"Lỗi: {e}. Đang thử kết nối lại...")
        # Nếu có lỗi (mất kết nối...), thử kết nối lại
        time.sleep(5)
        try:
            client.connect()
        except:
            print("Kết nối lại thất bại.")

    time.sleep(0.2) # Giảm tần suất đọc để hệ thống ổn định

