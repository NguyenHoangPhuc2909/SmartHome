from flask import Blueprint, request, jsonify, session
from models import db, AccessLog, FaceDataset, Device, ActuatorLog, User
from extensions import socketio
from config import Config
import os, datetime
import onnxruntime as ort
import numpy as np
import cv2

# Import class EmbeddingModel
from services.embedding_helper import EmbeddingModel
from services.mqtt_service import publish_command

# Lấy instance của model
face_model = EmbeddingModel.get_instance()

access_bp = Blueprint("access", __name__)


# ── Lấy lịch sử nhận diện ─────────────────────────────────────────────────
@access_bp.route("/logs", methods=["GET"])
def get_logs():
    limit = request.args.get("limit", 50, type=int)
    logs  = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(limit).all()
    return jsonify([{
        "id":                 l.id,
        "matched_dataset_id": l.matched_dataset_id,
        "matched_name":       l.matched_dataset.name if l.matched_dataset else None,
        "image_path":         l.image_path,
        "confidence":         l.confidence,
        "result":             l.result,
        "is_alert":           l.is_alert,
        "timestamp":          l.timestamp.isoformat(),
    } for l in logs])

# ── Lấy ảnh nhận diện mới nhất ──────────────────────────────────────────
@access_bp.route("/latest-image", methods=["GET"])
def get_latest_image():
    """Trả về ảnh nhận diện mới nhất (dùng cho live preview)"""
    import glob
    from flask import send_file
    
    recog_dir = Config.RECOG_IMAGES_DIR
    if not os.path.exists(recog_dir):
        return jsonify({"error": "Thư mục không tồn tại"}), 404
    
    # Lấy file mới nhất
    files = glob.glob(os.path.join(recog_dir, "*.jpg"))
    if not files:
        return jsonify({"error": "Không có ảnh"}), 404
    
    latest_file = max(files, key=os.path.getctime)
    return send_file(latest_file, mimetype="image/jpeg")

# ── Lấy ảnh theo ID của log ──────────────────────────────────────────────────
@access_bp.route("/image/<int:log_id>", methods=["GET"])
def get_log_image(log_id):
    from flask import send_file
    log = AccessLog.query.get(log_id)
    if not log or not log.image_path:
        return jsonify({"error": "Không tìm thấy ảnh"}), 404
        
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    image_full_path = os.path.join(base_dir, log.image_path)
    
    if not os.path.exists(image_full_path):
        return jsonify({"error": "File ảnh không tồn tại"}), 404
        
    return send_file(image_full_path, mimetype="image/jpeg")

# ── Webhook từ ESP32-CAM ─────────────────────────────────────────────
@access_bp.route("/recognize", methods=["POST"])
def recognize():
    filename   = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    image_path = os.path.join(Config.RECOG_IMAGES_DIR, filename)
    os.makedirs(Config.RECOG_IMAGES_DIR, exist_ok=True)

    if "image" in request.files:
        image_file = request.files["image"]
        image_file.save(image_path)
    elif request.get_data():
        with open(image_path, "wb") as f:
            f.write(request.get_data())
    else:
        return jsonify({"error": "Thiếu ảnh"}), 400

    # Nhận diện khuôn mặt
    from services.face_recognition import recognize_face
    matched_id, confidence = recognize_face(image_path, threshold=Config.FACE_RECOGNITION_THRESHOLD)

    # Lấy thông tin dataset
    matched_name = None
    if matched_id:
        ds = FaceDataset.query.get(matched_id)
        if ds:
            matched_name = ds.name

    # Tự động tạo thiết bị cửa giả lập nếu chưa có
    door_device = Device.query.filter_by(type="door").first()
    if not door_device:
        door_device = Device(type="door", room="Phòng Khách", name="Cửa chính")
        db.session.add(door_device)
        db.session.commit()

    # Quyết định: GRANTED hay DENIED
    result    = "GRANTED" if matched_id and confidence >= Config.FACE_RECOGNITION_THRESHOLD else "DENIED"
    is_alert  = result == "DENIED"

    # Ghi access log
    log = AccessLog(
        device_id          = door_device.id,
        matched_dataset_id = matched_id,
        image_path         = f"recog_images/{filename}",
        confidence         = float(confidence),
        result             = result,
        is_alert           = is_alert,
    )
    db.session.add(log)

    # Nếu GRANTED → ghi log mở cửa
    if result == "GRANTED":
        publish_command("myiot/home/commands/servo", "1")
        device_log = ActuatorLog(
            device_id = door_device.id,
            status    = 1,
            mode      = "Auto",
        )
        db.session.add(device_log)

    # Nếu DENIED → ghi log hú còi (chỉ gửi lệnh cảnh báo, còi hú hay không do ESP32 quyết định dựa vào tính năng bật/tắt còi)
    if is_alert:
        publish_command("myiot/home/commands/alert", "1")
        alarm_device = Device.query.filter_by(type="alarm").first()
        if not alarm_device:
            alarm_device = Device(type="alarm", room="Phòng Khách", name="Còi báo động")
            db.session.add(alarm_device)
            db.session.commit()
            
        alarm_log = ActuatorLog(
            device_id = alarm_device.id,
            status    = 1,
            mode      = "Alert",
        )
        db.session.add(alarm_log)

    db.session.commit()
    socketio.emit("refresh_access_logs", namespace="/")
    socketio.emit("refresh_devices", namespace="/")

    return jsonify({
        "result":        result,
        "confidence":    float(confidence),
        "matched_name":  matched_name,
        "image_path":    f"recog_images/{filename}",
    })
