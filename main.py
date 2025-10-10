import cv2
import paho.mqtt.client as mqtt
import time
from ultralytics import YOLO
import mediapipe as mp
import math

# ================== CẤU HÌNH ==================
# --- Cấu hình MQTT (PHẢI GIỐNG HỆT TRONG CODE ESP32) ---
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "my-shop/shelf-1/events"

# --- Cấu hình Logic ---
WEIGHT_PER_BOTTLE = 350  # Gram trên mỗi chai (thay đổi nếu cần)
ACTION_BUFFER_TIME = 2.0  # Giây (tìm hành động tay trong 2s gần nhất)

# --- Cấu hình Zone Cân (QUAN TRỌNG: BẠN SẼ CẦN THAY ĐỔI CÁC GIÁ TRỊ NÀY) ---
# Tọa độ (x, y) của góc trên bên trái, và chiều rộng, chiều cao của vùng
ZONE = {'x': 300, 'y': 250, 'w': 200, 'h': 150} 

# ================== BIẾN TOÀN CỤC ==================
# Biến này sẽ được cập nhật bởi MQTT thread và được đọc bởi main thread
g_weight_change_event = None 
action_buffer = []  # Lưu các hành động tay [{person_id, timestamp}, ...]
carts = {} # Lưu giỏ hàng của mỗi người {person_id: num_bottles}

# ================== KHỞI TẠO CÁC MODULE ==================
# --- Khởi tạo Camera ---
cap = cv2.VideoCapture(0) # Số 0 thường là webcam mặc định

# --- Khởi tạo YOLOv8 để nhận diện người ---
model = YOLO('yolov8n.pt')  # Dùng model nano nhỏ gọn, nhanh

# --- Khởi tạo MediaPipe để nhận diện tay ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# ================== LOGIC MQTT (CHẠY NGẦM) ==================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT đã kết nối!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Kết nối MQTT thất bại, mã lỗi: {rc}")

def on_message(client, userdata, msg):
    global g_weight_change_event
    payload = msg.payload.decode('utf-8')
    print(f"📬 Nhận được tin nhắn từ cân: '{payload}'")
    try:
        # Tách chuỗi, ví dụ: "CHANGE:-350" -> -350
        change_value = int(payload.split(':')[1])
        g_weight_change_event = change_value # Đặt "cờ" báo hiệu có sự kiện
    except Exception as e:
        print(f"Lỗi xử lý payload MQTT: {e}")

# --- Khởi tạo và chạy MQTT trong luồng riêng ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.loop_start() # << RẤT QUAN TRỌNG: Chạy ngầm, không block chương trình

# ================== VÒNG LẶP CHÍNH CỦA ỨNG DỤNG ==================
print("🚀 Bắt đầu chương trình chính...")
while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # --- 1. Nhận diện người và gán ID tracking ---
    results = model.track(frame, persist=True, classes=[0]) # Chỉ nhận diện lớp 'person'
    person_boxes = results[0].boxes

    # --- 2. Nhận diện tay ---
    hand_results = hands.process(frame_rgb)

    # --- 3. Ghi nhận hành động "tay trong zone" ---
    if hand_results.multi_hand_landmarks:
        for hand_landmarks in hand_results.multi_hand_landmarks:
            # Lấy tọa độ cổ tay (điểm 0)
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            cx, cy = int(wrist.x * frame.shape[1]), int(wrist.y * frame.shape[0])

            # Kiểm tra tay có trong zone không
            if ZONE['x'] < cx < ZONE['x'] + ZONE['w'] and ZONE['y'] < cy < ZONE['y'] + ZONE['h']:
                # Tìm người gần nhất với bàn tay này
                closest_person_id = None
                min_dist = float('inf')
                if person_boxes is not None and person_boxes.id is not None:
                    for box in person_boxes:
                        px1, py1, px2, py2 = box.xyxy[0]
                        person_center_x = (px1 + px2) / 2
                        person_center_y = (py1 + py2) / 2
                        dist = math.sqrt((cx - person_center_x)**2 + (cy - person_center_y)**2)
                        if dist < min_dist:
                            min_dist = dist
                            closest_person_id = int(box.id[0])
                
                if closest_person_id is not None:
                    # Ghi nhận hành động vào buffer
                    action_buffer.append({'person_id': closest_person_id, 'timestamp': time.time()})
                    # Vẽ vòng tròn xanh lá quanh tay trong zone
                    cv2.circle(frame, (cx, cy), 15, (0, 255, 0), 3)

    # --- 4. XỬ LÝ SỰ KIỆN TỪ CÂN (NẾU CÓ) ---
    if g_weight_change_event is not None:
        weight_change = g_weight_change_event
        
        # Tìm người hành động gần đây nhất
        person_id_acted = None
        now = time.time()
        # Lọc buffer, chỉ giữ lại các hành động trong khoảng thời gian cho phép
        recent_actions = [a for a in action_buffer if now - a['timestamp'] < ACTION_BUFFER_TIME]
        if recent_actions:
            # Lấy hành động gần nhất
            person_id_acted = recent_actions[-1]['person_id']

        if person_id_acted is not None:
            if weight_change < 0: # Lấy hàng
                num_bottles = round(abs(weight_change) / WEIGHT_PER_BOTTLE)
                print(f"✅ KẾT LUẬN: Person #{person_id_acted} đã LẤY {num_bottles} chai.")
                # Cập nhật giỏ hàng
                carts[person_id_acted] = carts.get(person_id_acted, 0) + num_bottles
        
        # Reset "cờ" sau khi đã xử lý
        g_weight_change_event = None
        action_buffer.clear() # Xóa buffer sau khi xử lý

    # --- 5. Vẽ lên màn hình ---
    # Vẽ zone
    cv2.rectangle(frame, (ZONE['x'], ZONE['y']), (ZONE['x'] + ZONE['w'], ZONE['y'] + ZONE['h']), (255, 0, 0), 2)
    cv2.putText(frame, "SHELF ZONE", (ZONE['x'], ZONE['y'] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # Vẽ bounding box và giỏ hàng cho người
    if person_boxes is not None and person_boxes.id is not None:
        for box in person_boxes:
            person_id = int(box.id[0])
            x1, y1, x2, y2 = [int(i) for i in box.xyxy[0]]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Hiển thị giỏ hàng
            num_items = carts.get(person_id, 0)
            label = f"Person #{person_id} | Cart: {num_items}"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Hiển thị video
    cv2.imshow("Amazon Go Demo", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Dọn dẹp ---
cap.release()
cv2.destroyAllWindows()
client.loop_stop()
print("Chương trình đã kết thúc.")