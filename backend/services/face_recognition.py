import cv2
import os
import numpy as np

# Import model MobileFaceNet
from services.embedding_helper import EmbeddingModel
from models import FaceDataset

face_model = EmbeddingModel.get_instance()

# Load Haar Cascade để dò tìm vị trí khuôn mặt
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def get_face_crop(img):
    """Hàm phụ trợ: Tìm và cắt khuôn mặt (ép thành hình vuông)"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    
    if len(faces) == 0:
        return None
        
    # Lấy khuôn mặt lớn nhất
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    
    # Ép khung cắt thành hình vuông bằng cách lấy cạnh lớn hơn
    size = max(w, h)
    
    # Tính toán lại x, y để giữ tâm khuôn mặt ở giữa
    center_x = x + w // 2
    center_y = y + h // 2
    
    new_x = max(0, center_x - size // 2)
    new_y = max(0, center_y - size // 2)
    
    # Đảm bảo không bị tràn viền ảnh gốc
    new_x_end = min(img.shape[1], new_x + size)
    new_y_end = min(img.shape[0], new_y + size)
    
    # Cắt ảnh vuông
    face_crop = img[new_y:new_y_end, new_x:new_x_end]
    return face_crop

def recognize_face(image_path: str, threshold: float = 0.65):
    img = cv2.imread(image_path)
    if img is None:
        return None, 0.0

    # 1. TÌM VÀ CẮT KHUÔN MẶT TỪ ẢNH ESP32/LAPTOP
    query_crop = get_face_crop(img)
    if query_crop is None:
        return None, 0.0 # Không thấy ai trong hình

    # 2. TRÍCH XUẤT ĐẶC TRƯNG (1 BƯỚC CNN)
    query_emb = face_model.extract_embedding(query_crop)

    best_match_id = None
    min_distance = float('inf')

    # 3. ĐỌC DATASET VÀ SO SÁNH
    datasets = FaceDataset.query.all()
    for ds in datasets:
        path = f"captured_faces/{ds.name}"
        if not os.path.exists(path):
            continue
        
        for fname in os.listdir(path):
            if not fname.endswith(".jpg"):
                continue
            
            fpath = os.path.join(path, fname)
            ds_img = cv2.imread(fpath)
            if ds_img is None:
                continue
            
            # Cắt khuôn mặt từ ảnh trong Dataset (Đảm bảo công bằng khi so sánh)
            ds_crop = get_face_crop(ds_img)
            if ds_crop is None:
                continue # Bỏ qua ảnh dataset nếu không thấy mặt
                
            # Trích xuất embedding
            ds_emb = face_model.extract_embedding(ds_crop)
            
            # Tính khoảng cách Cosine
            dist = EmbeddingModel.cosine_distance(query_emb, ds_emb)
            
            if dist < min_distance:
                min_distance = dist
                best_match_id = ds.id

    # 4. TÍNH ĐỘ TỰ TIN
    confidence = 1.0 - min_distance if min_distance != float('inf') else 0.0

    if confidence >= threshold:
        return best_match_id, confidence

    return None, confidence