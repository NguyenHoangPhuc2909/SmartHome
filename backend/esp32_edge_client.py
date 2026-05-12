import os
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import cv2
import time
import requests
import numpy as np
import threading

print("[INFO] Đang nạp YuNet Face Detector siêu nhẹ...")

# ================= CẤU HÌNH =================
ESP32_IP       = "192.168.1.42"
HOME_CODE      = "H123456" # Thay bằng mã ngôi nhà của bạn
CAPTURE_URL    = f"http://{ESP32_IP}/capture"
SERVER_URL     = f"http://localhost:5000/api/access/recognize?home_code={HOME_CODE}"
CAPTURE_DELAY  = 0.5   # Chụp 2 ảnh/giây - ESP32 chịu được lâu dài
RECOG_COOLDOWN = 5.0
# ============================================

detector = cv2.FaceDetectorYN.create( 
    model="trained_models/face_detection_yunet.onnx",
    config="",
    input_size=(320, 320),
    score_threshold=0.75,
    nms_threshold=0.3,
    top_k=5000
)
print("[INFO] YuNet sẵn sàng!")

try:
    requests.get(f"http://{ESP32_IP}/control?var=framesize&val=9", timeout=3)  # QVGA
    requests.get(f"http://{ESP32_IP}/control?var=quality&val=20", timeout=3)
    print("[INFO] Đã cấu hình ESP32: QVGA.")
except:
    pass

# ── Bộ đệm frame dùng chung ──────────────────────────────────────────────────
latest_frame     = None
latest_display   = None   # Frame đã vẽ khung xanh (dùng để hiển thị)
frame_lock       = threading.Lock()
running          = True

# ── Thread 1: Chụp ảnh từ ESP32 (2 FPS) + Detect mặt + Trigger nhận diện ─────
def capture_and_detect():
    global latest_frame, latest_display, running
    session = requests.Session()
    last_recognize_time = 0

    while running:
        t = time.time()
        try:
            resp = session.get(CAPTURE_URL, timeout=4)
            if resp.status_code != 200:
                time.sleep(1)
                continue

            img = cv2.imdecode(np.frombuffer(resp.content, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue

            h, w = img.shape[:2]
            detector.setInputSize((w, h))
            display = img.copy()

            now = time.time()
            if now - last_recognize_time > RECOG_COOLDOWN:
                _, faces = detector.detect(img)
                if faces is not None and len(faces) > 0:
                    last_recognize_time = now
                    for face in faces:
                        x, y, fw, fh = face[:4].astype(int)
                        cv2.rectangle(display, (x, y), (x+fw, y+fh), (0, 220, 90), 2)
                        cv2.putText(display, "Nhan dang...", (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 90), 2)
                    threading.Thread(target=send_to_server, args=(img.copy(),), daemon=True).start()

            with frame_lock:
                latest_frame   = img
                latest_display = display

        except requests.exceptions.ConnectionError:
            print("[Capture] Mất kết nối. Thử lại sau 3s...")
            session = requests.Session()
            time.sleep(3)
            continue
        except requests.exceptions.Timeout:
            time.sleep(0.5)
            continue
        except Exception as e:
            print(f"[Capture] Lỗi: {e}")
            time.sleep(1)
            continue

        # Kiểm soát đúng 2 FPS
        elapsed = time.time() - t
        wait = CAPTURE_DELAY - elapsed
        if wait > 0:
            time.sleep(wait)

threading.Thread(target=capture_and_detect, daemon=True).start()

# ── Thread 2: Gửi ảnh lên server ─────────────────────────────────────────────
def send_to_server(img):
    print("\n>>> [EDGE] Phát hiện khuôn mặt! Đang gửi lên Server...")
    _, jpeg = cv2.imencode('.jpg', img)
    files = {'image': ('capture.jpg', jpeg.tobytes(), 'image/jpeg')}
    try:
        resp = requests.post(SERVER_URL, files=files, timeout=10)
        data = resp.json()
        result = data.get('result', 'N/A')
        name   = data.get('matched_name') or 'Người lạ'
        conf   = data.get('confidence', 0)
        icon   = "✅" if result == "GRANTED" else "❌"
        print(f"<<< {icon} [{result}] Tên: {name} | Độ tin cậy: {conf:.2f}")
    except Exception as e:
        print(f"<<< [LỖI] {e}")

# ── Main: CHỈ hiển thị — chạy ở 30 FPS, không bao giờ đơ ────────────────────
print("[INFO] Ấn phím 'q' để thoát.\n")

while True:
    with frame_lock:
        display = latest_display.copy() if latest_display is not None else None

    if display is None:
        blank = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(blank, "Dang ket noi ESP32...", (30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
        cv2.imshow("ESP32-CAM | SmartHome", blank)
    else:
        cv2.imshow("ESP32-CAM | SmartHome", display)

    # 30 FPS display - không bao giờ đơ dù network chậm
    if cv2.waitKey(33) & 0xFF == ord('q'):
        break

running = False
cv2.destroyAllWindows()
print("[INFO] Đã thoát.")
