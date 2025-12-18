# ================== CÁC THƯ VIỆN CẦN THIẾT ==================
from machine import Pin
from hx711 import HX711
import time
import network
from umqtt.simple import MQTTClient

# ================== CẤU HÌNH MẠNG VÀ MQTT ==================
WIFI_SSID = "Hshop Guest"
WIFI_PASSWORD = "dienturobot"

MQTT_BROKER = "test.mosquitto.org" # Dùng broker công cộng để test
MQTT_CLIENT_ID = "esp32-shelf-1"   # Đặt tên riêng cho thiết bị của bạn
MQTT_TOPIC = "my-shop/shelf-1/events" # Chủ đề để gửi dữ liệu

# ================== CẤU HÌNH CHÂN ==================
DT_PIN = 25   # ESP32 GPIO 25 → HX711 DT (DOUT)
SCK_PIN = 26  # ESP32 GPIO 26 → HX711 SCK (PD_SCK)

# ================== GIÁ TRỊ HIỆU CHUẨN (Cập nhật theo đo của bạn) ==================
TARE_VALUE = 471778
VALUE_WITH_WEIGHT = 256326
KNOWN_WEIGHT_G = 480
# Có thể để công thức hoặc dùng giá trị số trực tiếp:
RATIO = (VALUE_WITH_WEIGHT - TARE_VALUE) / KNOWN_WEIGHT_G
#RATIO = -452.4

# ================== KHỞI TẠO CẢM BIẾN ==================
print("🚀 Khởi động cân...")
print(f"📌 Cấu hình chân: DT={DT_PIN}, SCK={SCK_PIN}")
hx = HX711(d_out=DT_PIN, pd_sck=SCK_PIN)
time.sleep(1)

# Test đọc HX711 ngay sau khi khởi tạo
print("🔍 Đang test đọc HX711...")
test_readings = []
for i in range(5):
    try:
        val = hx.read()
        test_readings.append(val)
        print(f"   Lần {i+1}: {val}")
    except Exception as e:
        print(f"   ❌ Lỗi đọc lần {i+1}: {e}")
    time.sleep(0.1)

if all(r == 0 for r in test_readings):
    print("⚠️  CẢNH BÁO: Tất cả giá trị đọc đều = 0!")
    print("💡 Kiểm tra:")
    print("   1. Dây kết nối DT (GPIO {}) và SCK (GPIO {})".format(DT_PIN, SCK_PIN))
    print("   2. Load cell có kết nối đúng với HX711 không")
    print("   3. HX711 có được cấp nguồn (VCC/GND) không")
    print("   4. Thử đổi chân DT/SCK nếu cần")
else:
    print(f"✅ HX711 đang đọc được giá trị (trung bình: {sum(test_readings)/len(test_readings):.0f})")
print()

# ================== KẾT NỐI WIFI ==================
print("📡 Đang khởi tạo Wi-Fi...")
wlan = network.WLAN(network.STA_IF)
wlan.active(False)  # Tắt trước để reset
time.sleep(0.5)
wlan.active(True)   # Bật lại
time.sleep(1)       # Đợi Wi-Fi sẵn sàng

# Quét mạng Wi-Fi để kiểm tra SSID có sẵn không
print("🔍 Đang quét mạng Wi-Fi...")
try:
    networks = wlan.scan()
    print(f"📶 Tìm thấy {len(networks)} mạng Wi-Fi:")
    found_ssid = False
    for net in networks:
        ssid = net[0].decode('utf-8') if isinstance(net[0], bytes) else net[0]
        rssi = net[3]  # Signal strength
        print(f"   - {ssid} (Signal: {rssi} dBm)")
        if ssid == WIFI_SSID:
            found_ssid = True
            print(f"   ✅ Tìm thấy mạng '{WIFI_SSID}'!")
    
    if not found_ssid:
        print(f"⚠️  CẢNH BÁO: Không tìm thấy mạng '{WIFI_SSID}' trong danh sách!")
        print("💡 Kiểm tra lại tên mạng (SSID) có đúng không, hoặc mạng có thể bị ẩn.")
    else:
        print(f"✅ Mạng '{WIFI_SSID}' có sẵn, đang thử kết nối...")
except Exception as e:
    print(f"⚠️  Không thể quét mạng: {e}")
    print("💡 Tiếp tục thử kết nối...")

if not wlan.isconnected():
    print(f"📡 Đang kết nối tới Wi-Fi: {WIFI_SSID}...")
    try:
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    except OSError as e:
        print(f"❌ Lỗi kết nối: {e}")
        print("🔄 Đang thử lại...")
        wlan.active(False)
        time.sleep(1)
        wlan.active(True)
        time.sleep(1)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # Chờ kết nối với timeout
    max_wait = 20
    while not wlan.isconnected() and max_wait > 0:
        time.sleep(1)
        max_wait -= 1
        if max_wait % 5 == 0:
            print(f"⏳ Đang chờ kết nối... ({max_wait}s)")
    
    if wlan.isconnected():
        print(f"✅ Đã kết nối Wi-Fi! IP: {wlan.ifconfig()[0]}")
    else:
        print("❌ Không thể kết nối Wi-Fi sau 20 giây!")
        print("💡 Kiểm tra lại SSID và mật khẩu, hoặc khoảng cách tới router.")
        raise Exception("Wi-Fi connection failed")
else:
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
        try:
            hx.read()
        except:
            pass
        time.sleep_ms(10)
        
    for _ in range(samples):
        try:
            val = hx.read()
            readings.append(val)
        except Exception as e:
            # Nếu lỗi, thêm 0 hoặc giá trị cuối cùng
            if readings:
                readings.append(readings[-1])
            else:
                readings.append(0)
        time.sleep_ms(10)
    
    if not readings or all(r == 0 for r in readings):
        return 0
    
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
print("🔄 Bắt đầu vòng lặp đọc cân...")
print("💡 Hệ thống đang chạy. Thêm/bớt vật trên cân để test MQTT.\n")

# Biến để hiển thị heartbeat
loop_count = 0
last_heartbeat_time = time.time()

while True:
    try:
        raw = read_weight_stable()
        current_weight = convert_to_weight(raw)
        loop_count += 1
        
        weight_change = current_weight - last_known_weight
        
        # Hiển thị heartbeat mỗi 5 giây để biết code vẫn chạy
        current_time = time.time()
        if current_time - last_heartbeat_time >= 5:
            print(f"💓 Đang chạy... (Lần đọc: {loop_count})")
            print(f"   📊 Raw HX711: {raw}")
            if raw == 0:
                print(f"   ⚠️  CẢNH BÁO: Raw = 0! HX711 không đọc được giá trị!")
                print(f"   💡 Kiểm tra kết nối dây DT (GPIO {DT_PIN}) và SCK (GPIO {SCK_PIN})")
            print(f"   ⚖️  Khối lượng: {current_weight:.1f} g")
            print(f"   📈 Thay đổi so với mốc: {weight_change:.1f} g")
            print(f"   🎯 Ngưỡng: ±{WEIGHT_CHANGE_THRESHOLD} g\n")
            last_heartbeat_time = current_time
        
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

