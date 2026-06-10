import json

import cv2
import numpy as np

from config import Config
from models import FaceDataset
from services.embedding_helper import EmbeddingModel
from services.face_preprocessing import detect_and_align_face


face_model = EmbeddingModel.get_instance()


def get_face_crop(img):
    """Detect and align a face using the same 5-point ArcFace template as training."""
    try:
        return detect_and_align_face(img, score_threshold=0.8, output_size=(112, 112))
    except Exception as exc:
        print(f"[WARNING] YuNet alignment failed during recognition: {exc}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
    size = int(max(w, h) * 1.18)
    cx, cy = x + w // 2, y + h // 2
    x1, y1 = max(0, cx - size // 2), max(0, cy - size // 2)
    crop = img[y1:min(img.shape[0], y1 + size), x1:min(img.shape[1], x1 + size)]
    if crop is None or crop.size == 0:
        return None
    return cv2.resize(crop, (112, 112))


def _normalize_embedding(embedding):
    embedding = np.asarray(embedding, dtype=np.float32)
    return embedding / (np.linalg.norm(embedding) + 1e-8)


def _load_template(embedding_json):
    if not embedding_json:
        raise ValueError("Empty embedding JSON")
        
    raw = json.loads(embedding_json)

    # Nếu DB format là dạng list cũ (chỉ có mobilefacenet)
    if isinstance(raw, list):
        centroid = _normalize_embedding(raw)
        return centroid, np.empty((0, centroid.shape[0]), dtype=np.float32)

    centroid = _normalize_embedding(raw.get("centroid") or raw.get("mean"))
    samples = raw.get("samples") or []
    if samples:
        samples = np.asarray(samples, dtype=np.float32)
        samples = samples / (np.linalg.norm(samples, axis=1, keepdims=True) + 1e-8)
    else:
        samples = np.empty((0, centroid.shape[0]), dtype=np.float32)

    return centroid, samples


def _score_template(query_emb, centroid, samples):
    centroid_score = float(np.dot(query_emb, centroid))
    if samples.size == 0:
        return centroid_score

    sample_scores = samples @ query_emb
    top_count = min(3, len(sample_scores))
    top_mean = float(np.mean(np.sort(sample_scores)[-top_count:]))
    best_sample = float(np.max(sample_scores))

    # Same-person poses can vary; compare against the closest enrolled pose.
    return max(centroid_score, best_sample, 0.65 * best_sample + 0.35 * top_mean)


def recognize_face(image_path: str, threshold: float = 0.65, model_type: str = "mobilefacenet"):
    img = cv2.imread(image_path)
    if img is None:
        return None, 0.0

    query_crop = get_face_crop(img)
    if query_crop is None:
        return None, 0.0

    face_model = EmbeddingModel.get_instance(model_type)
    query_emb = face_model.extract_embedding(query_crop)
    if query_emb is None:
        return None, 0.0

    best_match_id = None
    best_score = 0.0
    second_score = 0.0

    for ds in FaceDataset.query.all():
        # Lấy đúng cột embedding tương ứng với model_type
        ds_embedding_json = ds.embedding_resnet34 if model_type == "resnet34" else ds.embedding
        if not ds_embedding_json:
            continue

        try:
            centroid, samples = _load_template(ds_embedding_json)
        except Exception as exc:
            print(f"[WARNING] Invalid embedding template for dataset {ds.id} with model {model_type}: {exc}")
            continue

        score = _score_template(query_emb, centroid, samples)
        if score > best_score:
            second_score = best_score
            best_score = score
            best_match_id = ds.id
        elif score > second_score:
            second_score = score

    confidence = max(0.0, min(1.0, best_score))
    has_second_candidate = second_score > 0.0
    margin_ok = (not has_second_candidate) or (
        (best_score - second_score) >= Config.FACE_RECOGNITION_MARGIN
    )

    if confidence >= threshold and margin_ok:
        return best_match_id, confidence

    return None, confidence
