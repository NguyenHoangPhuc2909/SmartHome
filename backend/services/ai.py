import os
import pickle
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from models import Device

# ══════════════════════════════════════════════════════════════════════════════
# CLASS LOGISTIC REGRESSION TỰ VIẾT (DÙNG NHẤT QUÁN - KHÔNG IMPORT SKLEARN LR)
# ══════════════════════════════════════════════════════════════════════════════
class LogisticRegression:
    def __init__(self, eta=0.01, n_iter=1000, class_weight=None):
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
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))  # clip tránh overflow

    def net_input(self, X):
        return np.dot(X, self.w_[1:]) + self.w_[0]

    def activation(self, X):
        return self._sigmoid(self.net_input(X))

    def predict_proba(self, X):
        return self.activation(X)

    def predict(self, X):
        return np.where(self.net_input(X) >= 0.0, 1, 0)

    def score(self, X, y):
        """Tính accuracy để tương thích với sklearn API."""
        preds = self.predict(X)
        return np.mean(preds == y)


# ══════════════════════════════════════════════════════════════════════════════
# CẤU HÌNH ĐƯỜNG DẪN MODEL
# ══════════════════════════════════════════════════════════════════════════════
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR      = os.path.join(BASE_DIR, 'trained_models')
MODEL_PATH     = os.path.join(MODEL_DIR, 'logistic_regression_model.pkl')
PREPROCESSOR_PATH = os.path.join(MODEL_DIR, 'preprocessor.pkl')


# ══════════════════════════════════════════════════════════════════════════════
# HÀM TRAIN VÀ LƯU MODEL
# ══════════════════════════════════════════════════════════════════════════════
def train_and_save_model(dataset_path):
    """
    Đọc dữ liệu, tiền xử lý, huấn luyện LogisticRegression tự viết và lưu lại.
    Trả về dict {tên_thiết_bị: accuracy%} để hiển thị trên web.
    """

    # 1. ĐỌC FILE ─────────────────────────────────────────────────────────────
    if dataset_path.endswith('.xlsx'):
        xls = pd.ExcelFile(dataset_path)
        target_sheet = None
        for sheet in xls.sheet_names:
            if sheet.lower().strip() == "dữ liệu thô":
                target_sheet = sheet
                break
        if target_sheet is None:
            raise ValueError(
                f"Không tìm thấy sheet 'Dữ liệu thô'. Các sheet hiện có: {xls.sheet_names}"
            )
        df = pd.read_excel(dataset_path, sheet_name=target_sheet)
    else:
        df = pd.read_csv(dataset_path)

    # 2. TRÍCH XUẤT ĐẶC TRƯNG THỜI GIAN ───────────────────────────────────────
    df['Ngày'] = pd.to_datetime(df['Ngày'])
    df['day_of_week_num'] = df['Ngày'].dt.dayofweek
    df['day_of_month']    = df['Ngày'].dt.day

    numerical_cols   = ['Giờ', 'Phút', 'Nhiệt độ (°C)', 'Độ ẩm (%)',
                        'Ánh sáng (lux)', 'day_of_week_num', 'day_of_month', 'Tháng']
    categorical_cols = ['Device_ID', 'Tên thiết bị', 'Phòng']
    all_feature_cols = numerical_cols + categorical_cols

    # Xóa dòng rỗng
    df = df.dropna(subset=all_feature_cols + ['Trạng thái'])

    if len(df) < 20:
        raise ValueError("Dataset quá ít dòng (< 20). Hãy thu thập thêm dữ liệu.")

    X = df[all_feature_cols]
    y = df['Trạng thái'].values.astype(int)

    # 3. CHIA TRAIN / TEST ─────────────────────────────────────────────────────
    # stratify=y: giữ tỷ lệ BẬT/TẮT đồng đều giữa train và test (giống Colab)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 4. PIPELINE TIỀN XỬ LÝ ──────────────────────────────────────────────────
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_cols),
            ('num', StandardScaler(), numerical_cols)
        ],
        remainder='drop'
    )

    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc  = preprocessor.transform(X_test)

    # 5. HUẤN LUYỆN MODEL TỰ VIẾT (TRAIN RIÊNG TỪNG THIẾT BỊ) ─────────────────
    models = {}
    results = {}
    
    # Tính accuracy tổng
    total_correct = 0
    total_samples = 0

    X_train_df = X_train.reset_index(drop=True)
    y_train_arr = y_train
    X_test_df = X_test.reset_index(drop=True)
    y_test_arr = y_test

    for device_id in df['Device_ID'].unique():
        # Lọc dữ liệu train cho thiết bị này
        train_mask = (X_train_df['Device_ID'] == device_id).values
        test_mask = (X_test_df['Device_ID'] == device_id).values
        
        if train_mask.sum() > 0:
            model = LogisticRegression(eta=0.001, n_iter=5000, class_weight='balanced')
            model.fit(X_train_proc[train_mask], y_train_arr[train_mask])
            models[device_id] = model
            
            # Tính accuracy trên tập test của thiết bị này
            if test_mask.sum() > 0:
                acc = model.score(X_test_proc[test_mask], y_test_arr[test_mask])
                device_name = df.loc[df['Device_ID'] == device_id, 'Tên thiết bị'].iloc[0]
                results[f"{device_name} (ID {device_id})"] = round(acc * 100, 2)
                
                # Cộng dồn để tính accuracy tổng
                preds = model.predict(X_test_proc[test_mask])
                total_correct += np.sum(preds == y_test_arr[test_mask])
                total_samples += test_mask.sum()

    if total_samples > 0:
        results["Toàn bộ hệ thống"] = round((total_correct / total_samples) * 100, 2)
    else:
        results["Toàn bộ hệ thống"] = 0.0

    # 7. LƯU DICTIONARY CÁC MODEL & PREPROCESSOR ──────────────────────────────
    os.makedirs(MODEL_DIR, exist_ok=True)

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(models, f)
    with open(PREPROCESSOR_PATH, 'wb') as f:
        pickle.dump(preprocessor, f)

    print(f"✅ Đã lưu model tại: {MODEL_PATH}")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# HÀM DỰ ĐOÁN
# ══════════════════════════════════════════════════════════════════════════════
def predict_behavior(temp, humi, light, current_datetime):
    """
    Dự đoán trạng thái bật/tắt cho toàn bộ thiết bị (light, fan).
    Trả về dict {device_id: 0 hoặc 1}.
    """
    predictions = {}
    devices = Device.query.filter(Device.type.in_(["light", "fan"])).all()

    if not os.path.exists(MODEL_PATH) or not os.path.exists(PREPROCESSOR_PATH):
        print("⚠️  Model chưa được huấn luyện! Hãy upload dataset và train trước.")
        return predictions

    # Load dictionary models & preprocessor
    with open(PREPROCESSOR_PATH, 'rb') as f:
        preprocessor = pickle.load(f)
    with open(MODEL_PATH, 'rb') as f:
        models = pickle.load(f)

    # Trích xuất thời gian
    hour            = current_datetime.hour
    minute          = current_datetime.minute
    day_of_week_num = current_datetime.weekday()
    day_of_month    = current_datetime.day
    month           = current_datetime.month

    for device in devices:
        device_name = 'Quạt' if device.type == 'fan' else 'Đèn'

        # FIX: Dùng device.room từ DB thay vì hardcode
        room_name = device.room if device.room else 'Phòng khách'

        df_input = pd.DataFrame([{
            'Giờ':             hour,
            'Phút':            minute,
            'Nhiệt độ (°C)':   temp,
            'Độ ẩm (%)':       humi,
            'Ánh sáng (lux)':  light,
            'day_of_week_num': day_of_week_num,
            'day_of_month':    day_of_month,
            'Tháng':           month,
            'Device_ID':       device.id,
            'Tên thiết bị':    device_name,
            'Phòng':           room_name,
        }])

        try:
            X_proc = preprocessor.transform(df_input)
            model = models.get(device.id)
            if model:
                pred_status = int(model.predict(X_proc)[0])
                predictions[device.id] = pred_status
        except Exception as e:
            print(f"⚠️  Lỗi dự đoán thiết bị {device.id}: {e}")
            predictions[device.id] = 0  # fallback tắt

    return predictions