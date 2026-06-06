import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from models import Device, db

class DecisionNode:
    def __init__(self, feature=None, threshold=None, left=None, right=None, *, value=None):
        self.feature = feature          # Index of feature to split on
        self.threshold = threshold      # Threshold value for split
        self.left = left                # Left subtree
        self.right = right              # Right subtree
        self.value = value              # Class probabilities if leaf (list of floats)
        
    def is_leaf(self):
        return self.value is not None


class DecisionTreeClassifier:
    def __init__(self, max_depth=None, min_samples_split=2, max_features='sqrt', random_state=None):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.random_state = random_state
        self.root = None
        
    def fit(self, X, y, sample_weight=None, classes=None):
        X = np.asarray(X)
        y = np.asarray(y)
        n_samples, n_features = X.shape
        
        if sample_weight is None:
            sample_weight = np.ones(n_samples, dtype=float)
            
        if classes is not None:
            self.classes_ = np.asarray(classes)
        else:
            self.classes_ = np.array([0, 1])
            
        self.n_classes_ = len(self.classes_)
        self.rng = np.random.RandomState(self.random_state)
        
        self.root = self._build_tree(X, y, sample_weight, depth=0)
        return self
        
    def _build_tree(self, X, y, sample_weight, depth):
        n_samples, n_features = X.shape
        unique_y = np.unique(y)
        
        # Base case 1: pure node
        if len(unique_y) == 1:
            return DecisionNode(value=self._get_leaf_value(y, sample_weight))
            
        # Base case 2: max depth reached
        if self.max_depth is not None and depth >= self.max_depth:
            return DecisionNode(value=self._get_leaf_value(y, sample_weight))
            
        # Base case 3: too few samples
        if n_samples < self.min_samples_split:
            return DecisionNode(value=self._get_leaf_value(y, sample_weight))
            
        # Feature bagging
        if self.max_features == 'sqrt':
            n_sub_features = int(np.sqrt(n_features))
        elif isinstance(self.max_features, int):
            n_sub_features = min(self.max_features, n_features)
        else:
            n_sub_features = n_features
            
        n_sub_features = max(1, n_sub_features)
        feature_idxs = self.rng.choice(n_features, n_sub_features, replace=False)
        
        best_feat, best_thresh, best_gain = None, None, -1.0
        
        # Calculate parent Gini
        total_weight = np.sum(sample_weight)
        if total_weight == 0:
            return DecisionNode(value=self._get_leaf_value(y, sample_weight))
            
        class_weights = {}
        parent_gini = 1.0
        for c in self.classes_:
            c_mask = (y == c)
            c_weight = np.sum(sample_weight[c_mask])
            sample_weight_c = sample_weight[c_mask]
            class_weights[c] = (c_mask, c_weight, sample_weight_c)
            p = c_weight / total_weight
            parent_gini -= p ** 2
            
        for feat in feature_idxs:
            X_column = X[:, feat]
            thresholds = np.unique(X_column)
            if len(thresholds) <= 1:
                continue
                
            if len(thresholds) > 20:
                midpoints = np.percentile(X_column, np.linspace(5, 95, 20))
            else:
                midpoints = (thresholds[:-1] + thresholds[1:]) / 2.0
                
            # Pre-slice X_column for each class to speed up threshold loops
            X_column_by_class = {}
            for c in self.classes_:
                c_mask, _, _ = class_weights[c]
                X_column_by_class[c] = X_column[c_mask]
                
            for thresh in midpoints:
                left_c_weights = {}
                weight_l = 0.0
                for c in self.classes_:
                    _, _, sample_weight_c = class_weights[c]
                    X_column_c = X_column_by_class[c]
                    left_c_weight = np.sum(sample_weight_c[X_column_c <= thresh])
                    left_c_weights[c] = left_c_weight
                    weight_l += left_c_weight
                    
                weight_r = total_weight - weight_l
                
                if weight_l == 0 or weight_r == 0:
                    continue
                    
                gini_l = 1.0
                gini_r = 1.0
                for c in self.classes_:
                    _, c_weight_total, _ = class_weights[c]
                    left_c_weight = left_c_weights[c]
                    right_c_weight = c_weight_total - left_c_weight
                    
                    p_l = left_c_weight / weight_l
                    p_r = right_c_weight / weight_r
                    
                    gini_l -= p_l ** 2
                    gini_r -= p_r ** 2
                    
                child_gini = (weight_l / total_weight) * gini_l + (weight_r / total_weight) * gini_r
                gain = parent_gini - child_gini
                
                if gain > best_gain:
                    best_gain = gain
                    best_feat = feat
                    best_thresh = thresh
                    
        if best_gain <= 0.0 or best_feat is None:
            return DecisionNode(value=self._get_leaf_value(y, sample_weight))
            
        left_mask = X[:, best_feat] <= best_thresh
        right_mask = ~left_mask
        
        left_child = self._build_tree(X[left_mask], y[left_mask], sample_weight[left_mask], depth + 1)
        right_child = self._build_tree(X[right_mask], y[right_mask], sample_weight[right_mask], depth + 1)
        
        return DecisionNode(feature=best_feat, threshold=best_thresh, left=left_child, right=right_child)
        
    def _get_leaf_value(self, y, sample_weight):
        total_weight = np.sum(sample_weight)
        probs = np.zeros(self.n_classes_)
        if total_weight == 0:
            probs += 1.0 / self.n_classes_
            return probs
            
        for c_idx, c in enumerate(self.classes_):
            c_weight = np.sum(sample_weight[y == c])
            probs[c_idx] = c_weight / total_weight
        return probs
        
    def _predict_proba_sample(self, node, x):
        if node.is_leaf():
            return node.value
            
        if x[node.feature] <= node.threshold:
            return self._predict_proba_sample(node.left, x)
        else:
            return self._predict_proba_sample(node.right, x)
            
    def predict_proba(self, X):
        X = np.asarray(X)
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        probs = [self._predict_proba_sample(self.root, x) for x in X]
        return np.array(probs)
        
    def predict(self, X):
        probs = self.predict_proba(X)
        return np.array([self.classes_[np.argmax(p)] for p in probs])


class RandomForestClassifier:
    def __init__(self, n_estimators=100, max_depth=None, min_samples_split=2, 
                 class_weight=None, random_state=None, n_jobs=-1):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.class_weight = class_weight
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.estimators_ = []
        self.classes_ = None
        
    def fit(self, X, y):
        X = np.asarray(X)
        y = np.asarray(y)
        n_samples, n_features = X.shape
        
        self.classes_ = np.unique(y)
        self.n_classes_ = len(self.classes_)
        
        if self.class_weight == 'balanced':
            classes = self.classes_
            n_classes = self.n_classes_
            class_counts = np.bincount(y.astype(int))
            class_weights = {}
            for c in classes:
                count = class_counts[c] if c < len(class_counts) else 0
                class_weights[c] = n_samples / (n_classes * count) if count > 0 else 0.0
            sample_weight = np.array([class_weights[val] for val in y])
        else:
            sample_weight = np.ones(n_samples, dtype=float)
            
        rng = np.random.RandomState(self.random_state)
        
        self.estimators_ = []
        for i in range(self.n_estimators):
            bootstrap_idxs = rng.choice(n_samples, n_samples, replace=True)
            X_b = X[bootstrap_idxs]
            y_b = y[bootstrap_idxs]
            sw_b = sample_weight[bootstrap_idxs]
            
            tree_seed = rng.randint(0, 2**31 - 1)
            tree = DecisionTreeClassifier(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                max_features='sqrt',
                random_state=tree_seed
            )
            tree.fit(X_b, y_b, sample_weight=sw_b, classes=self.classes_)
            self.estimators_.append(tree)
            
        return self
        
    def predict_proba(self, X):
        X = np.asarray(X)
        is_single = False
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
            is_single = True
            
        all_tree_probs = []
        for tree in self.estimators_:
            all_tree_probs.append(tree.predict_proba(X))
            
        avg_probs = np.mean(all_tree_probs, axis=0)
        return avg_probs
        
    def predict(self, X):
        probs = self.predict_proba(X)
        return np.array([self.classes_[np.argmax(p)] for p in probs])

# ══════════════════════════════════════════════════════════════════════════════
# CẤU HÌNH ĐƯỜNG DẪN MODEL
# ══════════════════════════════════════════════════════════════════════════════
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR      = os.path.join(BASE_DIR, 'trained_models')
MODEL_PATH     = os.path.join(MODEL_DIR, 'random_forest_models.pkl')

# ══════════════════════════════════════════════════════════════════════════════
# SEED THIẾT BỊ NẾU CHƯA CÓ
# ══════════════════════════════════════════════════════════════════════════════
def ensure_devices_exist():
    """
    Đảm bảo 4 thiết bị AI (đèn pk, đèn pn, quạt pk, quạt pn) tồn tại trong database.
    """
    targets_info = {
        'PK_den': {'name': 'Đèn phòng khách', 'type': 'light', 'room': 'living_room'},
        'PK_quat': {'name': 'Quạt phòng khách', 'type': 'fan', 'room': 'living_room'},
        'PN_den': {'name': 'Đèn phòng ngủ', 'type': 'light', 'room': 'bedroom'},
        'PN_quat': {'name': 'Quạt phòng ngủ', 'type': 'fan', 'room': 'bedroom'},
    }
    for key, info in targets_info.items():
        dev = Device.query.filter_by(type=info['type'], room=info['room']).first()
        if not dev:
            dev = Device(name=info['name'], type=info['type'], room=info['room'])
            db.session.add(dev)
    db.session.commit()

# ══════════════════════════════════════════════════════════════════════════════
# TIỀN XỬ LÝ ĐẶC TRƯNG CHU KỲ & CHUYỂN ĐỔI BẢNG TALL -> WIDE
# ══════════════════════════════════════════════════════════════════════════════
def add_cyclic_features(df):
    """Thêm cyclic encoding cho các biến thời gian tuần hoàn."""
    df = df.copy()
    df['hour_sin']  = np.sin(2 * np.pi * df['hour']        / 24)
    df['hour_cos']  = np.cos(2 * np.pi * df['hour']        / 24)
    df['min_sin']   = np.sin(2 * np.pi * df['minute']      / 60)
    df['min_cos']   = np.cos(2 * np.pi * df['minute']      / 60)
    df['dow_sin']   = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['dow_cos']   = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * (df['month'] - 1) / 12)
    df['month_cos'] = np.cos(2 * np.pi * (df['month'] - 1) / 12)
    return df

def standardize_columns(df):
    rename_dict = {
        'Nhiệt độ (°C)': 'nhiet_do',
        'temp': 'nhiet_do',
        'Độ ẩm (%)': 'do_am',
        'humi': 'do_am',
        'Ánh sáng (lux)': 'anh_sang',
        'light': 'anh_sang',
        'Giờ': 'hour',
        'Phút': 'minute',
        'Tháng': 'month',
        'timestamp': 'timestamp',
        'Ngày': 'timestamp',
    }
    df = df.rename(columns=rename_dict)
    
    # Đảm bảo có day_of_week
    if 'day_of_week' not in df.columns:
        if 'day_of_week_num' in df.columns:
            df['day_of_week'] = df['day_of_week_num']
        elif 'Thứ' in df.columns:
            days_map = {
                'Thứ Hai': 0, 'Thứ Ba': 1, 'Thứ Tư': 2, 'Thứ Năm': 3,
                'Thứ Sáu': 4, 'Thứ Bảy': 5, 'Chủ Nhật': 6,
                'Thứ 2': 0, 'Thứ 3': 1, 'Thứ 4': 2, 'Thứ 5': 3,
                'Thứ 6': 4, 'Thứ 7': 5, 'Chủ nhật': 6
            }
            df['day_of_week'] = df['Thứ'].map(days_map)
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            
    # Trích xuất các trường từ timestamp nếu thiếu
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if 'hour' not in df.columns:
            df['hour'] = df['timestamp'].dt.hour
        if 'minute' not in df.columns:
            df['minute'] = df['timestamp'].dt.minute
        if 'month' not in df.columns:
            df['month'] = df['timestamp'].dt.month
            
    if 'is_weekend' not in df.columns and 'day_of_week' in df.columns:
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
    return df

def pivot_tall_df(df):
    """
    Nếu dataset truyền vào ở dạng dọc (tall format) từ DB, thực hiện pivot
    về dạng ngang (wide format) để tương thích với cấu trúc huấn luyện 4 thiết bị.
    """
    if 'Device_ID' in df.columns or 'Tên thiết bị' in df.columns:
        room_col = 'Phòng' if 'Phòng' in df.columns else 'room'
        type_col = 'Tên thiết bị' if 'Tên thiết bị' in df.columns else ('type' if 'type' in df.columns else None)
        status_col = 'Trạng thái' if 'Trạng thái' in df.columns else 'status'
        
        def get_target_name(row):
            r = str(row[room_col]).lower()
            t = str(row[type_col]).lower() if type_col else ""
            
            is_pk = 'khách' in r or 'living' in r or 'pk' in r
            is_pn = 'ngủ' in r or 'bedroom' in r or 'pn' in r
            is_den = 'đèn' in t or 'light' in t or 'den' in t
            is_quat = 'quạt' in t or 'fan' in t or 'quat' in t
            
            if is_pk and is_den:
                return 'PK_den'
            elif is_pk and is_quat:
                return 'PK_quat'
            elif is_pn and is_den:
                return 'PN_den'
            elif is_pn and is_quat:
                return 'PN_quat'
            return None
            
        df['target_name'] = df.apply(get_target_name, axis=1)
        df = df.dropna(subset=['target_name'])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['time_key'] = df['timestamp'].dt.round('10min')
        
        df_pivot = df.pivot_table(index='time_key', columns='target_name', values=status_col, aggfunc='last')
        
        sensor_cols = []
        for col in ['nhiet_do', 'do_am', 'anh_sang', 'temp', 'humi', 'light']:
            if col in df.columns:
                sensor_cols.append(col)
        df_sensors = df.groupby('time_key')[sensor_cols].mean()
        
        df_wide = df_sensors.join(df_pivot, how='inner').reset_index()
        df_wide = df_wide.rename(columns={'time_key': 'timestamp'})
        
        targets = ['PN_quat', 'PN_den', 'PK_quat', 'PK_den']
        for t in targets:
            if t not in df_wide.columns:
                df_wide[t] = 0
            else:
                df_wide[t] = df_wide[t].ffill().bfill().fillna(0).astype(int)
                
        return df_wide
    return df


# ══════════════════════════════════════════════════════════════════════════════
# HÀM TRAIN VÀ LƯU MODEL RANDOM FOREST
# ══════════════════════════════════════════════════════════════════════════════
def train_and_save_model(dataset_path):
    """
    Đọc dữ liệu, tiền xử lý và huấn luyện RandomForestClassifier cho cả 4 thiết bị.
    Trả về dict {tên_thiết_bị: accuracy%} để hiển thị trên web.
    """
    # 1. ĐỌC FILE DỮ LIỆU
    if dataset_path.endswith('.xlsx'):
        xls = pd.ExcelFile(dataset_path)
        target_sheet = None
        for sheet in xls.sheet_names:
            if sheet.lower().strip() in ["dữ liệu thô", "sheet1"]:
                target_sheet = sheet
                break
        if target_sheet is None:
            target_sheet = xls.sheet_names[0]
        df = pd.read_excel(dataset_path, sheet_name=target_sheet)
    else:
        df = pd.read_csv(dataset_path)

    # 2. CHUYỂN ĐỔI SANG DẠNG NGANG NẾU CẦN & CHUẨN HÓA CỘT
    df = pivot_tall_df(df)
    df = standardize_columns(df)
    
    # 3. ĐỒNG BỘ ĐẶC TRƯNG CHU KỲ
    if 'hour_sin' not in df.columns:
        df = add_cyclic_features(df)

    FEATURE_COLS = [
        'nhiet_do', 'do_am', 'anh_sang', 'is_weekend',
        'hour_sin', 'hour_cos',
        'min_sin',  'min_cos',
        'dow_sin',  'dow_cos',
        'month_sin','month_cos',
    ]
    TARGETS   = ['PN_quat', 'PN_den', 'PK_quat', 'PK_den']
    LABELS_VN = {
        'PN_quat': 'Phòng Ngủ - Quạt',
        'PN_den' : 'Phòng Ngủ - Đèn',
        'PK_quat': 'Phòng Khách - Quạt',
        'PK_den' : 'Phòng Khách - Đèn',
    }

    # Đảm bảo có ít nhất 20 dòng để train
    if len(df) < 20:
        raise ValueError(f"Dữ liệu không đủ dòng để train ({len(df)} dòng). Cần tối thiểu 20 dòng.")

    # 4. CHIA DỮ LIỆU SỬ DỤNG OUT-OF-TIME SPLIT THEO THÁNG (FALLBACK SANG STRATIFY NẾU CẦN)
    splits = {}
    try:
        df['year_month'] = df['timestamp'].dt.to_period('M')
        unique_periods = df['year_month'].unique()
        if len(unique_periods) > 1:
            for t in TARGETS:
                X_tr_list, X_te_list = [], []
                y_tr_list, y_te_list = [], []
                for period, group in df.groupby('year_month'):
                    group = group.sort_values('timestamp')
                    X_group = group[FEATURE_COLS].values
                    y_group = group[t].values
                    split_idx = int(len(group) * 0.8)
                    X_tr_list.append(X_group[:split_idx])
                    y_tr_list.append(y_group[:split_idx])
                    X_te_list.append(X_group[split_idx:])
                    y_te_list.append(y_group[split_idx:])
                splits[t] = (
                    np.vstack(X_tr_list),
                    np.vstack(X_te_list),
                    np.concatenate(y_tr_list),
                    np.concatenate(y_te_list)
                )
        else:
            raise ValueError("Not enough months for out-of-time split")
    except Exception as e:
        print(f"[INFO] Out-of-time split failed ({e}), falling back to train_test_split.")
        from sklearn.model_selection import train_test_split
        for t in TARGETS:
            X_data = df[FEATURE_COLS].values
            y_data = df[t].values
            if len(np.unique(y_data)) > 1:
                X_tr, X_te, y_tr, y_te = train_test_split(
                    X_data, y_data, test_size=0.2, random_state=42, stratify=y_data
                )
            else:
                X_tr, X_te, y_tr, y_te = train_test_split(
                    X_data, y_data, test_size=0.2, random_state=42
                )
            splits[t] = (X_tr, X_te, y_tr, y_te)

    # 5. HUẤN LUYỆN VÀ OPTIMIZE NGƯỠNG F1 CHO TỪNG THIẾT BỊ
    models = {}
    best_thresholds = {}
    results = {}
    
    total_correct = 0
    total_samples = 0
    thresholds_to_test = np.arange(0.3, 0.85, 0.005)

    for t in TARGETS:
        X_tr, X_te, y_tr, y_te = splits[t]
        
        # Huấn luyện Random Forest Classifier
        rf_model = RandomForestClassifier(
            n_estimators=20,
            max_depth=12,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_tr, y_tr)
        models[t] = rf_model
        
        # Tìm ngưỡng tối ưu cho F1-Score
        y_proba_te = rf_model.predict_proba(X_te)[:, 1]
        best_thresh = 0.5
        best_f1 = 0.0
        
        for thresh in thresholds_to_test:
            y_pred_custom = (y_proba_te >= thresh).astype(int)
            f1 = f1_score(y_te, y_pred_custom, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_thresh = thresh
                
        best_thresholds[t] = best_thresh
        
        # Đánh giá độ chính xác tại ngưỡng tối ưu
        y_pred = (y_proba_te >= best_thresh).astype(int)
        acc = accuracy_score(y_te, y_pred)
        results[LABELS_VN[t]] = round(acc * 100, 2)
        
        total_correct += np.sum(y_pred == y_te)
        total_samples += len(y_te)

    if total_samples > 0:
        results["Toàn bộ hệ thống"] = round((total_correct / total_samples) * 100, 2)
    else:
        results["Toàn bộ hệ thống"] = 0.0

    # 6. LƯU CÁC MODEL VÀ BỘ NGƯỠNG TỐI ƯU
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({
            'models': models,
            'thresholds': best_thresholds
        }, f)
        
    print(f"[INFO] Saved Random Forest models at: {MODEL_PATH}")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# HÀM DỰ ĐOÁN VỚI BỘ MODEL RANDOM FOREST VÀ NGƯỠNG TỐI ƯU
# ══════════════════════════════════════════════════════════════════════════════
def predict_behavior(temp, humi, light, current_datetime, home_id=None):
    """
    Dự đoán trạng thái bật/tắt cho toàn bộ 4 thiết bị AI dựa trên mô hình RF đã huấn luyện.
    Trả về dict {device_id: 0 hoặc 1}.
    """
    predictions = {}
    
    if not os.path.exists(MODEL_PATH):
        print("[WARNING] Model not trained yet! Please run training first.")
        return predictions

    # Đọc bộ model và thresholds
    with open(MODEL_PATH, 'rb') as f:
        saved_data = pickle.load(f)
        
    models = saved_data.get('models', {})
    thresholds = saved_data.get('thresholds', {})

    # Ánh xạ thiết bị thực tế trong Database
    from models import Device
    devices_map = {
        'PK_den': Device.query.filter_by(type='light', room='living_room').first(),
        'PK_quat': Device.query.filter_by(type='fan', room='living_room').first(),
        'PN_den': Device.query.filter_by(type='light', room='bedroom').first(),
        'PN_quat': Device.query.filter_by(type='fan', room='bedroom').first(),
    }
    
    # Seeding dự phòng nếu thiết bị chưa được khởi tạo
    if any(d is None for d in devices_map.values()):
        try:
            ensure_devices_exist()
            devices_map = {
                'PK_den': Device.query.filter_by(type='light', room='living_room').first(),
                'PK_quat': Device.query.filter_by(type='fan', room='living_room').first(),
                'PN_den': Device.query.filter_by(type='light', room='bedroom').first(),
                'PN_quat': Device.query.filter_by(type='fan', room='bedroom').first(),
            }
        except Exception as e:
            print(f"Error seeding devices during predict: {e}")

    # Tính toán đặc trưng chu kỳ
    hour = current_datetime.hour
    minute = current_datetime.minute
    day_of_week = current_datetime.weekday()
    month = current_datetime.month
    is_weekend = 1 if day_of_week >= 5 else 0

    hs  = np.sin(2 * np.pi * hour        / 24)
    hc  = np.cos(2 * np.pi * hour        / 24)
    ms  = np.sin(2 * np.pi * minute      / 60)
    mc  = np.cos(2 * np.pi * minute      / 60)
    ds  = np.sin(2 * np.pi * day_of_week / 7)
    dc  = np.cos(2 * np.pi * day_of_week / 7)
    mos = np.sin(2 * np.pi * (month - 1)   / 12)
    moc = np.cos(2 * np.pi * (month - 1)   / 12)

    base_features = [temp, humi, light, is_weekend, hs, hc, ms, mc, ds, dc, mos, moc]

    for t, dev in devices_map.items():
        if dev and t in models:
            model = models[t]
            thresh = thresholds.get(t, 0.5)
            try:
                # Chạy dự đoán xác suất và so sánh với ngưỡng tối ưu F1
                prob = model.predict_proba([base_features])[0][1]
                pred_status = 1 if prob >= thresh else 0
                predictions[dev.id] = pred_status
            except Exception as e:
                print(f"[WARNING] Error predicting for device {t} (ID {dev.id}): {e}")
                predictions[dev.id] = 0

    return predictions