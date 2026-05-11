import cv2
import os
import time
import threading

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
        # ĐỔI THÀNH IP ESP32-CAM CỦA BẠN NHÉ (Ví dụ: http://192.168.1.100:81/stream)
        self.stream_url      = "http://192.168.1.42/stream" 
        
        # --- NÂNG CẤP LÊN YUNET ---
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
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self.profile_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_profileface.xml"
            )
        self.limit_per_pos   = 5
        self.angles          = ["Thang", "Trai", "Phai", "Len", "Xuong"]
        self.last_save_time  = 0
        self.is_capturing    = False
        self.current_user    = ""
        self._lock           = threading.Lock()

        # Trạng thái pause giữa các góc
        self.pause_until     = 0.0   # epoch time khi hết pause
        self.pause_msg       = ""

        # --- NÂNG CẤP: CHẠY NỀN ĐỂ TỰ NHẬN DIỆN TỪ ESP32-CAM ---
        self.latest_frame    = None
        self._lock           = threading.Lock()
        self.active_viewers  = 0  # <--- Đếm số người đang xem Web

        # Chạy thread lấy ảnh nền
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def __del__(self):
        pass

    def _update(self):
        """Thread chạy ngầm: Lấy ảnh ESP32 liên tục qua cổng /capture (Cực kỳ ổn định)"""
        import urllib.request
        import numpy as np
        import re
        import requests

        # Tự động lấy IP từ cấu hình để truy cập cổng 80 (/capture) thay vì 81 (/stream)
        match = re.search(r'(http://[^:/]+)', self.stream_url)
        capture_url = match.group(1) + "/capture" if match else self.stream_url

        # Dùng Session để dùng chung 1 kết nối TCP (Tránh lỗi vỡ RAM error in accept 128 trên ESP32)
        session = requests.Session()

        while True:
            # 💡 NẾU KHÔNG CÓ AI MỞ WEB, BACKEND SẼ ĐI NGỦ ĐỂ NHƯỜNG CAMERA CHO EDGE CLIENT
            if self.active_viewers <= 0:
                time.sleep(1)
                continue

            try:
                # Ép lấy ảnh siêu tốc (10-20 FPS) để hết lag
                time.sleep(0.05)
                
                # Gọi API /capture và lấy thẳng byte nội dung
                response = session.get(capture_url, timeout=2)
                jpg = response.content
                
                img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    with self._lock:
                        self.latest_frame = img

            except Exception as e:
                print(f"[CẢNH BÁO] ESP32-CAM bị nghẽn mạng: {e}. Đang tự động thử lại...")
                time.sleep(2)

    def __del__(self):
        pass
    # ── Helpers ──────────────────────────────────────────────────────────────

    def _count_angle(self, path: str, angle: str) -> int:
        if not os.path.exists(path):
            return 0
        return len([f for f in os.listdir(path) if f.startswith(angle + "_")])

    def _get_current_angle(self, path: str):
        """Trả về (angle, count) góc chưa đủ ảnh. ("Hoan thanh", 0) nếu xong."""
        for angle in self.angles:
            count = self._count_angle(path, angle)
            if count < self.limit_per_pos:
                return angle, count
        return "Hoan thanh", 0

    def _detect(self, frame_in, angle, w_img):
        """
        Detect khuôn mặt theo góc. Hỗ trợ cả YuNet siêu nhẹ và Haar Cascade.
        """
        if getattr(self, 'use_yunet', False):
            # Cập nhật kích thước đầu vào cho detector (rất quan trọng với YuNet)
            h, w = frame_in.shape[:2]
            self.detector.setInputSize((w, h))
            
            _, faces = self.detector.detect(frame_in)
            if faces is not None and len(faces) > 0:
                # Dùng ngưỡng thấp hơn (0.7) vì mặt quay góc (profile) thường bị giảm độ tin cậy
                return [face[:4].astype(int) for face in faces if face[-1] > 0.7]
            return []

        # NẾU KHÔNG CÓ MTCNN THÌ DÙNG HAAR
        gray = frame_in
        if angle == "Thang":
            return self.face_cascade.detectMultiScale(
                gray, 1.1, 6, minSize=(80, 80)
            )

        if angle == "Trai":
            flipped = cv2.flip(gray, 1)
            boxes   = self.profile_cascade.detectMultiScale(
                flipped, 1.1, 6, minSize=(80, 80)
            )
            if len(boxes) == 0:
                return []
            return [(w_img - x - w, y, w, h) for (x, y, w, h) in boxes]

        if angle == "Phai":
            return self.profile_cascade.detectMultiScale(
                gray, 1.1, 6, minSize=(80, 80)
            )

        if angle in ("Len", "Xuong"):
            return self.face_cascade.detectMultiScale(
                gray, 1.2, 4, minSize=(80, 80)
            )

        return []

    # ── Main frame loop ───────────────────────────────────────────────────────

    def get_frame(self):
        # Giới hạn tốc độ cho Frontend (20 FPS) để hình mượt nhất có thể
        time.sleep(0.05)
        
        with self._lock:
            img = self.latest_frame
            
        if img is None:
            return None

        # Copy để vẽ HUD không dính vào frame gốc
        img = img.copy()

        # ESP32-CAM nếu hình không bị ngược thì không cần flip. 
        # Tạm thời comment lại, nếu bạn thấy ngược trái phải thì bỏ comment ra:
        # img = cv2.flip(img, 1)

        h_img, w_img = img.shape[:2]
        center_x, center_y = w_img // 2, h_img // 2
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        path          = f"captured_faces/{self.current_user}"
        current_angle = "Hoan thanh"
        current_count = 0

        if self.current_user:
            os.makedirs(path, exist_ok=True)
            current_angle, current_count = self._get_current_angle(path)

        now = time.time()

        # ── Đang trong thời gian pause giữa 2 góc ────────────────────────────
        if self.pause_until > 0 and now < self.pause_until:
            remaining = self.pause_until - now

            overlay = img.copy()
            cv2.rectangle(overlay, (0, 0), (w_img, h_img), (0, 0, 0), -1)
            img = cv2.addWeighted(img, 0.3, overlay, 0.7, 0)

            self._put_text_center(img, self.pause_msg,
                                  (w_img // 2, h_img // 2 - 40),
                                  scale=1.0, color=(0, 255, 120), thickness=2)

            next_angle, _ = self._get_current_angle(path)
            if next_angle != "Hoan thanh":
                label = ANGLE_LABEL.get(next_angle, next_angle)
                self._put_text_center(img,
                                      f"Chuan bi goc tiep theo: {label}",
                                      (w_img // 2, h_img // 2 + 10),
                                      scale=0.72, color=(200, 220, 255), thickness=1)

            self._put_text_center(img, f"Tiep tuc sau {remaining:.1f}s ...",
                                  (w_img // 2, h_img // 2 + 55),
                                  scale=0.6, color=(140, 140, 140), thickness=1)

            self._draw_progress(img, path, w_img, h_img)
            ret, jpeg = cv2.imencode(".jpg", img)
            return jpeg.tobytes() if ret else None

        # Hết pause
        if self.pause_until > 0 and now >= self.pause_until:
            self.pause_until = 0.0
            self.pause_msg   = ""

        # ── Hoàn thành tất cả góc ────────────────────────────────────────────
        if current_angle == "Hoan thanh":
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 0), (w_img, h_img), (0, 0, 0), -1)
            img = cv2.addWeighted(img, 0.35, overlay, 0.65, 0)
            self._put_text_center(img, "HOAN THANH! Da du 5 goc.",
                                  (w_img // 2, h_img // 2 - 20),
                                  scale=1.1, color=(0, 255, 120), thickness=3)
            self._put_text_center(img, "Nhan DUNG de ket thuc.",
                                  (w_img // 2, h_img // 2 + 30),
                                  scale=0.65, color=(200, 200, 200), thickness=1)
            self._draw_progress(img, path, w_img, h_img)
            ret, jpeg = cv2.imencode(".jpg", img)
            return jpeg.tobytes() if ret else None

        # ── Detect khuôn mặt ─────────────────────────────────────────────────
        boxes    = self._detect(gray, current_angle, w_img)
        msg      = f"Quay mat sang: {ANGLE_LABEL.get(current_angle, current_angle)}"
        color    = (0, 200, 255)
        is_ready = False
        save_box = None

        if len(boxes) > 0:
            best, best_d = None, float("inf")
            for (x, y, w, h) in boxes:
                d = abs((x + w // 2) - center_x) + abs((y + h // 2) - center_y)
                if d < best_d:
                    best_d, best = d, (x, y, w, h)

            x, y, w, h = best
            cx, cy     = x + w // 2, y + h // 2

            cv2.rectangle(img, (x, y), (x + w, y + h), (60, 60, 255), 2)

            if abs(cx - center_x) < 70 and abs(cy - center_y) < 70 and w > 100:
                is_ready = True
                save_box = (x, y, w, h)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 80), 3)
                msg   = f"Giu nguyen! Chup goc {ANGLE_LABEL.get(current_angle, current_angle)}..."
                color = (0, 255, 80)
            else:
                msg   = "Dua mat vao giua khung hinh!"
                color = (0, 165, 255)

        # ── Lưu ảnh + kích hoạt pause khi đủ 5 ảnh ──────────────────────────
        if self.is_capturing and is_ready and save_box is not None:
            if now - self.last_save_time > 0.8:
                sx, sy, sw, sh = save_box
                face_crop = img[sy: sy + sh, sx: sx + sw]
                if face_crop.size > 0:
                    face_resized = cv2.resize(face_crop, (112, 112))
                    filename     = f"{current_angle}_{current_count}.jpg"
                    cv2.imwrite(os.path.join(path, filename), face_resized)
                    self.last_save_time = now

                    new_count = current_count + 1
                    if new_count >= self.limit_per_pos:
                        # Đủ 5 ảnh → bật pause 2.5 giây, thông báo chuyển góc
                        label = ANGLE_LABEL.get(current_angle, current_angle)
                        self.pause_msg   = f"Xong goc {label}!  {self.limit_per_pos}/{self.limit_per_pos} anh"
                        self.pause_until = now + 2.5
                    else:
                        msg   = f"Da luu {new_count}/{self.limit_per_pos} - Goc {ANGLE_LABEL.get(current_angle, current_angle)}"
                        color = (0, 255, 80)

        # ── Vẽ HUD ───────────────────────────────────────────────────────────
        cv2.drawMarker(img, (center_x, center_y),
                       (255, 255, 255), cv2.MARKER_CROSS, 30, 2)

        self._draw_progress(img, path, w_img, h_img)
        self._draw_label_bg(img, msg, (15, 38), scale=0.68, color=color)

        # Góc + tiến độ (top-right)
        label_str = f"{ANGLE_LABEL.get(current_angle, current_angle)}  [{current_count}/{self.limit_per_pos}]"
        (tw, _), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        self._draw_label_bg(img, label_str, (w_img - tw - 20, 38),
                            scale=0.6, color=(220, 220, 220))

        ret, jpeg = cv2.imencode(".jpg", img)
        return jpeg.tobytes() if ret else None

    # ── UI Helpers ────────────────────────────────────────────────────────────

    def _put_text_center(self, img, text, center, scale=0.8,
                         color=(255, 255, 255), thickness=2):
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        x = center[0] - tw // 2
        y = center[1] + th // 2
        cv2.putText(img, text, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

    def _draw_label_bg(self, img, text, pos, scale=0.68,
                       color=(255, 255, 255), thickness=2):
        """Vẽ text kèm nền tối bán trong suốt để dễ đọc."""
        (tw, th), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness
        )
        x, y = pos
        pad  = 6
        sub  = img[y - th - pad: y + baseline + pad, x - pad: x + tw + pad]
        if sub.size > 0:
            dark = sub.copy()
            cv2.rectangle(dark, (0, 0), (sub.shape[1], sub.shape[0]), (0, 0, 0), -1)
            img[y - th - pad: y + baseline + pad,
                x - pad: x + tw + pad] = cv2.addWeighted(sub, 0.3, dark, 0.7, 0)
        cv2.putText(img, text, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

    def _draw_progress(self, img, path, w_img, h_img):
        """Thanh tiến độ 5 góc phía dưới màn hình."""
        bar_h   = 30
        y_start = h_img - bar_h
        n       = len(self.angles)
        seg_w   = w_img // n

        for i, angle in enumerate(self.angles):
            count   = self._count_angle(path, angle)
            ratio   = min(count / self.limit_per_pos, 1.0)
            x0      = i * seg_w
            x1      = x0 + seg_w

            # Nền
            cv2.rectangle(img, (x0, y_start), (x1, h_img), (25, 25, 25), -1)
            # Fill
            fill_w = int((x1 - x0 - 2) * ratio)
            if fill_w > 0:
                fill_color = (0, 210, 90) if ratio >= 1.0 else (0, 150, 210)
                cv2.rectangle(img,
                              (x0 + 1, y_start + 2),
                              (x0 + 1 + fill_w, h_img - 2),
                              fill_color, -1)

            # Label
            label = ANGLE_LABEL.get(angle, angle)
            txt   = f"{label} {count}/{self.limit_per_pos}"
            (tw, _), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            tx = x0 + (seg_w - tw) // 2
            cv2.putText(img, txt, (tx, h_img - 9),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1, cv2.LINE_AA)

            # Đường kẻ phân cách
            if i > 0:
                cv2.line(img, (x0, y_start), (x0, h_img), (55, 55, 55), 1)