import cv2
import os
import time
import threading
from config import Config

# Nhãn tiếng Việt hiển thị trên màn hình
ANGLE_LABEL = {
    "Thang": "THANG",
    "Trai":  "TRAI",
    "Phai":  "PHAI",
    "Len":   "LEN",
    "Xuong": "XUONG",
}

class VideoCamera(object):
    def __init__(self):
        # ── SỬA Ở ĐÂY: Dùng Webcam máy tính (0) để chụp Dataset ──
        self.camera_index = 0 
        self.cap = None
        
        # --- YUNET FACE DETECTOR ---
        try:
            self.detector = cv2.FaceDetectorYN.create(
                model="trained_models/face_detection_yunet.onnx",
                config="",
                input_size=(320, 320),
                score_threshold=0.8,
                nms_threshold=0.3,
                top_k=5000
            )
            self.use_yunet = True
            print("[INFO] Đã kích hoạt YuNet Face Detector!")
        except Exception as e:
            print(f"[CẢNH BÁO] Không load được YuNet ({e}), dùng lại Haar Cascade.")
            self.use_yunet = False
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
            
        self.limit_per_pos   = 5
        self.angles          = ["Thang", "Trai", "Phai", "Len", "Xuong"]
        self.last_save_time  = 0
        self.is_capturing    = False
        self.current_user    = ""
        self._lock           = threading.Lock()

        # Trạng thái pause
        self.pause_until     = 0.0
        self.pause_msg       = ""
        
        self.active_viewers  = 0

    def __del__(self):
        self.release_camera()

    def release_camera(self):
        """Giải phóng camera vật lý để tắt đèn Webcam"""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def _get_cap(self):
        """Khởi tạo camera nếu chưa có"""
        if self.cap is None or not self.cap.isOpened():
            # Thêm CAP_DSHOW để fix lỗi màn hình đen trên Windows
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            # Set độ phân giải thấp một chút cho mượt
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return self.cap

    def _count_angle(self, path: str, angle: str) -> int:
        if not os.path.exists(path): return 0
        return len([f for f in os.listdir(path) if f.startswith(angle + "_")])

    def _get_current_angle(self, path: str):
        for angle in self.angles:
            count = self._count_angle(path, angle)
            if count < self.limit_per_pos:
                return angle, count
        return "Hoan thanh", 0

    def _detect(self, img_bgr, gray, angle, w_img):
        if getattr(self, 'use_yunet', False):
            h, w = img_bgr.shape[:2]
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(img_bgr)
            if faces is not None and len(faces) > 0:
                return [face[:4].astype(int) for face in faces if face[-1] > 0.7]
            return []
        
        if angle == "Thang":
            return self.face_cascade.detectMultiScale(gray, 1.1, 6, minSize=(80, 80))
        if angle == "Trai":
            flipped = cv2.flip(gray, 1)
            boxes = self.profile_cascade.detectMultiScale(flipped, 1.1, 6, minSize=(80, 80))
            return [(w_img - x - w, y, w, h) for (x, y, w, h) in boxes] if len(boxes) > 0 else []
        if angle == "Phai":
            return self.profile_cascade.detectMultiScale(gray, 1.1, 6, minSize=(80, 80))
        if angle in ("Len", "Xuong"):
            return self.face_cascade.detectMultiScale(gray, 1.2, 4, minSize=(80, 80))
        return []

    def get_frame(self):
        time.sleep(0.02) # Giảm tải CPU và giúp stream ổn định hơn
        cap = self._get_cap()
        success, img = cap.read()
        if not success or img is None:
            return None

        # Tăng tốc độ mượt (chụp dataset cần nhanh)
        img = cv2.flip(img, 1) # Chụp qua webcam thường bị ngược gương, nên flip lại
        
        h_img, w_img = img.shape[:2]
        center_x, center_y = w_img // 2, h_img // 2
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        path = f"captured_faces/{self.current_user}"
        current_angle = "Hoan thanh"
        current_count = 0
        if self.current_user:
            os.makedirs(path, exist_ok=True)
            current_angle, current_count = self._get_current_angle(path)

        now = time.time()

        # ── Pause Logic ──
        if self.pause_until > 0 and now < self.pause_until:
            remaining = self.pause_until - now
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 0), (w_img, h_img), (0, 0, 0), -1)
            img = cv2.addWeighted(img, 0.3, overlay, 0.7, 0)
            self._put_text_center(img, self.pause_msg, (center_x, center_y - 40), scale=1.0, color=(0, 255, 120))
            self._put_text_center(img, f"Tiep tuc sau {remaining:.1f}s ...", (center_x, center_y + 55), scale=0.6, color=(140, 140, 140))
            self._draw_progress(img, path, w_img, h_img)
            ret, jpeg = cv2.imencode(".jpg", img)
            return jpeg.tobytes() if ret else None

        if self.pause_until > 0 and now >= self.pause_until:
            self.pause_until = 0.0
            self.pause_msg = ""

        # ── Hoàn thành ──
        if current_angle == "Hoan thanh":
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 0), (w_img, h_img), (0, 0, 0), -1)
            img = cv2.addWeighted(img, 0.35, overlay, 0.65, 0)
            self._put_text_center(img, "HOAN THANH!", (center_x, center_y - 20), scale=1.1, color=(0, 255, 120))
            self._draw_progress(img, path, w_img, h_img)
            ret, jpeg = cv2.imencode(".jpg", img)
            return jpeg.tobytes() if ret else None

        # ── Detect ──
        try:
            boxes = self._detect(img, gray, current_angle, w_img)
        except Exception as e:
            print(f"[ERROR DETECT] {e}")
            boxes = []
        msg = f"Quay mat sang: {ANGLE_LABEL.get(current_angle, current_angle)}"
        color = (0, 200, 255)
        is_ready = False
        save_box = None

        if len(boxes) > 0:
            # Chọn box gần tâm nhất
            best, best_d = None, float("inf")
            for (x, y, w, h) in boxes:
                d = abs((x + w // 2) - center_x) + abs((y + h // 2) - center_y)
                if d < best_d: best_d, best = d, (x, y, w, h)
            
            x, y, w, h = best
            cv2.rectangle(img, (x, y), (x+w, y+h), (60, 60, 255), 2)
            if abs((x+w//2)-center_x) < 70 and abs((y+h//2)-center_y) < 70 and w > 100:
                is_ready, save_box = True, (x, y, w, h)
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 80), 3)
                color = (0, 255, 80)
                msg = "Giu nguyen!"

        # ── Lưu ảnh ──
        if self.is_capturing and is_ready and save_box:
            if now - self.last_save_time > 0.8:
                sx, sy, sw, sh = save_box
                face_crop = img[sy:sy+sh, sx:sx+sw]
                if face_crop.size > 0:
                    face_resized = cv2.resize(face_crop, (112, 112))
                    cv2.imwrite(os.path.join(path, f"{current_angle}_{current_count}.jpg"), face_resized)
                    self.last_save_time = now
                    if current_count + 1 >= self.limit_per_pos:
                        self.pause_msg = f"Xong goc {ANGLE_LABEL.get(current_angle, current_angle)}!"
                        self.pause_until = now + 2.0
        
        # HUD
        cv2.drawMarker(img, (center_x, center_y), (255, 255, 255), cv2.MARKER_CROSS, 30, 2)
        self._draw_progress(img, path, w_img, h_img)
        self._draw_label_bg(img, msg, (15, 38), color=color)
        
        ret, jpeg = cv2.imencode(".jpg", img)
        return jpeg.tobytes() if ret else None

    def _put_text_center(self, img, text, center, scale=0.8, color=(255, 255, 255)):
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        cv2.putText(img, text, (center[0] - tw // 2, center[1] + th // 2), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)

    def _draw_label_bg(self, img, text, pos, scale=0.68, color=(255, 255, 255)):
        (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        x, y = pos
        sub = img[y - th - 6: y + bl + 6, x - 6: x + tw + 6]
        if sub.size > 0:
            dark = sub.copy(); cv2.rectangle(dark, (0, 0), (sub.shape[1], sub.shape[0]), (0, 0, 0), -1)
            img[y - th - 6: y + bl + 6, x - 6: x + tw + 6] = cv2.addWeighted(sub, 0.3, dark, 0.7, 0)
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)

    def _draw_progress(self, img, path, w_img, h_img):
        bar_h, y_start = 30, h_img - 30
        seg_w = w_img // len(self.angles)
        for i, angle in enumerate(self.angles):
            count = self._count_angle(path, angle)
            ratio = min(count / self.limit_per_pos, 1.0)
            x0 = i * seg_w
            cv2.rectangle(img, (x0, y_start), (x0 + seg_w, h_img), (25, 25, 25), -1)
            fill_w = int((seg_w - 2) * ratio)
            if fill_w > 0:
                cv2.rectangle(img, (x0 + 1, y_start + 2), (x0 + 1 + fill_w, h_img - 2), (0, 210, 90) if ratio >= 1.0 else (0, 150, 210), -1)
            txt = f"{ANGLE_LABEL[angle]} {count}/5"
            (tw, _), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.putText(img, txt, (x0 + (seg_w - tw) // 2, h_img - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1, cv2.LINE_AA)