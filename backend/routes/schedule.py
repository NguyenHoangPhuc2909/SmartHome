from flask import Blueprint, request, jsonify
from models import db, Schedule

schedule_bp = Blueprint("schedule", __name__)


# ── Lấy danh sách lịch ────────────────────────────────────────────────────
@schedule_bp.route("/", methods=["GET"])
def get_schedules():
    schedules = Schedule.query.all()
    return jsonify([{
        "id":        s.id,
        "device_id": s.device_id,
        "action":    s.action,
        "hour":      s.hour,
        "minute":    s.minute,
        "days":      s.days,
        "is_active": s.is_active,
    } for s in schedules])


# ── Thêm lịch ─────────────────────────────────────────────────────────────
@schedule_bp.route("/", methods=["POST"])
def add_schedule():
    data = request.json or {}
    s = Schedule(
        device_id = data.get("device_id"),
        action    = data.get("action"),
        hour      = data.get("hour"),
        minute    = data.get("minute"),
        days      = data.get("days"),
        is_active = data.get("is_active", True),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"status": "ok", "id": s.id})


# ── Bật tắt lịch ──────────────────────────────────────────────────────────
@schedule_bp.route("/<int:s_id>/toggle", methods=["POST"])
def toggle_schedule(s_id):
    s = Schedule.query.get_or_404(s_id)
    s.is_active = not s.is_active
    db.session.commit()
    return jsonify({"status": "ok", "is_active": s.is_active})


# ── Xoá lịch ──────────────────────────────────────────────────────────────
@schedule_bp.route("/<int:s_id>", methods=["DELETE"])
def delete_schedule(s_id):
    s = Schedule.query.get_or_404(s_id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"status": "ok"})