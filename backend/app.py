import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from models import db
from config import Config
import os

from extensions import socketio

app = Flask(__name__)
app.config.from_object(Config)

# ── Database ───────────────────────────────────────────────────────────────
db.init_app(app)

# ── Socket.IO ──────────────────────────────────────────────────────────────
socketio.init_app(app)

# ── MQTT ───────────────────────────────────────────────────────────────────
from services.mqtt_service import start_mqtt
start_mqtt(app)

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
def run_schedules_loop():
    import time
    from services.scheduler import check_schedules
    while True:
        # Thay vì ngủ fix cứng 60s, ta tính số giây còn lại để đến tròn phút tiếp theo
        current_second = time.localtime().tm_sec
        sleep_time = 60 - current_second
        socketio.sleep(sleep_time)
        
        with app.app_context():
            try:
                executed = check_schedules()
                if executed:
                    socketio.emit("refresh_devices", namespace="/")
            except Exception as e:
                print(f"[ERROR] Scheduler error: {e}")

# Tối ưu hóa: Ngăn scheduler khởi chạy 2 lần khi debug=True
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    socketio.start_background_task(run_schedules_loop)
    print("[INFO] Background scheduler started successfully!")

# ── Init folders & DB ──────────────────────────────────────────────────────
with app.app_context():
    os.makedirs(Config.CAPTURED_FACES_DIR, exist_ok=True)
    os.makedirs(Config.RECOG_IMAGES_DIR,   exist_ok=True)
    db.create_all()
    
    # Tự động tạo 4 thiết bị (đèn pk, đèn pn, quạt pk, quạt pn) nếu chưa có
    try:
        from services.ai import ensure_devices_exist
        ensure_devices_exist()
    except Exception as e:
        print(f"[WARNING] Could not initialize devices: {e}")
        
    print("[INFO] Initialized storage folders and database successfully!")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)