from flask import Blueprint, request, jsonify, session
from models import db, AccessLog, FaceDataset, Device, ActuatorLog, User, SystemSetting
from extensions import socketio
from config import Config
import os, datetime, json, shutil
import onnxruntime as ort
import numpy as np
import cv2

# Import class EmbeddingModel
from services.embedding_helper import EmbeddingModel
from services.mqtt_service import publish_command
from services.antispoof import AntiSpoofModel

access_bp = Blueprint("access", __name__)
ANTISPOOF_SETTING_KEY = "antispoof_enabled"
FACE_MODEL_SETTING_KEY = "face_model_type"


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
        "denied_reason":      l.denied_reason,
        "antispoof_label":    l.antispoof_label,
        "antispoof_score":    l.antispoof_score,
        "antispoof_threshold": l.antispoof_threshold,
        "antispoof_type":     l.antispoof_type,
        "timestamp":          l.timestamp.isoformat(),
    } for l in logs])


@access_bp.route("/antispoof-setting", methods=["GET"])
def get_antispoof_setting():
    return jsonify(_antispoof_setting_payload())


@access_bp.route("/antispoof-setting", methods=["POST"])
def update_antispoof_setting():
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("enabled"), bool):
        return jsonify({"error": "enabled must be a boolean"}), 400
    enabled = data["enabled"]

    if enabled and not _antispoof_available():
        return jsonify({
            **_antispoof_setting_payload(),
            "error": "Anti-spoof model is not available",
        }), 400

    setting = SystemSetting.query.get(ANTISPOOF_SETTING_KEY)
    if setting is None:
        setting = SystemSetting(key=ANTISPOOF_SETTING_KEY, value="1" if enabled else "0")
        db.session.add(setting)
    else:
        setting.value = "1" if enabled else "0"
    db.session.commit()

    return jsonify(_antispoof_setting_payload())


@access_bp.route("/face-model-setting", methods=["GET"])
def get_face_model_setting():
    setting = SystemSetting.query.get(FACE_MODEL_SETTING_KEY)
    model_type = setting.value if setting else "mobilefacenet"
    return jsonify({"model_type": model_type})


@access_bp.route("/face-model-setting", methods=["POST"])
def update_face_model_setting():
    data = request.get_json(silent=True) or {}
    model_type = data.get("model_type")
    if model_type not in ["mobilefacenet", "resnet34"]:
        return jsonify({"error": "Invalid model_type"}), 400

    setting = SystemSetting.query.get(FACE_MODEL_SETTING_KEY)
    if setting is None:
        setting = SystemSetting(key=FACE_MODEL_SETTING_KEY, value=model_type)
        db.session.add(setting)
    else:
        setting.value = model_type
    db.session.commit()

    return jsonify({"model_type": model_type})


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
    antispoof_enabled = _runtime_antispoof_enabled()
    antispoof_result = _run_antispoof(image_path, enabled=antispoof_enabled)
    can_recognize = (not antispoof_enabled) or antispoof_result.get("is_live", False)
    _save_antispoof_debug(image_path, filename, antispoof_result)

    matched_id = None
    confidence = 0.0
    denied_reason = None

    if can_recognize:
        from services.face_recognition import recognize_face
        # Lấy setting active model
        model_setting = SystemSetting.query.get(FACE_MODEL_SETTING_KEY)
        active_model = model_setting.value if model_setting else "mobilefacenet"
        
        matched_id, confidence = recognize_face(image_path, threshold=Config.FACE_RECOGNITION_THRESHOLD, model_type=active_model)
        if not matched_id:
            denied_reason = "UNKNOWN"
    else:
        denied_reason = _antispoof_denied_reason(antispoof_result)

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
    result    = "GRANTED" if can_recognize and matched_id and confidence >= Config.FACE_RECOGNITION_THRESHOLD else "DENIED"
    is_alert  = result == "DENIED" and _should_alert(denied_reason)

    # Ghi access log
    log = AccessLog(
        device_id          = door_device.id,
        matched_dataset_id = matched_id,
        image_path         = f"recog_images/{filename}",
        confidence         = float(confidence),
        result             = result,
        is_alert           = is_alert,
        denied_reason      = denied_reason if result == "DENIED" else None,
        antispoof_label    = antispoof_result.get("label"),
        antispoof_score    = _safe_float(antispoof_result.get("prob_spoof")),
        antispoof_threshold = _safe_float(antispoof_result.get("threshold")),
        antispoof_type     = antispoof_result.get("attack_type"),
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
        "denied_reason": denied_reason if result == "DENIED" else None,
        "antispoof": {
            "enabled": antispoof_enabled,
            "label": antispoof_result.get("label"),
            "is_live": antispoof_result.get("is_live"),
            "prob_spoof": antispoof_result.get("prob_spoof"),
            "threshold": antispoof_result.get("threshold"),
            "live_max_score": antispoof_result.get("live_max_score"),
            "spoof_min_score": antispoof_result.get("spoof_min_score"),
            "attack_type": antispoof_result.get("attack_type"),
            "attack_probability": antispoof_result.get("attack_probability"),
            "quality": antispoof_result.get("quality"),
            "error": antispoof_result.get("error"),
        },
    })


def _antispoof_available():
    return (
        bool(Config.ANTISPOOF_ENABLED)
        and os.path.exists(Config.ANTISPOOF_MODEL_PATH)
        and os.path.exists(Config.ANTISPOOF_THRESHOLD_CONFIG_PATH)
    )


def _runtime_antispoof_enabled():
    if not _antispoof_available():
        return False

    setting = SystemSetting.query.get(ANTISPOOF_SETTING_KEY)
    if setting is None:
        return True
    return setting.value == "1"


def _antispoof_setting_payload():
    return {
        "available": _antispoof_available(),
        "enabled": _runtime_antispoof_enabled(),
    }


def _run_antispoof(image_path, enabled=None):
    if enabled is None:
        enabled = _runtime_antispoof_enabled()

    if not enabled:
        return {
            "ok": True,
            "face_found": True,
            "is_live": True,
            "label": "DISABLED",
            "prob_spoof": 0.0,
            "threshold": None,
            "live_max_score": None,
            "spoof_min_score": None,
            "attack_type": None,
            "attack_probability": None,
            "quality": None,
            "error": None,
        }

    try:
        return AntiSpoofModel.get_instance().predict_file(image_path)
    except Exception as exc:
        print(f"[ERROR] Anti-spoof failed: {exc}")
        return {
            "ok": False,
            "face_found": False,
            "is_live": False,
            "label": "ERROR",
            "prob_spoof": 1.0,
            "threshold": None,
            "live_max_score": None,
            "spoof_min_score": None,
            "attack_type": None,
            "attack_probability": None,
            "quality": None,
            "error": str(exc),
        }


def _antispoof_denied_reason(antispoof_result):
    label = antispoof_result.get("label")
    if label == "SPOOF":
        return "SPOOF"
    if label == "NO_FACE":
        return "NO_FACE"
    if label == "UNCERTAIN":
        return "ANTISPOOF_UNCERTAIN"
    if label == "ERROR":
        return "ANTISPOOF_ERROR"
    return "ANTISPOOF"


def _should_alert(denied_reason):
    return denied_reason != "ANTISPOOF_UNCERTAIN"


def _save_antispoof_debug(image_path, filename, antispoof_result):
    if not Config.ANTISPOOF_DEBUG_ENABLED:
        return

    label = antispoof_result.get("label")
    if label in (None, "LIVE", "DISABLED"):
        return

    try:
        base_name = os.path.splitext(filename)[0]
        label_dir = os.path.join(Config.ANTISPOOF_DEBUG_DIR, label.lower())
        os.makedirs(label_dir, exist_ok=True)

        debug_image_path = os.path.join(label_dir, f"{base_name}.jpg")
        debug_json_path = os.path.join(label_dir, f"{base_name}.json")
        shutil.copy2(image_path, debug_image_path)

        metadata = {
            "timestamp": datetime.datetime.now().isoformat(),
            "source_image": f"recog_images/{filename}",
            "label": label,
            "prob_spoof": antispoof_result.get("prob_spoof"),
            "threshold": antispoof_result.get("threshold"),
            "live_max_score": antispoof_result.get("live_max_score"),
            "spoof_min_score": antispoof_result.get("spoof_min_score"),
            "attack_type": antispoof_result.get("attack_type"),
            "attack_probability": antispoof_result.get("attack_probability"),
            "quality": antispoof_result.get("quality"),
            "box": antispoof_result.get("box"),
            "face_box": antispoof_result.get("face_box"),
            "error": antispoof_result.get("error"),
        }
        with open(debug_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[WARNING] Could not save anti-spoof debug sample: {exc}")


def _safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
