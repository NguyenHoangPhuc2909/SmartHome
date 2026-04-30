import os
import datetime
from flask import Blueprint, request, jsonify
from models import db, Device, DeviceLog

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


# ── LUỒNG 2: ESP32 HỎI TRẠNG THÁI (GET /status) ───────────────────────────
@device_bp.route("/status", methods=["GET"])
def get_status():
    devices = Device.query.all()
    result = []
    for d in devices:
        last_log = DeviceLog.query.filter_by(device_id=d.id)\
                   .order_by(DeviceLog.timestamp.desc()).first()
        
        # Trả về mảng JSON đúng chuẩn ESP32 cần đọc
        result.append({
            "id":     d.id,
            "name":   d.name,
            "type":   d.type,
            "room":   d.room,
            "status": last_log.status if last_log else 0,
            "mode":   last_log.mode   if last_log else "AI",
        })
    return jsonify(result)


# ── LUỒNG 1: ESP32 GỬI CẢM BIẾN LÊN (POST /sensor) ────────────────────────
@device_bp.route("/sensor", methods=["POST"])
def update_sensor():
    data = request.json
    try:
        temp  = float(data.get("temp",  0))
        humi  = float(data.get("humi",  0))
        light = float(data.get("light", 0))
        gas   = float(data.get("gas",   0))

        now = datetime.datetime.now()
        
        # AI predict
        from services.ai import predict_behavior
        predictions = predict_behavior(temp, humi, light, now)

        # Ghi log cho từng thiết bị
        for device_id, predicted_status in predictions.items():
            last_log = DeviceLog.query.filter_by(device_id=device_id)\
                        .order_by(DeviceLog.timestamp.desc()).first()
            
            # Nếu người dùng đang chỉnh tay trên Web, AI không được phép can thiệp
            if last_log and last_log.mode == "Manual":
                continue 
                
            # Chỉ ghi log mới nếu AI thay đổi trạng thái (tối ưu DB)
            if last_log and last_log.status == predicted_status and last_log.mode == "AI":
                continue

            log = DeviceLog(
                device_id = device_id,
                status    = predicted_status,
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
        return jsonify({"status": "error", "message": str(e)}), 500


# ── LUỒNG 3: WEB UI ĐIỀU KHIỂN (POST /<id>/control) ───────────────────────
@device_bp.route("/<int:device_id>/control", methods=["POST"])
def control_device(device_id):
    data   = request.json
    status = data.get("status")
    mode   = data.get("mode", "Manual") 
    
    # Giao diện React PHẢI gửi kèm cảm biến hiện tại lúc bấm nút để DB không bị NULL
    temp   = data.get("temp")
    humi   = data.get("humi")
    light  = data.get("light")
    gas    = data.get("gas")

    if status is None:
        return jsonify({"error": "Thiếu status"}), 400

    log = DeviceLog(
        device_id = device_id,
        status    = status,
        mode      = mode, 
        temp      = float(temp) if temp is not None else 0,
        humi      = float(humi) if humi is not None else 0,
        light     = float(light) if light is not None else 0,
        gas       = float(gas) if gas is not None else 0,
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"status": "ok", "mode": mode, "device_status": status})


# ── API khác: Lịch sử, Upload AI ──────────────────────────────────────────
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

@device_bp.route("/train", methods=["POST"])
def handle_train_model():
    if 'file' not in request.files:
        return jsonify({"error": "Không tìm thấy file"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Chưa có file được chọn"}), 400

    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        temp_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', file.filename)
        file.save(temp_path)
        try:
            from services.ai import train_and_save_model
            train_and_save_model(temp_path)
            if os.path.exists(temp_path): os.remove(temp_path)
            return jsonify({"message": "Huấn luyện mô hình thành công!"}), 200
        except Exception as e:
            if os.path.exists(temp_path): os.remove(temp_path)
            return jsonify({"error": f"Lỗi trong quá trình train: {str(e)}"}), 500
    return jsonify({"error": "Định dạng file không hỗ trợ"}), 400