import os
import numpy as np
import cv2
import onnxruntime as ort

class LivenessModel:
    _instance = None
    _session = None
    _input_name = None
    
    @staticmethod
    def get_instance():
        if LivenessModel._instance is None:
            LivenessModel._instance = LivenessModel()
        return LivenessModel._instance

    def __init__(self):
        # Đường dẫn tương đối từ thư mục backend
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "trained_models", "real_or_fake.onnx")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Liveness model not found at {model_path}")
        
        print(f"[INFO] Loading liveness model from: {model_path}")
        try:
            self._session = ort.InferenceSession(
                model_path,
                providers=['CPUExecutionProvider']
            )
            self._input_name = self._session.get_inputs()[0].name
            print(f"[INFO] Liveness model loaded successfully! Input name: {self._input_name}")
        except Exception as e:
            print(f"[ERROR] Failed to load ONNX liveness model: {e}")
            raise

    def check_liveness(self, face_image: np.ndarray, threshold: float = 0.95) -> tuple:
        """
        Kiểm tra ảnh thật/giả sử dụng model anti-spoofing MobileNetV3-Large.
        Đầu vào: face_image (ảnh cắt khuôn mặt, dạng BGR từ OpenCV).
        Trả về: (is_live: bool, live_score: float).
        """
        if face_image is None or face_image.size == 0:
            return False, 0.0

        try:
            # 1. Đảm bảo ảnh ở dạng RGB (như trong Colab notebook)
            if len(face_image.shape) == 2:  # Grayscale
                img_rgb = cv2.cvtColor(face_image, cv2.COLOR_GRAY2RGB)
            elif face_image.shape[2] == 4:  # BGRA
                img_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGRA2RGB)
            else:
                img_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                
            # 2. Resize về kích thước model (224x224)
            img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
            
            # 3. Thêm batch dimension và chuyển sang float32
            # Model MobileNetV3Large_FaceAntiSpoof_TF có include_preprocessing=True, 
            # nên đầu vào là ảnh RGB trong khoảng [0.0, 255.0].
            batch = np.expand_dims(img_resized, axis=0).astype(np.float32)
            
            # 4. Chạy inference
            preds = self._session.run(None, {self._input_name: batch})
            
            # Tìm output node 'live_score' bằng tên của nó
            output_names = [o.name for o in self._session.get_outputs()]
            if "live_score" in output_names:
                live_score_idx = output_names.index("live_score")
                live_score = float(preds[live_score_idx][0][0])
            else:
                # Nếu không khớp tên, fallback về output đầu tiên
                live_score = float(preds[0][0][0])
                
            is_live = live_score >= threshold
            return is_live, live_score
            
        except Exception as e:
            print(f"[CẢNH BÁO] Lỗi trong quá trình chạy kiểm tra liveness: {e}")
            # Trả về True kèm theo điểm 1.0 làm fallback để tránh chặn nhầm người dùng khi có lỗi hệ thống bất ngờ
            return True, 1.0
