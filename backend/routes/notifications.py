from flask import Blueprint, request, jsonify
from models import db, AccessLog, ActuatorLog

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/", methods=["GET"])
def get_notifications():
    limit = request.args.get("limit", 20, type=int)
    
    # Lấy AccessLog
    access_logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(limit).all()
    # Lấy ActuatorLog
    actuator_logs = ActuatorLog.query.order_by(ActuatorLog.timestamp.desc()).limit(limit).all()
    
    notifications = []
    
    for log in access_logs:
        notifications.append({
            "id": f"access_{log.id}",
            "type": "access",
            "timestamp": log.timestamp.isoformat(),
            "message": "Cảnh báo người lạ xâm nhập" if log.result == "DENIED" else f"Người dùng {log.matched_dataset.name if log.matched_dataset else 'không xác định'} vừa mở cửa",
            "is_alert": log.is_alert,
            "raw_timestamp": log.timestamp
        })
        
    for log in actuator_logs:
        # không báo cho cửa (door) và còi (alarm) vì đã báo ở access
        if log.device.type in ['door', 'alarm']:
            continue
        status_text = "bật" if log.status == 1 else "tắt"
        notifications.append({
            "id": f"actuator_{log.id}",
            "type": "actuator",
            "timestamp": log.timestamp.isoformat(),
            "message": f"Thiết bị '{log.device.name}' được {status_text} (chế độ {log.mode})",
            "is_alert": False,
            "raw_timestamp": log.timestamp
        })
        
    # Sort by timestamp desc
    notifications.sort(key=lambda x: x["raw_timestamp"], reverse=True)
    
    # Bỏ raw_timestamp ra khỏi JSON
    for n in notifications:
        del n["raw_timestamp"]
        
    return jsonify(notifications[:limit])
