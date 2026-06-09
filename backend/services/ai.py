import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from models import Device, db

from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.tree import DecisionTreeClassifier as SklearnDecisionTreeClassifier

# ============================================================================
# 1. HÀM HỖ TRỢ HUẤN LUYỆN ĐA LUỒNG (CUSTOM FORESTS LOGIC)
# ============================================================================
def _train_single_tree(args):
    tree_idx, X, y, tree_params, balanced_sampling, rng_seed = args
    rng = np.random.RandomState(rng_seed)
    n_samples = len(y)
    
    # 1. Tự code logic Lấy mẫu (Bootstrapping / Balanced Sampling)
    if balanced_sampling:
        classes = np.unique(y)
        class_indices = {}
        min_count = float('inf')
        for cls in classes:
            indices = np.where(y == cls)[0]
            class_indices[cls] = indices
            min_count = min(min_count, len(indices))
            
        balanced_indices = []
        for cls in classes:
            # Lấy mẫu cân bằng cho từng class
            sampled = rng.choice(class_indices[cls], size=int(min_count), replace=True)
            balanced_indices.append(sampled)
        indices = np.concatenate(balanced_indices)
        rng.shuffle(indices)
    else:
        # Bootstrapping truyền thống
        indices = rng.choice(n_samples, size=n_samples, replace=True)
        
    X_boot = X[indices]
    y_boot = y[indices]
    
    # 2. Kế thừa thuật toán CART siêu tốc của sklearn cho từng cây con
    tree = SklearnDecisionTreeClassifier(random_state=rng_seed, **tree_params)
    tree.fit(X_boot, y_boot)
    
    return tree_idx, tree, tree.feature_importances_

# ============================================================================
# 2. CUSTOM RANDOM FOREST CLASSIFIER
# ============================================================================
class CustomRandomForest(BaseEstimator, ClassifierMixin):
    def __init__(self, n_estimators=100, max_depth=None, min_samples_split=2,
                 min_samples_leaf=1, max_features='sqrt', balanced_sampling=True,
                 class_weight=None, random_state=42, n_jobs=1):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.balanced_sampling = balanced_sampling
        self.class_weight = class_weight
        self.random_state = random_state
        self.n_jobs = n_jobs

    def fit(self, X, y):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int32)
        
        self.classes_ = np.unique(y)
        self.n_classes_ = len(self.classes_)
        self.n_features_ = X.shape[1]
        
        # Tham số sẽ truyền xuống cho DecisionTree
        tree_params = {
            'max_depth': self.max_depth,
            'min_samples_split': self.min_samples_split,
            'min_samples_leaf': self.min_samples_leaf,
            'max_features': self.max_features,
            'class_weight': self.class_weight,
        }
        
        master_rng = np.random.RandomState(self.random_state)
        tree_seeds = master_rng.randint(0, 2**31 - 1, size=self.n_estimators)
        
        args_list = [
            (i, X, y, tree_params, self.balanced_sampling, int(tree_seeds[i]))
            for i in range(self.n_estimators)
        ]
        
        self.estimators_ = [None] * self.n_estimators
        self.feature_importances_ = np.zeros(self.n_features_)
        
        n_jobs = self.n_jobs if self.n_jobs != -1 else (os.cpu_count() or 1)
            
        if n_jobs > 1:
            print(f"  [PARALLEL] Dang huan luyen {self.n_estimators} cay ({n_jobs} workers)...")
            with ProcessPoolExecutor(max_workers=n_jobs) as executor:
                futures = {executor.submit(_train_single_tree, args): args[0] for args in args_list}
                for future in as_completed(futures):
                    tree_idx, tree, fi = future.result()
                    self.estimators_[tree_idx] = tree
                    self.feature_importances_ += fi
        else:
            for i, args in enumerate(args_list):
                _, tree, fi = _train_single_tree(args)
                self.estimators_[i] = tree
                self.feature_importances_ += fi
                
        # Tính trung bình feature importance của cả rừng
        self.feature_importances_ /= self.n_estimators
        
        return self

    def predict_proba(self, X):
        # Tự code logic gom nhóm (Aggregation) của Random Forest
        X = np.asarray(X, dtype=np.float64)
        all_proba = np.zeros((X.shape[0], self.n_classes_))
        
        for tree in self.estimators_:
            all_proba += tree.predict_proba(X)
            
        all_proba /= self.n_estimators
        return all_proba

    def predict(self, X):
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]

# Alias to avoid breaking references in other files
RandomForestClassifier = CustomRandomForest

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
    Đảm bảo TẤT CẢ thiết bị phần cứng tồn tại trong database.
    """
    all_devices = [
        {'name': 'Đèn phòng khách',  'type': 'light', 'room': 'living_room'},
        {'name': 'Quạt phòng khách', 'type': 'fan',   'room': 'living_room'},
        {'name': 'Đèn phòng ngủ',    'type': 'light', 'room': 'bedroom'},
        {'name': 'Quạt phòng ngủ',   'type': 'fan',   'room': 'bedroom'},
        {'name': 'Đèn phòng bếp',    'type': 'light', 'room': 'kitchen'},
        {'name': 'Đèn cổng',         'type': 'light', 'room': 'gate'},
        {'name': 'Đèn nhà vệ sinh',  'type': 'light', 'room': 'bathroom'},
        {'name': 'Còi báo động',     'type': 'alarm', 'room': 'kitchen'},
    ]
    for info in all_devices:
        dev = Device.query.filter_by(type=info['type'], room=info['room']).first()
        if not dev:
            dev = Device(name=info['name'], type=info['type'], room=info['room'])
            db.session.add(dev)
            print(f"[DB] Created device: {info['name']} ({info['type']}/{info['room']})")
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
        
        # Huấn luyện Custom Random Forest Classifier
        rf_model = CustomRandomForest(
            n_estimators=20,
            max_depth=12,
            class_weight='balanced',
            random_state=42,
            n_jobs=1
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