import os
import glob
import datetime
import traceback

import pandas as pd
from flask import Blueprint, request, jsonify
from models import db, Device, DeviceLog

device_bp = Blueprint("device", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# GET /  — Lấy danh sách thiết bị
# ══════════════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════════════
# GET /status  — ESP32 hỏi trạng thái hiện tại của từng thiết bị
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/status", methods=["GET"])
def get_status():
    devices = Device.query.all()
    result = []
    for d in devices:
        last_log = (
            DeviceLog.query
            .filter_by(device_id=d.id)
            .order_by(DeviceLog.timestamp.desc())
            .first()
        )
        result.append({
            "id":     d.id,
            "name":   d.name,
            "type":   d.type,
            "room":   d.room,
            "status": last_log.status if last_log else 0,
            "mode":   last_log.mode   if last_log else "AI",
        })
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# POST /sensor  — ESP32 gửi dữ liệu cảm biến, AI dự đoán và ghi log
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/sensor", methods=["POST"])
def update_sensor():
    data = request.json or {}
    try:
        temp  = float(data.get("temp",  0))
        humi  = float(data.get("humi",  0))
        light = float(data.get("light", 0))
        gas   = float(data.get("gas",   0))

        now = datetime.datetime.now()

        from services.ai import predict_behavior
        predictions = predict_behavior(temp, humi, light, now)

        for device_id, predicted_status in predictions.items():
            last_log = (
                DeviceLog.query
                .filter_by(device_id=device_id)
                .order_by(DeviceLog.timestamp.desc())
                .first()
            )

            # Người dùng đang điều khiển tay → AI không can thiệp
            if last_log and last_log.mode == "Manual":
                continue

            # Trạng thái không đổi → không ghi log thừa
            if last_log and last_log.status == predicted_status and last_log.mode == "AI":
                continue

            db.session.add(DeviceLog(
                device_id=device_id,
                status=predicted_status,
                mode="AI",
                temp=temp,
                humi=humi,
                light=light,
                gas=gas,
            ))

        db.session.commit()
        return jsonify({"status": "ok", "predictions": predictions})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /<id>/control  — Web UI điều khiển thủ công
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/<int:device_id>/control", methods=["POST"])
def control_device(device_id):
    data   = request.json or {}
    status = data.get("status")
    mode   = data.get("mode", "Manual")
    temp   = data.get("temp")
    humi   = data.get("humi")
    light  = data.get("light")
    gas    = data.get("gas")

    if status is None:
        return jsonify({"error": "Thiếu trường 'status'"}), 400

    db.session.add(DeviceLog(
        device_id=device_id,
        status=int(status),
        mode=mode,
        temp=float(temp)  if temp  is not None else 0.0,
        humi=float(humi)  if humi  is not None else 0.0,
        light=float(light) if light is not None else 0.0,
        gas=float(gas)   if gas   is not None else 0.0,
    ))
    db.session.commit()
    return jsonify({"status": "ok", "mode": mode, "device_status": status})


# ══════════════════════════════════════════════════════════════════════════════
# GET /<id>/logs  — Lịch sử log của thiết bị
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/<int:device_id>/logs", methods=["GET"])
def get_logs(device_id):
    limit = request.args.get("limit", 50, type=int)
    logs  = (
        DeviceLog.query
        .filter_by(device_id=device_id)
        .order_by(DeviceLog.timestamp.desc())
        .limit(limit)
        .all()
    )
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


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Đường dẫn thư mục trained_models
# ══════════════════════════════════════════════════════════════════════════════
def _models_dir():
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'trained_models')


def _clear_old_datasets(directory):
    """Xóa dataset cũ trước khi lưu cái mới."""
    for f in glob.glob(os.path.join(directory, '*.csv')) + glob.glob(os.path.join(directory, '*.xlsx')):
        try:
            os.remove(f)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# POST /train  — Upload dataset từ Web để train
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/train", methods=["POST"])
def handle_train_model():
    if 'file' not in request.files:
        return jsonify({"error": "Không tìm thấy file trong request"}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "Chưa có file được chọn"}), 400

    is_csv  = file.filename.endswith('.csv')
    is_xlsx = file.filename.endswith('.xlsx')
    if not (is_csv or is_xlsx):
        return jsonify({"error": "Chỉ hỗ trợ định dạng .csv hoặc .xlsx"}), 400

    models_dir = _models_dir()
    os.makedirs(models_dir, exist_ok=True)
    _clear_old_datasets(models_dir)

    ext       = '.csv' if is_csv else '.xlsx'
    file_path = os.path.join(models_dir, f'latest_dataset{ext}')
    file.save(file_path)

    try:
        from services.ai import train_and_save_model
        accuracy_results = train_and_save_model(file_path)
        return jsonify({"message": _build_result_message(accuracy_results)}), 200

    except Exception as e:
        traceback.print_exc()
        _safe_remove(file_path)
        return jsonify({"error": f"Lỗi trong quá trình train: {str(e)}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /train-from-db  — Trích xuất DeviceLog trong DB rồi train
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/train-from-db", methods=["POST"])
def train_from_db():
    records = (
        db.session.query(DeviceLog, Device)
        .join(Device, DeviceLog.device_id == Device.id)
        .filter(DeviceLog.temp.isnot(None))
        .all()
    )

    if len(records) < 20:
        return jsonify({
            "error": f"Dữ liệu trong Database quá ít ({len(records)} bản ghi). Cần ít nhất 20 bản ghi."
        }), 400

    days_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

    data = []
    for log, device in records:
        ts = log.timestamp
        data.append({
            "Ngày":            ts.strftime("%Y-%m-%d"),
            "Thứ":             days_vn[ts.weekday()],
            "Giờ":             ts.hour,
            "Phút":            ts.minute,
            "Nhiệt độ (°C)":   log.temp,
            "Độ ẩm (%)":       log.humi,
            "Ánh sáng (lux)":  log.light,
            "Tháng":           ts.month,
            "Device_ID":       log.device_id,
            "Tên thiết bị":    device.name,
            "Phòng":           device.room,      # FIX: lấy từ DB
            "Trạng thái":      log.status,
            "Trạng thái text": "BẬT" if log.status == 1 else "TẮT",
        })

    df = pd.DataFrame(data)

    models_dir = _models_dir()
    os.makedirs(models_dir, exist_ok=True)
    _clear_old_datasets(models_dir)

    file_path = os.path.join(models_dir, 'latest_dataset.xlsx')
    df.to_excel(file_path, sheet_name="Dữ liệu thô", index=False)

    try:
        from services.ai import train_and_save_model
        accuracy_results = train_and_save_model(file_path)
        return jsonify({"message": _build_result_message(accuracy_results)}), 200

    except Exception as e:
        traceback.print_exc()
        _safe_remove(file_path)
        return jsonify({"error": f"Lỗi train từ DB: {str(e)}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _build_result_message(accuracy_results: dict) -> str:
    """Tạo chuỗi thông báo kết quả train để hiển thị trên Frontend."""
    lines = ["Huấn luyện AI thành công! Độ chính xác trên tập kiểm thử:"]
    for key, acc in accuracy_results.items():
        lines.append(f"{key}: {acc}%")
    return "\n".join(lines)


def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass