from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler
from models import db
from config import Config
import os

app = Flask(__name__)
app.config.from_object(Config)

# ── Database ───────────────────────────────────────────────────────────────
db.init_app(app)

# ── IP Guard Middleware ────────────────────────────────────────────────────
@app.before_request
def limit_remote_addr():
    """Chỉ cho phép truy cập từ mạng nội bộ (Local Network)"""
    client_ip = request.remote_addr
    
    # Cho phép localhost (cả IPv4 và IPv6) và dải IP nội bộ phổ biến
    is_local = (
        client_ip in ["127.0.0.1", "::1"] or 
        client_ip.startswith("192.168.") or 
        client_ip.startswith("10.") or
        client_ip.startswith("172.16.")
    )
    
    if not is_local:
        return jsonify({"error": f"Access Denied: Your IP ({client_ip}) is not on the local network."}), 403

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

# Tối ưu hóa: Ngăn scheduler khởi chạy 2 lần khi debug=True
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    scheduler.start()
    print("[INFO] APScheduler đã khởi động thành công!")

# ── Init folders & DB ──────────────────────────────────────────────────────
with app.app_context():
    os.makedirs(Config.CAPTURED_FACES_DIR, exist_ok=True)
    os.makedirs(Config.RECOG_IMAGES_DIR,   exist_ok=True)
    db.create_all()
    print("[INFO] Khởi tạo các thư mục lưu trữ dữ liệu ảnh và Database thành công!")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)