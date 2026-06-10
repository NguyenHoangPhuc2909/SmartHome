import json
import os

import cv2
import numpy as np
import onnxruntime as ort

from config import Config
from services.face_preprocessing import best_face, detect_faces_yunet


class AntiSpoofModel:
    _instance = None

    @staticmethod
    def get_instance():
        if AntiSpoofModel._instance is None:
            AntiSpoofModel._instance = AntiSpoofModel()
        return AntiSpoofModel._instance

    def __init__(self):
        if not os.path.exists(Config.ANTISPOOF_MODEL_PATH):
            raise FileNotFoundError(f"Anti-spoof model not found: {Config.ANTISPOOF_MODEL_PATH}")
        if not os.path.exists(Config.ANTISPOOF_THRESHOLD_CONFIG_PATH):
            raise FileNotFoundError(
                f"Anti-spoof threshold config not found: {Config.ANTISPOOF_THRESHOLD_CONFIG_PATH}"
            )

        with open(Config.ANTISPOOF_THRESHOLD_CONFIG_PATH, "r", encoding="utf-8") as f:
            threshold_config = json.load(f)

        model_info = {}
        if os.path.exists(Config.ANTISPOOF_MODEL_INFO_PATH):
            with open(Config.ANTISPOOF_MODEL_INFO_PATH, "r", encoding="utf-8") as f:
                model_info = json.load(f)

        input_info = threshold_config.get("input", {})
        self.image_size = int(input_info.get("image_size") or model_info.get("input", {}).get("image_size") or 224)
        self.crop_scale = float(input_info.get("face_crop_scale", 1.45))
        self.threshold = float(threshold_config.get("threshold_from_val", 0.5))
        self.live_max_score = float(Config.ANTISPOOF_LIVE_MAX_SCORE)
        self.spoof_min_score = float(Config.ANTISPOOF_SPOOF_MIN_SCORE)
        if self.live_max_score >= self.spoof_min_score:
            self.live_max_score = min(self.threshold, 0.65)
            self.spoof_min_score = max(self.threshold, 0.90)

        self.session = ort.InferenceSession(
            Config.ANTISPOOF_MODEL_PATH,
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]

        print(
            "[INFO] Anti-spoof model loaded: "
            f"{Config.ANTISPOOF_MODEL_PATH}, input={self.input_name}, "
            f"outputs={self.output_names}, threshold={self.threshold}, "
            f"live_max={self.live_max_score}, spoof_min={self.spoof_min_score}"
        )

    def predict_file(self, image_path):
        image_bgr = cv2.imread(image_path)
        if image_bgr is None:
            return self._empty_result("ERROR", "Cannot read image")
        return self.predict_bgr(image_bgr)

    def predict_bgr(self, image_bgr):
        crop_bgr, crop_info = crop_face_for_antispoof(image_bgr, self.crop_scale, self.image_size)
        if crop_bgr is None:
            return self._empty_result("NO_FACE", "No face detected")

        quality = _image_quality(crop_bgr, crop_info)
        quality_error = _quality_error(quality)
        if quality_error:
            return self._uncertain_result(quality_error, quality, crop_info)

        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        model_input = np.expand_dims(crop_rgb.astype(np.float32), axis=0)

        outputs = self.session.run(self.output_names, {self.input_name: model_input})
        output_map = dict(zip(self.output_names, outputs))

        prob_spoof_arr = output_map.get("prob_spoof")
        type_prob_arr = output_map.get("type_prob")

        if prob_spoof_arr is None:
            prob_spoof_arr = outputs[0]
        prob_spoof = float(np.ravel(prob_spoof_arr)[0])

        attack_type = None
        attack_probability = None
        type_prob = None
        if type_prob_arr is not None:
            type_prob = np.ravel(type_prob_arr).astype(float)
            if len(type_prob) >= 2:
                attack_idx = int(np.argmax(type_prob[:2]))
                attack_type = "print" if attack_idx == 0 else "replay"
                attack_probability = float(type_prob[attack_idx])

        if prob_spoof < self.live_max_score:
            label = "LIVE"
        elif prob_spoof >= self.spoof_min_score:
            label = "SPOOF"
        else:
            label = "UNCERTAIN"
        is_live = label == "LIVE"

        return {
            "ok": True,
            "face_found": True,
            "is_live": is_live,
            "label": label,
            "prob_spoof": prob_spoof,
            "threshold": self.threshold,
            "live_max_score": self.live_max_score,
            "spoof_min_score": self.spoof_min_score,
            "attack_type": attack_type,
            "attack_probability": attack_probability,
            "type_prob": type_prob.tolist() if type_prob is not None else None,
            "box": crop_info.get("crop_box"),
            "face_box": crop_info.get("face_box"),
            "quality": quality,
            "error": None,
        }

    def _empty_result(self, label, error):
        return {
            "ok": False,
            "face_found": False,
            "is_live": False,
            "label": label,
            "prob_spoof": 1.0,
            "threshold": self.threshold,
            "live_max_score": self.live_max_score,
            "spoof_min_score": self.spoof_min_score,
            "attack_type": None,
            "attack_probability": None,
            "type_prob": None,
            "box": None,
            "face_box": None,
            "quality": None,
            "error": error,
        }

    def _uncertain_result(self, error, quality, crop_info):
        return {
            "ok": False,
            "face_found": True,
            "is_live": False,
            "label": "UNCERTAIN",
            "prob_spoof": None,
            "threshold": self.threshold,
            "live_max_score": self.live_max_score,
            "spoof_min_score": self.spoof_min_score,
            "attack_type": None,
            "attack_probability": None,
            "type_prob": None,
            "box": crop_info.get("crop_box"),
            "face_box": crop_info.get("face_box"),
            "quality": quality,
            "error": error,
        }


def crop_face_for_antispoof(image_bgr, crop_scale=1.45, output_size=224):
    face = best_face(detect_faces_yunet(image_bgr, score_threshold=0.75))
    if face is None:
        face = _detect_face_haar(image_bgr)
    if face is None:
        return None, None

    x, y, w, h = [float(v) for v in face[:4]]
    img_h, img_w = image_bgr.shape[:2]
    side = max(w, h) * float(crop_scale)
    cx = x + w / 2.0
    cy = y + h / 2.0

    x1 = int(round(cx - side / 2.0))
    y1 = int(round(cy - side / 2.0))
    x2 = int(round(cx + side / 2.0))
    y2 = int(round(cy + side / 2.0))

    pad_left = max(0, -x1)
    pad_top = max(0, -y1)
    pad_right = max(0, x2 - img_w)
    pad_bottom = max(0, y2 - img_h)

    x1_clamped = max(0, x1)
    y1_clamped = max(0, y1)
    x2_clamped = min(img_w, x2)
    y2_clamped = min(img_h, y2)

    crop = image_bgr[y1_clamped:y2_clamped, x1_clamped:x2_clamped]
    if crop is None or crop.size == 0:
        return None, None

    if any(v > 0 for v in [pad_left, pad_top, pad_right, pad_bottom]):
        crop = cv2.copyMakeBorder(
            crop,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            cv2.BORDER_REPLICATE,
        )

    crop = cv2.resize(crop, (output_size, output_size), interpolation=cv2.INTER_AREA)
    crop_info = {
        "crop_box": (x1_clamped, y1_clamped, x2_clamped, y2_clamped),
        "face_box": (int(round(x)), int(round(y)), int(round(x + w)), int(round(y + h))),
        "face_ratio": float(max(w, h) / max(1, min(img_w, img_h))),
        "crop_scale": float(crop_scale),
    }
    return crop, crop_info


def _image_quality(crop_bgr, crop_info):
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    return {
        "brightness": float(np.mean(gray)),
        "blur": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "face_ratio": float(crop_info.get("face_ratio", 0.0)),
        "crop_scale": float(crop_info.get("crop_scale", 0.0)),
    }


def _quality_error(quality):
    if quality["face_ratio"] < Config.ANTISPOOF_MIN_FACE_RATIO:
        return "FACE_TOO_SMALL"
    if quality["brightness"] < Config.ANTISPOOF_MIN_BRIGHTNESS:
        return "LOW_LIGHT"
    if quality["brightness"] > Config.ANTISPOOF_MAX_BRIGHTNESS:
        return "OVEREXPOSED"
    if quality["blur"] < Config.ANTISPOOF_MIN_BLUR:
        return "BLURRY"
    return None


def _detect_face_haar(image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    return max(faces, key=lambda item: item[2] * item[3])
