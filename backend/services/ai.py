from models import Device, DeviceLog


def predict_behavior(temp, humi, light, hour, month):
    """
    Predict trạng thái bật/tắt cho từng thiết bị dựa trên dữ liệu cảm biến.
    Trả về dict { device_id: status (0|1) }
    """
    predictions = {}
    devices = Device.query.filter(Device.type.in_(["light", "fan"])).all()

    for device in devices:
        if device.type == "fan" and device.sensor_type == "temp":
            status = _predict_fan(temp, humi, light, hour, month)
        elif device.type == "light" and device.sensor_type == "light":
            status = _predict_led(temp, humi, light, hour, month)
        else:
            continue
        predictions[device.id] = status

    return predictions


def _predict_fan(t, h, l, hour, month):
    """Logistic regression predict quạt."""
    t_s = (t - 28.52) / 4.73
    h_s = (h - 75.99) / 5.41
    l_s = (l - 301.43) / 287.79
    g_s = (hour - 11.58) / 6.75
    m_s = (month - 2.00) / 0.83
    z   = t_s * 1.867 + h_s * 0.002 + l_s * 0.232 + g_s * 0.224 + m_s * 0.132 + 0.181
    return 1 if z > 0 else 0


def _predict_led(t, h, l, hour, month):
    """Logistic regression predict đèn."""
    t_s = (t - 27.72) / 3.73
    h_s = (h - 76.74) / 4.11
    l_s = (l - 284.40) / 284.88
    g_s = (hour - 11.50) / 6.92
    m_s = (month - 2.00) / 0.83
    z   = t_s * 0.635 + h_s * -0.101 + l_s * -4.260 + g_s * 3.105 + m_s * -0.225 - 4.722
    return 1 if z > 0 else 0