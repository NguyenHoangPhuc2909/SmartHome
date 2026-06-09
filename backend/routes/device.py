import os
import glob
import datetime
import traceback

import pandas as pd
from flask import Blueprint, request, jsonify, session
from models import db, Device, ActuatorLog, SensorLog, User
from extensions import socketio
from services.mqtt_service import publish_command

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
        if d.type == "sensor":
            last_log = SensorLog.query.filter_by(device_id=d.id).order_by(SensorLog.timestamp.desc()).first()
            result.append({
                "id":     d.id,
                "name":   d.name,
                "type":   d.type,
                "room":   d.room,
                "sensor_type": d.sensor_type,
                "status": 1,
                "mode":   "Manual",
                "temp":   last_log.temp   if last_log else None,
                "humi":   last_log.humi   if last_log else None,
                "light":  last_log.light  if last_log else None,
                "gas":    last_log.gas    if last_log else None,
            })
        else:
            last_log = ActuatorLog.query.filter_by(device_id=d.id).order_by(ActuatorLog.timestamp.desc()).first()
            result.append({
                "id":     d.id,
                "name":   d.name,
                "type":   d.type,
                "room":   d.room,
                "sensor_type": d.sensor_type,
                "status": last_log.status if last_log else 0,
                "mode":   last_log.mode   if last_log else "AI",
                "temp":   None,
                "humi":   None,
                "light":  None,
                "gas":    None,
            })
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# POST /reset-to-ai  — Reset tất cả thiết bị về AI mode
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/reset-to-ai", methods=["POST"])
def reset_to_ai():
    try:
        devices = Device.query.filter(Device.type.in_(["light", "fan"])).all()
        count = 0
        for d in devices:
            last_log = (
                ActuatorLog.query
                .filter_by(device_id=d.id)
                .order_by(ActuatorLog.timestamp.desc())
                .first()
            )
            if last_log and last_log.mode == "Manual":
                db.session.add(ActuatorLog(
                    device_id=d.id,
                    status=last_log.status,
                    mode="AI"
                ))
                count += 1
        db.session.commit()
        socketio.emit("refresh_devices", namespace="/")
        return jsonify({"status": "ok", "reset_count": count})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /sensor  — ESP32 gửi dữ liệu cảm biến, lưu 1 phút/lần
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

        # Luôn đảm bảo có 1 thiết bị "Cụm Cảm Biến"
        master_sensor = Device.query.filter_by(type="sensor", sensor_type="all").first()
        if not master_sensor:
            master_sensor = Device(name="Cụm Cảm Biến", type="sensor", room="Phòng khách", sensor_type="all")
            db.session.add(master_sensor)
            db.session.commit()

        # LOGIC LỌC: Chỉ lưu vào Database nếu log gần nhất cách đây > 60 giây
        last_log = SensorLog.query.filter_by(device_id=master_sensor.id).order_by(SensorLog.timestamp.desc()).first()
        should_save = True
        
        if last_log:
            time_diff = (now - last_log.timestamp).total_seconds()
            if time_diff < 60:
                should_save = False

        if should_save:
            db.session.add(SensorLog(
                device_id=master_sensor.id,
                temp=temp,
                humi=humi,
                light=light,
                gas=gas,
                timestamp=now
            ))
            db.session.commit()

        socketio.emit("refresh_devices", namespace="/")
        return jsonify({"status": "ok", "message": "Đã cập nhật cảm biến"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /auto-control  — Tự động xác định trạng thái thiết bị bằng AI
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/auto-control", methods=["POST"])
def auto_control_devices():
    data = request.json or {}
    try:
        temp  = float(data.get("temp",  25.0))
        humi  = float(data.get("humi",  60.0))
        light = float(data.get("light", 150.0))
        gas   = float(data.get("gas",   0.0))

        now = datetime.datetime.now()

        from services.ai import predict_behavior, ensure_devices_exist
        ensure_devices_exist()
        
        predictions = predict_behavior(temp, humi, light, now)

        devices_map = {
            'PK_den': Device.query.filter_by(type='light', room='living_room').first(),
            'PK_quat': Device.query.filter_by(type='fan', room='living_room').first(),
            'PN_den': Device.query.filter_by(type='light', room='bedroom').first(),
            'PN_quat': Device.query.filter_by(type='fan', room='bedroom').first(),
        }

        actions = []
        state_changed = False
        for key, dev in devices_map.items():
            if dev:
                pred_status = predictions.get(dev.id, 0)
                
                # Chỉ ghi log và Publish MQTT nếu trạng thái thay đổi
                last_log = ActuatorLog.query.filter_by(device_id=dev.id).order_by(ActuatorLog.timestamp.desc()).first()
                if not last_log or last_log.status != pred_status:
                    # Publish MQTT command cho AI
                    topic = get_mqtt_topic(dev)
                    if topic:
                        publish_command(topic, pred_status)
                    
                    db.session.add(ActuatorLog(
                        device_id=dev.id,
                        status=pred_status,
                        mode="AI",
                        timestamp=now
                    ))
                    state_changed = True
                
                actions.append({
                    "id": dev.id,
                    "name": dev.name,
                    "room": dev.room,
                    "status": pred_status,
                    "status_text": "BẬT" if pred_status == 1 else "TẮT"
                })

        db.session.commit()
        if state_changed:
            socketio.emit("refresh_devices", namespace="/")
            
        return jsonify({"status": "ok", "actions": actions, "state_changed": state_changed})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /simulate  — Giả lập tự động kích hoạt thiết bị bằng AI với tham số tùy chỉnh
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/simulate", methods=["POST"])
def simulate_devices():
    data = request.json or {}
    try:
        temp  = float(data.get("temp",  25.0))
        humi  = float(data.get("humi",  60.0))
        light = float(data.get("light", 150.0))
        gas   = float(data.get("gas",   0.0))

        time_str = data.get("time")
        if time_str:
            try:
                dt = datetime.datetime.fromisoformat(time_str)
            except Exception as ex:
                print(f"[WARNING] Invalid ISO datetime format: {time_str}, fallback to now. Error: {ex}")
                dt = datetime.datetime.now()
        else:
            dt = datetime.datetime.now()

        from services.ai import predict_behavior, ensure_devices_exist
        ensure_devices_exist()
        
        predictions = predict_behavior(temp, humi, light, dt)

        from models import Device, ActuatorLog, SensorLog
        
        # Ghi nhận chỉ số cảm biến giả lập vào SensorLog (cho cụm cảm biến)
        master_sensor = Device.query.filter_by(type="sensor", sensor_type="all").first()
        if master_sensor:
            db.session.add(SensorLog(
                device_id=master_sensor.id,
                temp=temp,
                humi=humi,
                light=light,
                gas=gas,
                timestamp=dt
            ))

        devices_map = {
            'PK_den': Device.query.filter_by(type='light', room='living_room').first(),
            'PK_quat': Device.query.filter_by(type='fan', room='living_room').first(),
            'PN_den': Device.query.filter_by(type='light', room='bedroom').first(),
            'PN_quat': Device.query.filter_by(type='fan', room='bedroom').first(),
        }

        actions = []
        state_changed = False
        for key, dev in devices_map.items():
            if dev:
                pred_status = predictions.get(dev.id, 0)
                
                # Chỉ ghi log trạng thái AI cho thiết bị vào ActuatorLog nếu trạng thái đổi
                last_log = ActuatorLog.query.filter_by(device_id=dev.id).order_by(ActuatorLog.timestamp.desc()).first()
                if not last_log or last_log.status != pred_status:
                    db.session.add(ActuatorLog(
                        device_id=dev.id,
                        status=pred_status,
                        mode="AI",
                        timestamp=dt
                    ))
                    state_changed = True
                
                actions.append({
                    "id": dev.id,
                    "name": dev.name,
                    "room": dev.room,
                    "status": pred_status,
                    "status_text": "BẬT" if pred_status == 1 else "TẮT"
                })

        db.session.commit()
        if state_changed:
            socketio.emit("refresh_devices", namespace="/")
        return jsonify({"status": "ok", "actions": actions, "state_changed": state_changed})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# GET /sensor-history  — Lấy lịch sử cảm biến cho mini-chart
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/sensor-history", methods=["GET"])
def get_sensor_history():
    logs = (
        db.session.query(SensorLog)
        .join(Device, SensorLog.device_id == Device.id)
        .filter(Device.type == "sensor")
        .filter(SensorLog.temp.isnot(None))
        .order_by(SensorLog.timestamp.desc())
        .limit(50)
        .all()
    )
    
    logs.reverse()
    
    return jsonify([{
        "time":  l.timestamp.strftime("%H:%M:%S"),
        "temp":  l.temp,
        "humi":  l.humi,
        "light": l.light,
        "gas":   l.gas,
    } for l in logs])


# ══════════════════════════════════════════════════════════════════════════════
# POST /<id>/control  — Web UI điều khiển thủ công
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/<int:device_id>/control", methods=["POST"])
def control_device(device_id):
    data   = request.json or {}
    status = data.get("status")
    mode   = data.get("mode", "Manual")

    if status is None:
        return jsonify({"error": "Thiếu trường 'status'"}), 400

    device = Device.query.get(device_id)
    if not device:
        return jsonify({"error": "Không tìm thấy thiết bị"}), 404

    # Publish MQTT command
    topic = get_mqtt_topic(device)
    print(f"[DEBUG] Control device {device_id}: name={device.name!r}, type={device.type!r}, room={device.room!r} -> topic={topic!r}")
    if topic:
        publish_command(topic, status)
    else:
        print(f"[DEBUG] WARNING: No MQTT topic mapped for this device! Check type/room values.")

    db.session.add(ActuatorLog(
        device_id=device_id,
        status=int(status),
        mode=mode,
        timestamp=datetime.datetime.now()
    ))
    db.session.commit()
    socketio.emit("refresh_devices", namespace="/")
    return jsonify({"status": "ok", "mode": mode, "device_status": status})


# ══════════════════════════════════════════════════════════════════════════════
# GET /<id>/logs  — Lịch sử log của thiết bị
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/<int:device_id>/logs", methods=["GET"])
def get_logs(device_id):
    limit = request.args.get("limit", 50, type=int)
    
    # Kiểm tra xem đây là sensor hay actuator
    device = Device.query.get(device_id)
    if not device:
        return jsonify({"error": "Không tìm thấy thiết bị"}), 404
        
    if device.type == "sensor":
        logs = SensorLog.query.filter_by(device_id=device_id).order_by(SensorLog.timestamp.desc()).limit(limit).all()
        return jsonify([{
            "id":        l.id,
            "status":    1,
            "mode":      "Manual",
            "temp":      l.temp,
            "humi":      l.humi,
            "light":     l.light,
            "gas":       l.gas,
            "timestamp": l.timestamp.isoformat(),
        } for l in logs])
    else:
        logs = ActuatorLog.query.filter_by(device_id=device_id).order_by(ActuatorLog.timestamp.desc()).limit(limit).all()
        return jsonify([{
            "id":        l.id,
            "status":    l.status,
            "mode":      l.mode,
            "temp":      None,
            "humi":      None,
            "light":     None,
            "gas":       None,
            "timestamp": l.timestamp.isoformat(),
        } for l in logs])


# ══════════════════════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════════════════════
def get_mqtt_topic(device):
    if device.type == "light":
        if device.room == "living_room": return "myiot/home/controls/led1"
        if device.room == "bedroom": return "myiot/home/controls/led2"
        if device.room == "kitchen": return "myiot/home/controls/led3"
        if device.room == "gate": return "myiot/home/controls/led4"
        if device.room == "bathroom": return "myiot/home/controls/led5"
    elif device.type == "fan":
        if device.room == "living_room": return "myiot/home/controls/motor1"
        if device.room == "bedroom": return "myiot/home/controls/motor2"
    elif device.type == "door":
        return "myiot/home/commands/servo"
    elif device.type == "alarm":
        return "myiot/home/controls/buzzer"
    return None

def _models_dir():
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'trained_models')

def _clear_upload_dataset(directory):
    for ext in ['.csv', '.xlsx']:
        path = os.path.join(directory, f'latest_upload_dataset{ext}')
        _safe_remove(path)

def _clear_db_dataset(directory):
    for ext in ['.csv', '.xlsx']:
        path = os.path.join(directory, f'latest_db_dataset{ext}')
        _safe_remove(path)


def _build_result_message(accuracy_results: dict) -> str:
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
    _clear_upload_dataset(models_dir)

    ext       = '.csv' if is_csv else '.xlsx'
    file_path = os.path.join(models_dir, f'latest_upload_dataset{ext}')
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
# POST /train-from-db  — Trích xuất dữ liệu từ DB (Actuator + Sensor) rồi train
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/train-from-db", methods=["POST"])
def train_from_db():
    try:
        # 1. Lấy dữ liệu cảm biến làm trục thời gian
        master_sensor = Device.query.filter_by(type="sensor", sensor_type="all").first()
        if not master_sensor:
            return jsonify({"error": "Không tìm thấy Cụm Cảm Biến trong cơ sở dữ liệu."}), 400
            
        sensor_logs = SensorLog.query.filter_by(device_id=master_sensor.id).order_by(SensorLog.timestamp.asc()).all()
        if not sensor_logs:
            return jsonify({"error": "Chưa có dữ liệu cảm biến để huấn luyện."}), 400
            
        sensor_data = [{
            "timestamp": log.timestamp,
            "nhiet_do": log.temp,
            "do_am": log.humi,
            "anh_sang": log.light
        } for log in sensor_logs]
        
        df_sensors = pd.DataFrame(sensor_data)
        df_sensors['time_key'] = df_sensors['timestamp'].dt.round('1min')
        df_sensors = df_sensors.groupby('time_key').mean().reset_index()

        # 2. Lấy dữ liệu sự kiện bật/tắt
        ai_devices = Device.query.filter(
            Device.type.in_(["light", "fan"]),
            Device.room.in_(["living_room", "bedroom"])
        ).all()
        ai_device_ids = [d.id for d in ai_devices]
        
        device_logs = (
            db.session.query(ActuatorLog, Device)
            .join(Device, ActuatorLog.device_id == Device.id)
            .filter(Device.id.in_(ai_device_ids))
            .order_by(ActuatorLog.timestamp.asc())
            .all()
        )
        
        events = []
        for log, device in device_logs:
            target = None
            r, t = device.room, device.type
            if r == "living_room" and t == "light": target = "PK_den"
            elif r == "living_room" and t == "fan": target = "PK_quat"
            elif r == "bedroom" and t == "light": target = "PN_den"
            elif r == "bedroom" and t == "fan": target = "PN_quat"
            
            if target:
                events.append({
                    "timestamp": log.timestamp,
                    "target_name": target,
                    "status": log.status
                })
                
        # 3. Gộp dữ liệu
        if events:
            df_events = pd.DataFrame(events)
            df_events['time_key'] = df_events['timestamp'].dt.round('1min')
            df_pivot = df_events.pivot_table(index='time_key', columns='target_name', values='status', aggfunc='last').reset_index()
            df_merged = pd.merge(df_sensors, df_pivot, on='time_key', how='left')
            
            # Khởi tạo giá trị ban đầu là 0 nếu cột chưa có dữ liệu tại thời điểm đầu
            targets_col = ["PK_den", "PK_quat", "PN_den", "PN_quat"]
            for t in targets_col:
                if t in df_merged.columns:
                    # ffill() để điền tiếp nối, fillna(0) cho các giá trị ở đầu (trước khi có sự kiện đầu tiên)
                    df_merged[t] = df_merged[t].ffill().fillna(0).astype(int)
                else:
                    df_merged[t] = 0
        else:
            df_merged = df_sensors
            for t in ["PK_den", "PK_quat", "PN_den", "PN_quat"]:
                df_merged[t] = 0

        df_merged = df_merged.rename(columns={'time_key': 'timestamp'})
        
        if len(df_merged) < 20:
            return jsonify({
                "error": f"Dữ liệu trong Database quá ít ({len(df_merged)} phút). Cần ít nhất 20 phút dữ liệu để train."
            }), 400

        # Xuất ra file Excel
        models_dir = _models_dir()
        os.makedirs(models_dir, exist_ok=True)
        _clear_db_dataset(models_dir)

        file_path = os.path.join(models_dir, 'latest_db_dataset.xlsx')
        df_merged.to_excel(file_path, sheet_name="Dữ liệu chuẩn hóa", index=False)

        from services.ai import train_and_save_model
        accuracy_results = train_and_save_model(file_path)
        return jsonify({"message": _build_result_message(accuracy_results)}), 200

    except Exception as e:
        traceback.print_exc()
        if 'file_path' in locals():
            _safe_remove(file_path)
        return jsonify({"error": f"Lỗi train từ DB: {str(e)}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /trigger_refresh  — Endpoint nội bộ: Scheduler gọi để emit WebSocket
# ══════════════════════════════════════════════════════════════════════════════
@device_bp.route("/trigger_refresh", methods=["POST"])
def trigger_refresh():
    """Background scheduler gọi endpoint này để emit refresh_devices từ request context chuẩn"""
    socketio.emit("refresh_devices", namespace="/")
    return jsonify({"status": "ok"})