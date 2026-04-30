import os
import pickle
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from models import Device

# Định nghĩa chính xác class đã dùng khi train để có thể load model
class LogisticRegression(object):
    def __init__(self, eta=0.01, n_iter=50, class_weight=None):
        self.eta = eta
        self.n_iter = n_iter
        self.class_weight = class_weight

    def _compute_sample_weights(self, y):
        if self.class_weight == 'balanced':
            classes, counts = np.unique(y, return_counts=True)
            n_samples = len(y)
            n_classes = len(classes)
            weight_map = {c: n_samples / (n_classes * cnt) for c, cnt in zip(classes, counts)}
            return np.array([weight_map[yi] for yi in y])
        return np.ones(len(y))

    def fit(self, X, y):
        sample_weights = self._compute_sample_weights(y)
        self.w_ = np.zeros(1 + X.shape[1])
        self.cost_ = []
        for i in range(self.n_iter):
            y_val = self.activation(X)
            errors = (y - y_val) * sample_weights
            self.w_[1:] += self.eta * X.T.dot(errors)
            self.w_[0]  += self.eta * errors.sum()
            self.cost_.append(self._logit_cost(y, self.activation(X), sample_weights))
        return self

    def _logit_cost(self, y, y_val, sample_weights=None):
        epsilon = 1e-10
        y_val_clipped = np.clip(y_val, epsilon, 1 - epsilon)
        loss = -y * np.log(y_val_clipped) - (1 - y) * np.log(1 - y_val_clipped)
        if sample_weights is not None:
            loss = loss * sample_weights
        return loss.mean()

    def _sigmoid(self, z):
        return 1.0 / (1.0 + np.exp(-z))

    def net_input(self, X):
        return np.dot(X, self.w_[1:]) + self.w_[0]

    def activation(self, X):
        return self._sigmoid(self.net_input(X))

    def predict_proba(self, X):
        return self.activation(X)

    def predict(self, X):
        return np.where(self.net_input(X) >= 0.0, 1, 0)


# Cấu hình đường dẫn lưu model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'trained_models')
MODEL_PATH = os.path.join(MODEL_DIR, 'logistic_regression_model.pkl')
PREPROCESSOR_PATH = os.path.join(MODEL_DIR, 'preprocessor.pkl')

def train_and_save_model(dataset_path):
    """
    Đọc dữ liệu, tiền xử lý, huấn luyện và lưu model.
    """
    if dataset_path.endswith('.xlsx'):
        df = pd.read_excel(dataset_path, sheet_name='📊 Dữ liệu thô')
    else:
        df = pd.read_csv(dataset_path)

    # Chuyển đổi và trích xuất đặc trưng thời gian
    df['Ngày'] = pd.to_datetime(df['Ngày'])
    df['day_of_week_num'] = df['Ngày'].dt.dayofweek
    df['day_of_month'] = df['Ngày'].dt.day

    numerical_cols = ['Giờ', 'Phút', 'Nhiệt độ (°C)', 'Độ ẩm (%)', 'Ánh sáng (lux)', 'day_of_week_num', 'day_of_month', 'Tháng']
    categorical_cols = ['Device_ID', 'Tên thiết bị', 'Phòng']
    all_feature_cols = numerical_cols + categorical_cols

    X = df[all_feature_cols]
    y = df['Trạng thái'].values

    # Pipeline tiền xử lý
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_cols),
            ('num', StandardScaler(), numerical_cols)
        ],
        remainder='drop'
    )

    X_proc = preprocessor.fit_transform(X)

    # Huấn luyện model dùng class tự xây dựng
    logistR = LogisticRegression(n_iter=5000, eta=0.001, class_weight='balanced')
    logistR.fit(X_proc, y)

    # Lưu model và bộ tiền xử lý
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(logistR, f)
    with open(PREPROCESSOR_PATH, 'wb') as f:
        pickle.dump(preprocessor, f)

    return True

def predict_behavior(temp, humi, light, current_datetime):
    """
    Dự đoán trạng thái bật/tắt cho toàn bộ thiết bị qua model dùng chung.
    Sử dụng current_datetime (datetime object) thay vì nhập tay giờ/tháng.
    """
    predictions = {}
    devices = Device.query.filter(Device.type.in_(["light", "fan"])).all()

    if not os.path.exists(MODEL_PATH) or not os.path.exists(PREPROCESSOR_PATH):
        print("Model chưa được huấn luyện!")
        return predictions

    # Load model & preprocessor
    with open(PREPROCESSOR_PATH, 'rb') as f:
        preprocessor = pickle.load(f)
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)

    # Trích xuất thời gian
    hour = current_datetime.hour
    minute = current_datetime.minute
    day_of_week_num = current_datetime.weekday()
    day_of_month = current_datetime.day
    month = current_datetime.month

    for device in devices:
        # Xây dựng vector đặc trưng cho từng thiết bị
        device_name = 'Quạt' if device.type == 'fan' else 'Đèn'
        
        # Nếu database của bạn có lưu phòng (room), bạn có thể gán room_name = device.room
        # Ở đây tôi mặc định là 'Phòng khách' cho Quạt và 'Phòng ngủ' cho đèn dựa theo data mẫu
        room_name = 'Phòng khách' if device.type == 'fan' else 'Phòng ngủ'
        
        df_input = pd.DataFrame([{
            'Giờ': hour,
            'Phút': minute,
            'Nhiệt độ (°C)': temp,
            'Độ ẩm (%)': humi,
            'Ánh sáng (lux)': light,
            'day_of_week_num': day_of_week_num,
            'day_of_month': day_of_month,
            'Tháng': month,
            'Device_ID': device.id,
            'Tên thiết bị': device_name,
            'Phòng': room_name
        }])

        X_proc = preprocessor.transform(df_input)
        pred = model.predict(X_proc)[0]
        predictions[device.id] = int(pred)

    return predictions