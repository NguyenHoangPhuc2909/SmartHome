import cv2
import os
import numpy as np


def recognize_face(image_path: str, threshold: float = 0.75):
    """
    So sánh ảnh từ ESP32 với toàn bộ dataset trong captured_faces/.
    Trả về (matched_dataset_id, confidence) hoặc (None, 0.0) nếu không khớp.
    """
    from models import FaceDataset

    img = cv2.imread(image_path)
    if img is None:
        return None, 0.0

    gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade   = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces     = cascade.detectMultiScale(gray, 1.1, 5)

    if len(faces) == 0:
        return None, 0.0

    # Lấy khuôn mặt lớn nhất
    x, y, w, h  = max(faces, key=lambda f: f[2] * f[3])
    face_crop   = cv2.resize(gray[y:y + h, x:x + w], (112, 112))

    recognizer  = cv2.face.LBPHFaceRecognizer_create()
    labels      = []
    faces_train = []
    dataset_map = {}  # label index → dataset id

    datasets = FaceDataset.query.all()
    for idx, ds in enumerate(datasets):
        path = f"captured_faces/{ds.name}"
        if not os.path.exists(path):
            continue
        for fname in os.listdir(path):
            if not fname.endswith(".jpg"):
                continue
            fpath    = os.path.join(path, fname)
            face_img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            face_img = cv2.resize(face_img, (112, 112))
            faces_train.append(face_img)
            labels.append(idx)
        dataset_map[idx] = ds.id

    if not faces_train:
        return None, 0.0

    recognizer.train(faces_train, np.array(labels))
    label, dist = recognizer.predict(face_crop)

    # LBPH: dist càng nhỏ càng giống — chuyển sang confidence 0.0–1.0
    confidence = max(0.0, 1.0 - dist / 100.0)

    if confidence >= threshold:
        return dataset_map.get(label), confidence

    return None, confidence