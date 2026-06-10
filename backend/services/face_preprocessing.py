import os

import cv2
import numpy as np


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YUNET_MODEL_PATH = os.path.join(BASE_DIR, "trained_models", "face_detection_yunet.onnx")

# ArcFace/MobileFaceNet 112x112 reference points used by the training notebook.
REFERENCE_FACIAL_POINTS = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


def detect_faces_yunet(img_bgr, score_threshold=0.8):
    if img_bgr is None or img_bgr.size == 0:
        return []

    h, w = img_bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        model=YUNET_MODEL_PATH,
        config="",
        input_size=(w, h),
        score_threshold=score_threshold,
        nms_threshold=0.3,
        top_k=5000,
    )
    _, faces = detector.detect(img_bgr)
    if faces is None:
        return []
    return list(faces)


def best_face(faces):
    if not faces:
        return None
    return max(faces, key=lambda face: face[-1])


def crop_face_square(img_bgr, face, padding=1.18, output_size=(112, 112)):
    x, y, w, h = [int(v) for v in face[:4]]
    size = int(max(w, h) * padding)
    center_x = x + w // 2
    center_y = y + h // 2

    x1 = max(0, center_x - size // 2)
    y1 = max(0, center_y - size // 2)
    x2 = min(img_bgr.shape[1], x1 + size)
    y2 = min(img_bgr.shape[0], y1 + size)

    crop = img_bgr[y1:y2, x1:x2]
    if crop is None or crop.size == 0:
        return None
    if output_size:
        crop = cv2.resize(crop, output_size)
    return crop


def _landmarks_for_arcface(face):
    if len(face) < 15:
        return None

    eye_a = np.array(face[4:6], dtype=np.float32)
    eye_b = np.array(face[6:8], dtype=np.float32)
    nose = np.array(face[8:10], dtype=np.float32)
    mouth_a = np.array(face[10:12], dtype=np.float32)
    mouth_b = np.array(face[12:14], dtype=np.float32)

    left_eye, right_eye = sorted([eye_a, eye_b], key=lambda point: point[0])
    mouth_left, mouth_right = sorted([mouth_a, mouth_b], key=lambda point: point[0])

    return np.array(
        [left_eye, right_eye, nose, mouth_left, mouth_right],
        dtype=np.float32,
    )


def align_face_from_landmarks(img_bgr, face, output_size=(112, 112)):
    src = _landmarks_for_arcface(face)
    if src is None:
        return None

    matrix, _ = cv2.estimateAffinePartial2D(
        src,
        REFERENCE_FACIAL_POINTS,
        method=cv2.LMEDS,
    )
    if matrix is None:
        return None

    return cv2.warpAffine(
        img_bgr,
        matrix,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderValue=0.0,
    )


def align_or_crop_face(img_bgr, face, output_size=(112, 112)):
    aligned = align_face_from_landmarks(img_bgr, face, output_size=output_size)
    if aligned is not None and aligned.size > 0:
        return aligned
    return crop_face_square(img_bgr, face, output_size=output_size)


def detect_and_align_face(img_bgr, score_threshold=0.8, output_size=(112, 112)):
    face = best_face(detect_faces_yunet(img_bgr, score_threshold=score_threshold))
    if face is None:
        return None
    return align_or_crop_face(img_bgr, face, output_size=output_size)
