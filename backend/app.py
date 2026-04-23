from flask import Flask
from flask_dance.contrib.google import make_google_blueprint
from flask_apscheduler import APScheduler
from models import db
from config import Config
import os

app = Flask(__name__)
app.config.from_object(Config)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

# ── Database ───────────────────────────────────────────────────────────────
db.init_app(app)

# ── Google OAuth ───────────────────────────────────────────────────────────
google_bp = make_google_blueprint(
    client_id     = Config.GOOGLE_CLIENT_ID,
    client_secret = Config.GOOGLE_CLIENT_SECRET,
    scope         = ["profile", "email"],
    redirect_to   = "auth.after_login",
)
app.register_blueprint(google_bp, url_prefix="/login")

# ── Routes ─────────────────────────────────────────────────────────────────
from routes.auth     import auth_bp
from routes.device   import device_bp
from routes.dataset  import dataset_bp
from routes.schedule import schedule_bp
from routes.access   import access_bp

app.register_blueprint(auth_bp)
app.register_blueprint(device_bp,   url_prefix="/api/devices")
app.register_blueprint(dataset_bp,  url_prefix="/api/datasets")
app.register_blueprint(schedule_bp, url_prefix="/api/schedules")
app.register_blueprint(access_bp,   url_prefix="/api/access")

# ── Scheduler (chạy schedules) ─────────────────────────────────────────────
scheduler = APScheduler()
scheduler.init_app(app)

@scheduler.task("interval", id="run_schedules", seconds=60, misfire_grace_time=10)
def run_schedules():
    from services.scheduler import check_schedules
    with app.app_context():
        check_schedules()

scheduler.start()

# ── Init folders & DB ──────────────────────────────────────────────────────
with app.app_context():
    os.makedirs(Config.CAPTURED_FACES_DIR, exist_ok=True)
    os.makedirs(Config.RECOG_IMAGES_DIR,   exist_ok=True)
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)