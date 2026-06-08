import os
import csv
import random
import sqlite3

def populate():
    # Xac dinh duong dan tuyet doi theo vi tri cua file script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, 'smarthome.db')
    csv_path = os.path.join(script_dir, 'trained_models', 'latest_dataset.csv')
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Khong tim thay file database tai: {db_path}")
        return
    if not os.path.exists(csv_path):
        print(f"[ERROR] Khong tim thay file du lieu nguon tai: {csv_path}")
        return
        
    print(f"[INFO] Dang ket noi toi database {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Dam bao cac thiet bi can thiet ton tai trong bang devices
    print("[INFO] Dang kiem tra cau hinh cac thiet bi (devices)...")
    targets_info = {
        'PK_den': ('Den phong khach', 'light', 'living_room'),
        'PK_quat': ('Quat phong khach', 'fan', 'living_room'),
        'PN_den': ('Den phong ngu', 'light', 'bedroom'),
        'PN_quat': ('Quat phong ngu', 'fan', 'bedroom'),
    }
    
    device_ids = {}
    for key, (name, type_, room) in targets_info.items():
        cursor.execute("SELECT id FROM devices WHERE type=? AND room=?", (type_, room))
        row = cursor.fetchone()
        if row:
            device_ids[key] = row[0]
        else:
            cursor.execute("INSERT INTO devices (name, type, room) VALUES (?, ?, ?)", (name, type_, room))
            device_ids[key] = cursor.lastrowid
            
    # Thiet bi cam bien chinh
    cursor.execute("SELECT id FROM devices WHERE type=? AND sensor_type=?", ("sensor", "all"))
    row = cursor.fetchone()
    if row:
        device_ids['master_sensor'] = row[0]
    else:
        cursor.execute("INSERT INTO devices (name, type, room, sensor_type) VALUES (?, ?, ?, ?)", 
                       ("Cum Cam Bien", "sensor", "Phong khach", "all"))
        device_ids['master_sensor'] = cursor.lastrowid
        
    # 2. Doc du lieu tu file CSV bang thu vien csv tich hop san
    print(f"[INFO] Dang doc du lieu tu tep {csv_path}...")
    
    sensor_data = []
    actuator_data = []
    
    start_date = '2024-01-01 00:00:00'
    end_date = '2024-04-01 00:00:00'
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        # Xac dinh chi so cot dong
        ts_idx = header.index('timestamp')
        temp_idx = header.index('nhiet_do')
        humi_idx = header.index('do_am')
        light_idx = header.index('anh_sang')
        pn_quat_idx = header.index('PN_quat')
        pn_den_idx = header.index('PN_den')
        pk_quat_idx = header.index('PK_quat')
        pk_den_idx = header.index('PK_den')
        
        for row in reader:
            ts = row[ts_idx]
            # Loc lay 3 thang du lieu
            if start_date <= ts < end_date:
                temp = float(row[temp_idx])
                humi = float(row[humi_idx])
                light = float(row[light_idx])
                gas = random.uniform(5.0, 15.0)  # Muc gas an toan ngau nhien
                
                sensor_data.append((device_ids['master_sensor'], temp, humi, light, gas, ts))
                
                actuator_data.append((device_ids['PK_den'], int(row[pk_den_idx]), 'AI', ts))
                actuator_data.append((device_ids['PK_quat'], int(row[pk_quat_idx]), 'AI', ts))
                actuator_data.append((device_ids['PN_den'], int(row[pn_den_idx]), 'AI', ts))
                actuator_data.append((device_ids['PN_quat'], int(row[pn_quat_idx]), 'AI', ts))
                
    total_rows = len(sensor_data)
    if total_rows == 0:
        print("[ERROR] Khong tim thay du lieu nao trong khoang thoi gian yeu cau.")
        conn.close()
        return
        
    print(f"[INFO] Da loc duoc {total_rows} dong du lieu mau.")
    
    # 3. Don dep cac ban ghi cu cua cac thiet bi nay
    print("[INFO] Dang don dep cac log cu trong database...")
    cursor.execute("DELETE FROM sensor_logs WHERE device_id=?", (device_ids['master_sensor'],))
    
    actuator_ids = [device_ids['PK_den'], device_ids['PK_quat'], device_ids['PN_den'], device_ids['PN_quat']]
    cursor.execute("DELETE FROM actuator_logs WHERE device_id IN (?, ?, ?, ?)", tuple(actuator_ids))
    conn.commit()
    
    # 4. Ghi du lieu vao DB
    print(f"[INFO] Dang ghi {len(sensor_data)} ban ghi vao bang sensor_logs...")
    cursor.executemany(
        "INSERT INTO sensor_logs (device_id, temp, humi, light, gas, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        sensor_data
    )
    
    print(f"[INFO] Dang ghi {len(actuator_data)} ban ghi vao bang actuator_logs...")
    cursor.executemany(
        "INSERT INTO actuator_logs (device_id, status, mode, timestamp) VALUES (?, ?, ?, ?)",
        actuator_data
    )
    
    conn.commit()
    
    # 5. Kiem tra lai so luong thuc te
    cursor.execute("SELECT COUNT(*) FROM sensor_logs WHERE device_id=?", (device_ids['master_sensor'],))
    sensor_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM actuator_logs WHERE device_id IN (?, ?, ?, ?)", tuple(actuator_ids))
    actuator_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("[SUCCESS] Da nap thanh cong du lieu mau 3 thang vao database!")
    print(f"[STATUS] Ket qua luu tru trong database:")
    print(f"  - Tong so ban ghi SensorLog: {sensor_count}")
    print(f"  - Tong so ban ghi ActuatorLog: {actuator_count}")

if __name__ == '__main__':
    populate()
