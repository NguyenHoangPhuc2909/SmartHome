from models import db, Schedule, DeviceLog
import datetime


def check_schedules():
    """
    Chạy mỗi 60 giây — kiểm tra schedule nào khớp giờ hiện tại
    rồi ghi vào device_logs với mode = Schedule.
    """
    now      = datetime.datetime.now()
    day_map  = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    today    = day_map[now.weekday()]

    schedules = Schedule.query.filter_by(is_active=True).all()

    for s in schedules:
        # Kiểm tra đúng giờ và đúng ngày
        if s.hour != now.hour or s.minute != now.minute:
            continue
        if today not in s.days.split(","):
            continue

        # Tránh ghi log 2 lần trong cùng 1 phút
        already_logged = DeviceLog.query.filter_by(
            device_id = s.device_id,
            mode      = "Schedule",
        ).filter(
            DeviceLog.timestamp >= now.replace(second=0, microsecond=0)
        ).first()

        if already_logged:
            continue

        log = DeviceLog(
            device_id = s.device_id,
            status    = s.action,
            mode      = "Schedule",
        )
        db.session.add(log)

    db.session.commit()