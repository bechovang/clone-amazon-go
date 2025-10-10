import paho.mqtt.client as mqtt

# --- CẤU HÌNH (PHẢI GIỐNG HỆT TRONG CODE ESP32) ---
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "my-shop/shelf-1/events"

# Hàm này sẽ được gọi khi kết nối thành công tới broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Đã kết nối thành công tới MQTT Broker!")
        # Sau khi kết nối, đăng ký (subscribe) để lắng nghe topic
        client.subscribe(MQTT_TOPIC)
        print(f"👂 Đang lắng nghe trên topic: '{MQTT_TOPIC}'")
    else:
        print(f"❌ Kết nối thất bại, mã lỗi: {rc}")

# Hàm này sẽ được gọi mỗi khi có tin nhắn mới từ topic đã đăng ký
def on_message(client, userdata, msg):
    # Lấy nội dung tin nhắn và in ra màn hình
    payload = msg.payload.decode('utf-8')
    print(f"📬 Nhận được tin nhắn: '{payload}' từ topic '{msg.topic}'")

# --- KHỞI TẠO VÀ CHẠY ---
# Tạo một MQTT client mới
client = mqtt.Client()

# Gán các hàm callback
client.on_connect = on_connect
client.on_message = on_message

# Kết nối tới broker
print("🧠 Đang kết nối tới MQTT Broker...")
client.connect(MQTT_BROKER, 1883, 60)

# Bắt đầu vòng lặp để lắng nghe mãi mãi
# Chương trình sẽ dừng ở đây và chờ tin nhắn
client.loop_forever()