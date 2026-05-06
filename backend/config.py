import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── App ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret")

    # ── Google OAuth ───────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    # ── MySQL ──────────────────────────────────────────────────────────────
    MYSQL_HOST     = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT     = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER     = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB       = os.getenv("MYSQL_DB", "smarthome")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
        f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
        f"/{os.getenv('MYSQL_DB', 'smarthome')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Scheduler ─────────────────────────────────────────────────────────
    SCHEDULER_API_ENABLED = True

    # ── Upload ────────────────────────────────────────────────────────────
    CAPTURED_FACES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "captured_faces")
    RECOG_IMAGES_DIR   = os.path.join(os.path.abspath(os.path.dirname(__file__)), "recog_images")


    # ── Face Recognition Model (MobileFaceNet Embedding) ──────────────────
    FACE_MODEL_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "trained_models", "mobilefacenet.onnx")
    FACE_RECOGNITION_THRESHOLD = 0.65  # Confidence threshold (0-1)