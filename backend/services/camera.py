import cv2
import os
import time


class VideoCamera(object):
    def __init__(self):
        self.video           = cv2.VideoCapture(0)
        self.face_cascade    = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
        self.limit_per_pos   = 5
        self.angles          = ["Thang", "Trai", "Phai", "Len", "Xuong"]
        self.last_save_time  = 0
        self.is_capturing    = False
        self.current_user    = ""

    def __del__(self):
        self.video.release()

    def get_frame(self):
        success, img = self.video.read()
        if not success:
            return None

        h_img, w_img, _ = img.shape
        center_x, center_y = w_img // 2, h_img // 2
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        current_angle = "Hoan thanh"
        path = f"captured_faces/{self.current_user}"

        if self.current_user:
            os.makedirs(path, exist_ok=True)
            for angle in self.angles:
                count = len([f for f in os.listdir(path) if f.startswith(angle)])
                if count < self.limit_per_pos:
                    current_angle = angle
                    current_count = count
                    break

        detected_faces = []
        is_ready = False
        msg, color = "Dang cho...", (0, 255, 255)

        if current_angle == "Thang":
            detected_faces = self.face_cascade.detectMultiScale(gray, 1.1, 6)
        elif current_angle == "Trai":
            detected_faces = self.profile_cascade.detectMultiScale(gray, 1.1, 6)
        elif current_angle == "Phai":
            detected_faces = self.profile_cascade.detectMultiScale(cv2.flip(gray, 1), 1.1, 6)
        elif current_angle in ["Len", "Xuong"]:
            detected_faces = self.face_cascade.detectMultiScale(gray, 1.2, 4)

        if len(detected_faces) > 0:
            for (x, y, w, h) in detected_faces:
                plot_x = w_img - x - w if current_angle == "Phai" else x
                f_cx, f_cy = plot_x + w // 2, y + h // 2
                cv2.rectangle(img, (plot_x, y), (plot_x + w, y + h), (255, 0, 0), 2)

                if abs(f_cx - center_x) < 60 and abs(f_cy - center_y) < 60 and w > 150:
                    is_ready = True
                    cv2.rectangle(img, (plot_x, y), (plot_x + w, y + h), (0, 255, 0), 3)
                else:
                    msg   = "HAY DUA MAT VAO GIUA TAM!"
                    color = (0, 165, 255)

            if self.is_capturing and is_ready:
                now = time.time()
                if now - self.last_save_time > 1.0:
                    face_crop = img[y:y + h, plot_x:plot_x + w]
                    if face_crop.size > 0:
                        face_resized = cv2.resize(face_crop, (112, 112))
                        cv2.imwrite(os.path.join(path, f"{current_angle}_{current_count}.jpg"), face_resized)
                        self.last_save_time = now
                        msg   = f"DA LUU {current_angle}: {current_count + 1}/5"
                        color = (0, 255, 0)
        else:
            if current_angle != "Hoan thanh":
                msg   = f"SAI HUONG! Quay sang: {current_angle}"
                color = (0, 0, 255)

        cv2.drawMarker(img, (center_x, center_y), (255, 255, 255), cv2.MARKER_CROSS, 30, 2)
        cv2.putText(img, msg, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        ret, jpeg = cv2.imencode(".jpg", img)
        return jpeg.tobytes()