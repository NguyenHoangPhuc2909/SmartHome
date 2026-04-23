from flask import Blueprint, request, jsonify
from models import db, AccessLog, FaceDataset, Device, DeviceLog
from config import Config
import os, datetime

access_bp = Blueprint("access", __name__)


# ── ESP32-CAM gửi ảnh lên nhận diện ───────────────────────────────────────
@access_bp.route("/recognize", methods=["POST"])
def recognize():
    if "image" not in request.files:
        return jsonify({"error": "Thiếu ảnh"}), 400

    image_file = request.files["image"]
    filename   = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    image_path = os.path.join(Config.RECOG_IMAGES_DIR, filename)
    image_file.save(image_path)

    # Nhận diện khuôn mặt
    from services.face_recognition import recognize_face
    matched_id, confidence = recognize_face(image_path)

    # Lấy thiết bị cửa
    door_device = Device.query.filter_by(type="door").first()
    if not door_device:
        return jsonify({"error": "Không tìm thấy thiết bị cửa"}), 404

    threshold = 0.75
    result    = "GRANTED" if matched_id and confidence >= threshold else "DENIED"
    is_alert  = result == "DENIED"

    # Ghi access log
    log = AccessLog(
        device_id          = door_device.id,
        matched_dataset_id = matched_id,
        image_path         = f"recog_images/{filename}",
        confidence         = confidence,
        result             = result,
        is_alert           = is_alert,
    )
    db.session.add(log)

    # Nếu GRANTED → mở cửa (ghi device log)
    if result == "GRANTED":
        device_log = DeviceLog(
            device_id = door_device.id,
            status    = 1,
            mode      = "Auto",
        )
        db.session.add(device_log)

    # Nếu DENIED → hú còi (ghi device log cho còi)
    if is_alert:
        alarm_device = Device.query.filter_by(type="alarm").first()
        if alarm_device:
            alarm_log = DeviceLog(
                device_id = alarm_device.id,
                status    = 1,
                mode      = "Alert",
            )
            db.session.add(alarm_log)

    db.session.commit()
    return jsonify({"result": result, "confidence": confidence})


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