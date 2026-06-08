import cv2
import os
import numpy as np
import json

# Import model MobileFaceNet
from services.embedding_helper import EmbeddingModel
from models import FaceDataset

face_model = EmbeddingModel.get_instance()

def get_face_crop(img, scale=1.1):
    """Hàm phụ trợ: Tìm và cắt khuôn mặt sử dụng YuNet (đồng bộ với camera.py)"""
    img_to_crop = img
    try:
        detector = cv2.FaceDetectorYN.create(
            model="trained_models/face_detection_yunet.onnx",
            config="",
            input_size=(img.shape[1], img.shape[0]),
            score_threshold=0.8,
            nms_threshold=0.3,
            top_k=5000
        )
        _, faces = detector.detect(img)
        if faces is not None and len(faces) > 0:
            # Chọn khuôn mặt có điểm tự tin cao nhất
            best_face = max(faces, key=lambda f: f[-1])
            x, y, w, h = best_face[:4].astype(int)
            
            if len(best_face) >= 14:
                re_x, re_y = best_face[4], best_face[5]
                le_x, le_y = best_face[6], best_face[7]
                if re_x > le_x:
                    re_x, re_y, le_x, le_y = le_x, le_y, re_x, re_y
                dx = le_x - re_x
                dy = le_y - re_y
                if dx > 0:
                    angle = np.degrees(np.arctan2(dy, dx))
                    if abs(angle) < 45:
                        cx, cy = x + w // 2, y + h // 2
                        M = cv2.getRotationMatrix2D((float(cx), float(cy)), angle, 1.0)
                        img_to_crop = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_CUBIC)
        else:
            return None
    except Exception as e:
        print(f"[CẢNH BÁO] Không load được YuNet trong nhận diện: {e}")
        # Fallback xuống Haar
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    # Ép khung cắt thành hình vuông bằng cách lấy cạnh lớn hơn
    size = int(max(w, h) * scale)
    
    # Tính toán lại x, y để giữ tâm khuôn mặt ở giữa
    center_x = x + w // 2
    center_y = y + h // 2
    
    new_x = max(0, center_x - size // 2)
    new_y = max(0, center_y - size // 2)
    
    # Đảm bảo không bị tràn viền ảnh gốc
    new_x_end = min(img_to_crop.shape[1], new_x + size)
    new_y_end = min(img_to_crop.shape[0], new_y + size)
    
    # Cắt ảnh vuông
    face_crop = img_to_crop[new_y:new_y_end, new_x:new_x_end]
    return face_crop


def crop_face_liveness(img, scale=1.45):
    """Cắt ảnh khuôn mặt cho liveness sử dụng Haar Cascade (đồng bộ chính xác với notebook)"""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
        cx, cy = x + w / 2, y + h / 2
        side = max(w, h) * scale
        x1, y1 = int(cx - side / 2), int(cy - side / 2)
        x2, y2 = int(cx + side / 2), int(cy + side / 2)
        H, W = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(W, x2), min(H, y2)
        return img[y1:y2, x1:x2]
    except Exception as e:
        print(f"[CẢNH BÁO] Lỗi khi crop liveness bằng Haar Cascade: {e}")
        return None


def recognize_face(image_path: str, threshold: float = 0.65):
    img = cv2.imread(image_path)
    if img is None:
        return None, 0.0

    # 1. TÌM VÀ CẮT KHUÔN MẶT
    query_crop = get_face_crop(img)
    if query_crop is None:
        return None, 0.0 

    # 2. TRÍCH XUẤT ĐẶC TRƯNG NGƯỜI ĐANG ĐỨNG TRƯỚC CAM
    query_emb = face_model.extract_embedding(query_crop)
    if query_emb is None:
        return None, 0.0

    best_match_id = None
    min_distance = float('inf')

    # 3. SO SÁNH VỚI EMBEDDING TỪ DATABASE (SIÊU NHANH)
    datasets = FaceDataset.query.all()
    for ds in datasets:
        # Bỏ qua nếu người này chưa được tính vector (chưa ấn Dừng chụp hoặc code cũ)
        if not ds.embedding:
            continue 
            
        # Parse JSON string trở lại thành mảng Numpy
        ds_emb = np.array(json.loads(ds.embedding), dtype=np.float32)
        
        # Tính khoảng cách Cosine
        dist = EmbeddingModel.cosine_distance(query_emb, ds_emb)
        
        if dist < min_distance:
            min_distance = dist
            best_match_id = ds.id

    # 4. TÍNH ĐỘ TỰ TIN
    confidence = 1.0 - min_distance if min_distance != float('inf') else 0.0

    # 5. QUYẾT ĐỊNH KẾT QUẢ
    if confidence >= threshold:
        return best_match_id, confidence

    return None, confidence