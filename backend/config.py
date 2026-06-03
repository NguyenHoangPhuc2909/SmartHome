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
    FACE_RECOGNITION_THRESHOLD = 0.55  # Confidence threshold (0-1)