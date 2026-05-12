from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ── Users ──────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name          = db.Column(db.String(128))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    datasets = db.relationship("FaceDataset", backref="owner", lazy=True, cascade="all, delete")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


# ── Face Datasets ──────────────────────────────────────────────────────────
class FaceDataset(db.Model):
    __tablename__ = "face_datasets"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name       = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    access_logs = db.relationship("AccessLog", backref="matched_dataset", lazy=True,
                                  foreign_keys="AccessLog.matched_dataset_id")

    @property
    def photo_count(self):
        import os
        path = f"captured_faces/{self.name}"
        if not os.path.exists(path):
            return 0
        return len([f for f in os.listdir(path) if f.endswith(".jpg")])

    def __repr__(self):
        return f"<FaceDataset {self.name}>"


# ── Devices ────────────────────────────────────────────────────────────────
class Device(db.Model):
    __tablename__ = "devices"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128), nullable=False)     # "Đèn phòng khách"
    type        = db.Column(db.String(64),  nullable=False)     # light | fan | alarm | door
    room        = db.Column(db.String(64),  nullable=False)     # living_room | bedroom | kitchen | bathroom | entrance
    sensor_type = db.Column(db.String(32),  nullable=True)      # temp | humi | light | gas | NULL

    logs        = db.relationship("DeviceLog",  backref="device", lazy=True)
    schedules   = db.relationship("Schedule",   backref="device", lazy=True)
    access_logs = db.relationship("AccessLog",  backref="device", lazy=True)

    def __repr__(self):
        return f"<Device {self.name} ({self.type}) - {self.room}>"


# ── Device Logs ────────────────────────────────────────────────────────────
class DeviceLog(db.Model):
    __tablename__ = "device_logs"

    id        = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False)
    status    = db.Column(db.Integer, nullable=False)           # 0 = OFF | 1 = ON
    mode      = db.Column(db.String(16), nullable=False)        # Manual | AI | Schedule | Alert
    temp      = db.Column(db.Float,   nullable=True)            # nhiệt độ lúc ghi log
    humi      = db.Column(db.Float,   nullable=True)            # độ ẩm lúc ghi log
    light     = db.Column(db.Float,   nullable=True)            # ánh sáng lúc ghi log
    gas       = db.Column(db.Float,   nullable=True)            # khí gas lúc ghi log
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DeviceLog device={self.device_id} status={self.status} mode={self.mode}>"


# ── Schedules ──────────────────────────────────────────────────────────────
class Schedule(db.Model):
    __tablename__ = "schedules"

    id        = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False)
    action    = db.Column(db.Integer, nullable=False)           # 0 = OFF | 1 = ON
    hour      = db.Column(db.Integer, nullable=False)           # 0–23
    minute    = db.Column(db.Integer, nullable=False)           # 0–59
    days      = db.Column(db.String(64), nullable=False)        # "mon,tue,wed,thu,fri,sat,sun"
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Schedule device={self.device_id} action={self.action} {self.hour}:{self.minute:02d}>"


# ── Access Logs (ESP32-CAM nhận diện khuôn mặt) ────────────────────────────
class AccessLog(db.Model):
    __tablename__ = "access_logs"

    id                 = db.Column(db.Integer, primary_key=True)
    device_id          = db.Column(db.Integer, db.ForeignKey("devices.id"),       nullable=False)
    matched_dataset_id = db.Column(db.Integer, db.ForeignKey("face_datasets.id"), nullable=True)
    image_path         = db.Column(db.String(512))
    confidence         = db.Column(db.Float)
    result             = db.Column(db.String(16), nullable=False)               # GRANTED | DENIED
    is_alert           = db.Column(db.Boolean, default=False)                   # true nếu trigger còi
    timestamp          = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AccessLog device={self.device_id} result={self.result} alert={self.is_alert}>"