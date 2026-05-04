import random
from datetime import datetime, timedelta
import os

DEVICES = [
    (5,'light'),(6,'light'),(7,'fan'),
    (9,'light'),(10,'fan'),(11,'light'),
    (12,'light'),(13,'fan'),(14,'light'),
    (15,'fan'),(16,'light'),
]

def get_status(dtype, hour, temp, light):
    if dtype == 'fan':
        return 1 if temp > 29.5 else 0
    if 1 <= hour <= 5: return 0
    if 6 <= hour <= 8: return 1
    if 9 <= hour <= 17: return 1 if light < 300 else 0
    return 1

now = datetime.now()
rows = []
for day in range(30):
    for hour in [0,2,4,6,7,9,11,13,15,18,20,22]:
        dt = now - timedelta(days=day, hours=now.hour-hour)
        if 6<=hour<=8:
            temp  = random.uniform(23,26)
            humi  = random.uniform(68,78)
            light = random.uniform(50,150)
        elif 9<=hour<=11:
            temp  = random.uniform(27,31)
            humi  = random.uniform(58,68)
            light = random.uniform(500,750)
        elif 12<=hour<=15:
            temp  = random.uniform(31,36)
            humi  = random.uniform(48,58)
            light = random.uniform(700,950)
        elif 18<=hour<=22:
            temp  = random.uniform(27,31)
            humi  = random.uniform(60,72)
            light = random.uniform(30,120)
        else:
            temp  = random.uniform(24,27)
            humi  = random.uniform(68,80)
            light = random.uniform(0,10)

        ts = dt.strftime('%Y-%m-%d %H:%M:%S')
        for did, dtype in DEVICES:
            s = get_status(dtype, hour, temp, light)
            rows.append(
                "({},{}, 'AI',{:.1f},{:.1f},{:.1f},0.0,'{}')".format(
                    did, s, temp, humi, light, ts
                )
            )

chunk = 200
with open('train_ai_data.sql', 'w', encoding='utf-8') as f:
    f.write('USE smarthome;\n\n')
    for i in range(0, len(rows), chunk):
        block = rows[i:i+chunk]
        f.write('INSERT INTO device_logs (device_id,status,mode,temp,humi,light,gas,timestamp) VALUES\n')
        f.write(',\n'.join(block) + ';\n\n')

print('Done: {} rows -> train_ai_data.sql'.format(len(rows)))
