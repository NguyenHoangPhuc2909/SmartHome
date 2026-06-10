import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── App ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret")

    # ── Database (SQLite cho nhẹ và đơn giản) ─────────────────────────────
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "smarthome.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Scheduler ─────────────────────────────────────────────────────────
    SCHEDULER_API_ENABLED = True

    # ── Upload ────────────────────────────────────────────────────────────
    CAPTURED_FACES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "captured_faces")
    RECOG_IMAGES_DIR   = os.path.join(os.path.abspath(os.path.dirname(__file__)), "recog_images")

    # ── Face Recognition Model (MobileFaceNet Embedding) ──────────────────
    FACE_MODEL_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "trained_models", "mobilefacenet.onnx")
    FACE_MODEL_RESNET34_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "trained_models", "resnet34.onnx")
    FACE_RECOGNITION_THRESHOLD = float(os.getenv("FACE_RECOGNITION_THRESHOLD", "0.6"))
    FACE_RECOGNITION_MARGIN = float(os.getenv("FACE_RECOGNITION_MARGIN", "0.05"))
    FACE_TEMPLATE_MAX_SAMPLES = int(os.getenv("FACE_TEMPLATE_MAX_SAMPLES", "40"))

    # Anti-spoofing model runs before face recognition.
    ANTISPOOF_ENABLED = os.getenv("ANTISPOOF_ENABLED", "1") == "1"
    ANTISPOOF_MODEL_PATH = os.getenv(
        "ANTISPOOF_MODEL_PATH",
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "trained_models", "antispoof.onnx"),
    )
    ANTISPOOF_THRESHOLD_CONFIG_PATH = os.getenv(
        "ANTISPOOF_THRESHOLD_CONFIG_PATH",
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "trained_models", "antispoof_threshold_config.json"),
    )
    ANTISPOOF_MODEL_INFO_PATH = os.getenv(
        "ANTISPOOF_MODEL_INFO_PATH",
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "trained_models", "antispoof_model_info.json"),
    )
    ANTISPOOF_LIVE_MAX_SCORE = float(os.getenv("ANTISPOOF_LIVE_MAX_SCORE", "0.65"))
    ANTISPOOF_SPOOF_MIN_SCORE = float(os.getenv("ANTISPOOF_SPOOF_MIN_SCORE", "0.90"))
    ANTISPOOF_MIN_FACE_RATIO = float(os.getenv("ANTISPOOF_MIN_FACE_RATIO", "0.16"))
    ANTISPOOF_MIN_BRIGHTNESS = float(os.getenv("ANTISPOOF_MIN_BRIGHTNESS", "35"))
    ANTISPOOF_MAX_BRIGHTNESS = float(os.getenv("ANTISPOOF_MAX_BRIGHTNESS", "235"))
    ANTISPOOF_MIN_BLUR = float(os.getenv("ANTISPOOF_MIN_BLUR", "18"))
    ANTISPOOF_DEBUG_ENABLED = os.getenv("ANTISPOOF_DEBUG_ENABLED", "1") == "1"
    ANTISPOOF_DEBUG_DIR = os.getenv(
        "ANTISPOOF_DEBUG_DIR",
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "antispoof_debug"),
    )
