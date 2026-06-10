from models import db, Schedule, ActuatorLog
import datetime


def check_schedules():
    """
    Chạy mỗi 60 giây — kiểm tra schedule nào khớp giờ hiện tại
    rồi ghi vào actuator_logs với mode = Schedule.
    """
    now      = datetime.datetime.now()
    day_map  = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    today    = day_map[now.weekday()]

    schedules = Schedule.query.filter_by(is_active=True).all()
    print(f"[SCHEDULER DEBUG] Wake up at {now.strftime('%H:%M:%S')}. Active schedules: {len(schedules)}. Today: {today}")
    executed = False

    for s in schedules:
        print(f"[SCHEDULER DEBUG] Checking ID={s.id} Time={s.hour:02d}:{s.minute:02d} Days=[{s.days}]")
        # Kiểm tra đúng giờ và đúng ngày
        if s.hour != now.hour or s.minute != now.minute:
            continue
        if today not in s.days.split(","):
            continue

        # Tránh ghi log 2 lần trong cùng 1 phút
        already_logged = ActuatorLog.query.filter_by(
            device_id = s.device_id,
            mode      = "Schedule",
        ).filter(
            ActuatorLog.timestamp >= now.replace(second=0, microsecond=0)
        ).first()

        if already_logged:
            continue

        log = ActuatorLog(
            device_id = s.device_id,
            status    = s.action,
            mode      = "Schedule",
        )
        db.session.add(log)
        
        # Bắn lệnh MQTT xuống thiết bị thực tế
        from models import Device
        device = Device.query.get(s.device_id)
        if device:
            from routes.device import get_mqtt_topic
            topic = get_mqtt_topic(device)
            if topic:
                from services.mqtt_service import publish_command
                publish_command(topic, s.action)

        executed = True

    if executed:
        db.session.commit()
    
    return executed