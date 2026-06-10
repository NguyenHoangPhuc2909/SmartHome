import json
import threading
import paho.mqtt.client as mqtt
import datetime
from extensions import socketio
from models import db, SensorLog, Device

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_SENSORS = "myiot/home/sensors"

client = mqtt.Client()

# Để app_context hoạt động, ta cần truyền app từ file chính vào đây
flask_app = None

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected to {MQTT_BROKER} with result code {rc}")
    client.subscribe(TOPIC_SENSORS)
    client.subscribe("myiot/home/status/#")

def on_message(client, userdata, msg):
    if not flask_app:
        return
        
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    if topic == TOPIC_SENSORS:
        try:
            data = json.loads(payload)
            temp = float(data.get("temp", 0))
            humi = float(data.get("humi", 0))
            gas = float(data.get("gas", 0))
            light = float(data.get("light", 0))
            
            with flask_app.app_context():
                master_sensor = Device.query.filter_by(type="sensor", sensor_type="all").first()
                if not master_sensor:
                    master_sensor = Device(name="Cụm Cảm Biến", type="sensor", room="Phòng khách", sensor_type="all")
                    db.session.add(master_sensor)
                    db.session.commit()
                
                now = datetime.datetime.now()
                
                # Cập nhật socket liên tục cho WebUI
                socketio.emit("refresh_devices", namespace="/")
                if gas > 3000:
                    socketio.emit("gas_alert", {"gas_level": gas, "message": "Nguy hiểm: Rò rỉ khí Gas!"}, namespace="/")
                
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
                    
        except Exception as e:
            print(f"[MQTT] Parse sensor data error: {e}")

    elif topic.startswith("myiot/home/status/"):
        try:
            device_name_in_topic = topic.split("/")[-1]
            status_val = int(payload)
            
            with flask_app.app_context():
                dev = None
                if device_name_in_topic == "led1": dev = Device.query.filter_by(type="light", room="living_room").first()
                elif device_name_in_topic == "led2": dev = Device.query.filter_by(type="light", room="bedroom").first()
                elif device_name_in_topic == "led3": dev = Device.query.filter_by(type="light", room="kitchen").first()
                elif device_name_in_topic == "led4": dev = Device.query.filter_by(type="light", room="gate").first()
                elif device_name_in_topic == "led5": dev = Device.query.filter_by(type="light", room="bathroom").first()
                elif device_name_in_topic == "motor1": dev = Device.query.filter_by(type="fan", room="living_room").first()
                elif device_name_in_topic == "motor2": dev = Device.query.filter_by(type="fan", room="bedroom").first()
                elif device_name_in_topic == "buzzer": dev = Device.query.filter_by(type="alarm").first()
                
                if dev:
                    # Ghi nhận thay đổi trạng thái từ phần cứng
                    from models import ActuatorLog
                    
                    # LOGIC LỌC: Chỉ ghi log nếu trạng thái thực sự thay đổi 
                    # (Để tránh phần cứng echo lại trạng thái vừa được Web/Schedule yêu cầu)
                    last_log = ActuatorLog.query.filter_by(device_id=dev.id).order_by(ActuatorLog.timestamp.desc()).first()
                    
                    if not last_log or last_log.status != status_val:
                        db.session.add(ActuatorLog(
                            device_id=dev.id,
                            status=status_val,
                            mode="Manual",
                            timestamp=datetime.datetime.now()
                        ))
                        db.session.commit()
                        socketio.emit("refresh_devices", namespace="/")
        except Exception as e:
            print(f"[MQTT] Parse status data error: {e}")

client.on_connect = on_connect
client.on_message = on_message

def start_mqtt(app):
    global flask_app
    flask_app = app
    
    def mqtt_thread():
        while True:
            try:
                print(f"[MQTT] Connecting to {MQTT_BROKER}...")
                client.connect(MQTT_BROKER, MQTT_PORT, 60)
                client.loop_forever()
            except Exception as e:
                print(f"[MQTT] Connect error: {e}. Retrying in 10s...")
                import time
                time.sleep(10)
            
    # Chạy MQTT trong thread riêng để không block Flask
    threading.Thread(target=mqtt_thread, daemon=True).start()

def publish_command(topic, payload):
    if client.is_connected():
        client.publish(topic, str(payload))
        print(f"[MQTT] Published to {topic}: {payload}")
    else:
        print(f"[MQTT] WARNING: Not connected, cannot publish to {topic}")
