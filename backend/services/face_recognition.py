import cv2
import os
import numpy as np

# Import model MobileFaceNet
from services.embedding_helper import EmbeddingModel
from models import FaceDataset

face_model = EmbeddingModel.get_instance()

def get_face_crop(img):
    """Hàm phụ trợ: Tìm và cắt khuôn mặt sử dụng YuNet (đồng bộ với camera.py)"""
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

    # 1. TÌM VÀ CẮT KHUÔN MẶT TỪ ẢNH ESP32
    query_crop = get_face_crop(img)
    if query_crop is None:
        return None, 0.0 # Không thấy ai trong hình

    # 2. TRÍCH XUẤT ĐẶC TRƯNG (ẢNH CẦN NHẬN DIỆN)
    query_emb = face_model.extract_embedding(query_crop)
    if query_emb is None:
        return None, 0.0

    best_match_id = None
    min_distance = float('inf')

    # 3. SO SÁNH VỚI EMBEDDING CỦA TỪNG NGƯỜI TRONG DATASET
    datasets = FaceDataset.query.all()
    for ds in datasets:
        ds_emb = get_person_embedding(ds)
        if ds_emb is None:
            continue
            
        # Tính khoảng cách Cosine với vector đặc trưng trung bình của người đó
        dist = EmbeddingModel.cosine_distance(query_emb, ds_emb)
        
        if dist < min_distance:
            min_distance = dist
            best_match_id = ds.id

    # 4. TÍNH ĐỘ TỰ TIN
    confidence = 1.0 - min_distance if min_distance != float('inf') else 0.0

    if confidence >= threshold:
        return best_match_id, confidence

    return None, confidence

# ── CACHE EMBEDDING ĐỂ TĂNG TỐC ĐỘ ─────────────────────────────────────────
_EMBEDDINGS_CACHE = {}

def get_person_embedding(ds):
    """
    Tính vector đặc trưng (Embedding) trung bình của một người.
    Kết quả được lưu vào biến Cache trong RAM để so sánh siêu tốc trong tương lai.
    """
    global _EMBEDDINGS_CACHE
    path = f"captured_faces/{ds.name}"
    if not os.path.exists(path):
        return None
    
    files = [f for f in os.listdir(path) if f.endswith(".jpg")]
    if not files:
        return None
        
    # Tạo khoá cache dựa trên ID người dùng và số lượng ảnh
    # (Nếu họ chụp thêm ảnh, số lượng ảnh thay đổi -> Tự động tính lại)
    cache_key = f"{ds.id}_{len(files)}"
    if cache_key in _EMBEDDINGS_CACHE:
        return _EMBEDDINGS_CACHE[cache_key]
        
    embeddings = []
    for fname in files:
        fpath = os.path.join(path, fname)
        ds_img = cv2.imread(fpath)
        if ds_img is None:
            continue
            
        # ⚠️ QUAN TRỌNG: Ảnh Dataset ĐÃ ĐƯỢC CẮT CHUẨN 112x112 LÚC CHỤP
        # Không được dùng get_face_crop() để cắt lại nữa, nếu không sẽ bị lỗi
        emb = face_model.extract_embedding(ds_img)
        if emb is not None:
            embeddings.append(emb)
            
    if not embeddings:
        return None
        
    # Tính Vector trung bình cộng (Mean Embedding) để đại diện cho người đó
    mean_emb = np.mean(embeddings, axis=0)
    # Chuẩn hoá lại vector (Normalize)
    mean_emb = mean_emb / np.linalg.norm(mean_emb)
    
    _EMBEDDINGS_CACHE[cache_key] = mean_emb
    return mean_emb