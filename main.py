import cv2
import paho.mqtt.client as mqtt
import time
from ultralytics import YOLO
import math
import json
import os

# ================== CẤU HÌNH ==================
# --- Cấu hình MQTT (PHẢI GIỐNG HỆT TRONG CODE ESP32) ---
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "my-shop/shelf-1/events"

# --- Cấu hình Logic ---
WEIGHT_PER_BOTTLE = 350  # Gram trên mỗi chai (thay đổi nếu cần)
HIGHLIGHT_DURATION_SEC = 2.0

# --- Cấu hình Zone Cân (QUAN TRỌNG: BẠN SẼ CẦN THAY ĐỔI CÁC GIÁ TRỊ NÀY) ---
# Tọa độ (x, y) của góc trên bên trái, và chiều rộng, chiều cao của vùng
ZONE = {'x': 300, 'y': 250, 'w': 200, 'h': 150} 
ZONE_CONFIG_PATH = "zone_config.json"

# ================== LƯU/LOAD CẤU HÌNH ZONE ==================
def load_zone_config():
    try:
        if os.path.exists(ZONE_CONFIG_PATH):
            with open(ZONE_CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if all(k in data for k in ['x', 'y', 'w', 'h']):
                ZONE.update({
                    'x': int(data['x']),
                    'y': int(data['y']),
                    'w': max(10, int(data['w'])),
                    'h': max(10, int(data['h']))
                })
                print(f"🗂️ Đã tải cấu hình zone từ {ZONE_CONFIG_PATH}: {ZONE}")
    except Exception as e:
        print(f"Không thể tải cấu hình zone: {e}")

def save_zone_config():
    try:
        with open(ZONE_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(ZONE, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu zone vào {ZONE_CONFIG_PATH}: {ZONE}")
    except Exception as e:
        print(f"Không thể lưu cấu hình zone: {e}")

# ================== BIẾN TOÀN CỤC ==================
# Biến này sẽ được cập nhật bởi MQTT thread và được đọc bởi main thread
g_weight_change_event = None 
carts = {} # Lưu giỏ hàng của mỗi người {person_id: num_bottles}
last_taker_id = None
last_highlight_until = 0.0

# ================== KHỞI TẠO CÁC MODULE ==================
# --- Khởi tạo Camera ---
def open_camera():
    print("📷 Đang mở camera...")
    candidates = [
        (0, cv2.CAP_DSHOW),
        (0, cv2.CAP_MSMF),
        (0, cv2.CAP_VFW),
        (1, cv2.CAP_DSHOW),
        (1, 0),  # default backend
    ]
    for index, api in candidates:
        try:
            cap = cv2.VideoCapture(index, api) if api != 0 else cv2.VideoCapture(index)
            time.sleep(0.3)
            if cap.isOpened():
                print(f"✅ Mở camera thành công (index={index}, api={api})")
                return cap
            cap.release()
        except Exception:
            pass
    print("❌ Không thể mở camera. Kiểm tra kết nối/driver hoặc thử đổi cổng USB.")
    return None

cap = open_camera() # Số 0 thường là webcam mặc định

# Tham số retry khi đọc khung hình
READ_RETRY_LIMIT = 60
READ_RETRY_DELAY_SEC = 0.05

# Tải zone nếu có
load_zone_config()

# ================== TƯƠNG TÁC CHUỘT CHO ZONE ==================
is_dragging = False
drag_type = None  # 'move' | 'tl' | 'tr' | 'bl' | 'br'
drag_start = (0, 0)
zone_start = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
HANDLE_RADIUS = 10
frame_width = 0
frame_height = 0

def clamp(val, min_v, max_v):
    return max(min_v, min(max_v, val))

def get_handles():
    x, y, w, h = ZONE['x'], ZONE['y'], ZONE['w'], ZONE['h']
    return {
        'tl': (x, y),
        'tr': (x + w, y),
        'bl': (x, y + h),
        'br': (x + w, y + h),
    }

def hit_handle(px, py):
    for name, (hx, hy) in get_handles().items():
        if (px - hx) ** 2 + (py - hy) ** 2 <= HANDLE_RADIUS ** 2:
            return name
    return None

def point_in_zone(px, py):
    return ZONE['x'] <= px <= ZONE['x'] + ZONE['w'] and ZONE['y'] <= py <= ZONE['y'] + ZONE['h']

def on_mouse(event, x, y, flags, param):
    global is_dragging, drag_type, drag_start, zone_start, ZONE
    if event == cv2.EVENT_LBUTTONDOWN:
        handle = hit_handle(x, y)
        if handle:
            is_dragging = True
            drag_type = handle
            drag_start = (x, y)
            zone_start = ZONE.copy()
        elif point_in_zone(x, y):
            is_dragging = True
            drag_type = 'move'
            drag_start = (x, y)
            zone_start = ZONE.copy()
    elif event == cv2.EVENT_MOUSEMOVE and is_dragging:
        dx = x - drag_start[0]
        dy = y - drag_start[1]
        x0, y0, w0, h0 = zone_start['x'], zone_start['y'], zone_start['w'], zone_start['h']
        if drag_type == 'move':
            nx = clamp(x0 + dx, 0, max(0, frame_width - w0))
            ny = clamp(y0 + dy, 0, max(0, frame_height - h0))
            ZONE['x'], ZONE['y'] = int(nx), int(ny)
        else:
            # Resize from a corner
            left = x0
            top = y0
            right = x0 + w0
            bottom = y0 + h0
            if 'l' in drag_type:
                left = clamp(x0 + dx, 0, right - 20)
            if 'r' in drag_type:
                right = clamp(x0 + w0 + dx, left + 20, frame_width)
            if 't' in drag_type:
                top = clamp(y0 + dy, 0, bottom - 20)
            if 'b' in drag_type:
                bottom = clamp(y0 + h0 + dy, top + 20, frame_height)
            ZONE['x'] = int(left)
            ZONE['y'] = int(top)
            ZONE['w'] = int(right - left)
            ZONE['h'] = int(bottom - top)
    elif event == cv2.EVENT_LBUTTONUP:
        is_dragging = False
        drag_type = None

# --- Khởi tạo YOLOv8 để nhận diện người ---
model = YOLO('yolov8n.pt')  # Dùng model nano nhỏ gọn, nhanh

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
cv2.namedWindow("Amazon Go Demo", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Amazon Go Demo", on_mouse)
consecutive_read_failures = 0
while True:
    if cap is None or not cap.isOpened():
        print("❌ Lỗi: Không thể mở camera.")
        # Thử mở lại camera
        cap = open_camera()
        if cap is None or not cap.isOpened():
            break
    ret, frame = cap.read()
    if not ret:
        consecutive_read_failures += 1
        # Cứ sau 10 lần lỗi, thử mở lại camera
        if consecutive_read_failures % 10 == 0:
            if cap is not None:
                cap.release()
            cap = open_camera()
        if consecutive_read_failures >= READ_RETRY_LIMIT:
            print("❌ Camera không trả khung hình sau nhiều lần thử. Thoát.")
            break
        time.sleep(READ_RETRY_DELAY_SEC)
        continue
    else:
        consecutive_read_failures = 0
        
    # --- 1. Nhận diện người và gán ID tracking ---
    results = model.track(frame, persist=True, classes=[0]) # Chỉ nhận diện lớp 'person'
    person_boxes = results[0].boxes

    # --- 2. XỬ LÝ SỰ KIỆN TỪ CÂN (NẾU CÓ) ---
    if g_weight_change_event is not None:
        weight_change = g_weight_change_event
        now = time.time()

        # Tìm người gần shelf zone nhất (theo tâm bbox -> khoảng cách tới hình chữ nhật zone)
        closest_person_id = None
        closest_distance = float('inf')
        if person_boxes is not None and person_boxes.id is not None:
            zx, zy, zw, zh = ZONE['x'], ZONE['y'], ZONE['w'], ZONE['h']
            zcx1, zcy1, zcx2, zcy2 = zx, zy, zx + zw, zy + zh
            for box in person_boxes:
                x1, y1, x2, y2 = [float(i) for i in box.xyxy[0]]
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                # khoảng cách điểm tới hình chữ nhật (0 nếu ở trong)
                dx = 0.0 if zcx1 <= cx <= zcx2 else (zcx1 - cx if cx < zcx1 else cx - zcx2)
                dy = 0.0 if zcy1 <= cy <= zcy2 else (zcy1 - cy if cy < zcy1 else cy - zcy2)
                dist = math.hypot(dx, dy)
                if dist < closest_distance:
                    closest_distance = dist
                    closest_person_id = int(box.id[0])

        if closest_person_id is not None and weight_change < 0:
            num_bottles = round(abs(weight_change) / WEIGHT_PER_BOTTLE)
            carts[closest_person_id] = carts.get(closest_person_id, 0) + num_bottles
            last_taker_id = closest_person_id
            last_highlight_until = now + HIGHLIGHT_DURATION_SEC
            print(f"✅ KẾT LUẬN: Person #{closest_person_id} đã LẤY {num_bottles} chai. (dist={closest_distance:.1f})")
        elif closest_person_id is not None and weight_change > 0:
            # Optional: nếu muốn trừ giỏ khi đặt lại hàng, bật dòng sau
            # num_bottles = round(abs(weight_change) / WEIGHT_PER_BOTTLE)
            # carts[closest_person_id] = max(0, carts.get(closest_person_id, 0) - num_bottles)
            # last_taker_id = closest_person_id
            # last_highlight_until = now + HIGHLIGHT_DURATION_SEC
            print(f"ℹ️ Phát hiện tăng khối lượng: {weight_change}. (Người gần nhất: #{closest_person_id})")
        else:
            print("⚠️ Không tìm thấy người nào để gán sự kiện cân.")

        # Reset sự kiện sau khi xử lý
        g_weight_change_event = None

    # --- 5. Vẽ lên màn hình ---
    # Vẽ zone + tay nắm (handles)
    cv2.rectangle(frame, (ZONE['x'], ZONE['y']), (ZONE['x'] + ZONE['w'], ZONE['y'] + ZONE['h']), (255, 0, 0), 2)
    cv2.putText(frame, "SHELF ZONE", (ZONE['x'], max(15, ZONE['y'] - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    for name, (hx, hy) in get_handles().items():
        cv2.circle(frame, (int(hx), int(hy)), HANDLE_RADIUS, (255, 0, 0), -1)

    # Vẽ bounding box và giỏ hàng cho người
    if person_boxes is not None and person_boxes.id is not None:
        for box in person_boxes:
            person_id = int(box.id[0])
            x1, y1, x2, y2 = [int(i) for i in box.xyxy[0]]
            color = (0, 255, 0)
            if person_id == last_taker_id and time.time() < last_highlight_until:
                color = (0, 165, 255)  # Orange
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Hiển thị giỏ hàng
            num_items = carts.get(person_id, 0)
            label = f"Person #{person_id} | Cart: {num_items}"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Hiển thị video
    # Cập nhật kích thước khung hình để ràng buộc kéo-thả
    frame_height, frame_width = frame.shape[:2]
    cv2.imshow("Amazon Go Demo", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        save_zone_config()

# --- Dọn dẹp ---
if cap is not None:
    cap.release()
cv2.destroyAllWindows()
client.loop_stop()
print("Chương trình đã kết thúc.")