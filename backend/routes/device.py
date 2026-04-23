from flask import Blueprint, request, jsonify
from models import db, Device, DeviceLog
import datetime

device_bp = Blueprint("device", __name__)


# ── Lấy danh sách thiết bị ─────────────────────────────────────────────────
@device_bp.route("/", methods=["GET"])
def get_devices():
    devices = Device.query.all()
    return jsonify([{
        "id":          d.id,
        "name":        d.name,
        "type":        d.type,
        "room":        d.room,
        "sensor_type": d.sensor_type,
    } for d in devices])


# ── Lấy trạng thái hiện tại của tất cả thiết bị ───────────────────────────
@device_bp.route("/status", methods=["GET"])
def get_status():
    devices = Device.query.all()
    result = []
    for d in devices:
        last_log = DeviceLog.query.filter_by(device_id=d.id)\
                   .order_by(DeviceLog.timestamp.desc()).first()
        result.append({
            "id":     d.id,
            "name":   d.name,
            "type":   d.type,
            "room":   d.room,
            "status": last_log.status if last_log else 0,
            "mode":   last_log.mode   if last_log else "Manual",
        })
    return jsonify(result)


# ── Nhận dữ liệu cảm biến từ ESP32 + ghi log ──────────────────────────────
@device_bp.route("/sensor", methods=["POST"])
def update_sensor():
    data = request.json
    try:
        temp  = float(data.get("temp",  0))
        humi  = float(data.get("humi",  0))
        light = float(data.get("light", 0))
        gas   = float(data.get("gas",   0))

        # AI predict
        from services.ai import predict_behavior
        now = datetime.datetime.now()
        predictions = predict_behavior(temp, humi, light, now.hour, now.month)

        # Ghi log cho từng thiết bị AI điều khiển
        for device_id, status in predictions.items():
            log = DeviceLog(
                device_id = device_id,
                status    = status,
                mode      = "AI",
                temp      = temp,
                humi      = humi,
                light     = light,
                gas       = gas,
            )
            db.session.add(log)
        db.session.commit()

        return jsonify({"status": "ok", "predictions": predictions})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ── Bật tắt thủ công từ UI ─────────────────────────────────────────────────
@device_bp.route("/<int:device_id>/control", methods=["POST"])
def control_device(device_id):
    data   = request.json
    status = data.get("status")   # 0 | 1
    temp   = data.get("temp")
    humi   = data.get("humi")
    light  = data.get("light")
    gas    = data.get("gas")

    if status is None:
        return jsonify({"error": "Thiếu status"}), 400

    log = DeviceLog(
        device_id = device_id,
        status    = status,
        mode      = "Manual",
        temp      = temp,
        humi      = humi,
        light     = light,
        gas       = gas,
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"status": "ok"})


# ── Lấy lịch sử log của thiết bị ──────────────────────────────────────────
@device_bp.route("/<int:device_id>/logs", methods=["GET"])
def get_logs(device_id):
    limit = request.args.get("limit", 50, type=int)
    logs  = DeviceLog.query.filter_by(device_id=device_id)\
            .order_by(DeviceLog.timestamp.desc()).limit(limit).all()
    return jsonify([{
        "id":        l.id,
        "status":    l.status,
        "mode":      l.mode,
        "temp":      l.temp,
        "humi":      l.humi,
        "light":     l.light,
        "gas":       l.gas,
        "timestamp": l.timestamp.isoformat(),
    } for l in logs])