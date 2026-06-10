import os
import numpy as np
import cv2
import onnxruntime as ort
from config import Config


class EmbeddingModel:
    _instances = {}

    @staticmethod
    def get_instance(model_type="mobilefacenet"):
        """Factory pattern — load model theo type (mobilefacenet hoặc resnet34)"""
        if model_type not in EmbeddingModel._instances:
            EmbeddingModel._instances[model_type] = EmbeddingModel(model_type)
        return EmbeddingModel._instances[model_type]

    def __init__(self, model_type="mobilefacenet"):
        """Load model ONNX"""
        self.model_type = model_type
        
        if model_type == "mobilefacenet":
            model_path = Config.FACE_MODEL_PATH
        elif model_type == "resnet34":
            model_path = getattr(Config, "FACE_MODEL_RESNET34_PATH", None)
            if not model_path:
                raise ValueError("FACE_MODEL_RESNET34_PATH is not configured.")
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Could not find {model_type} model at: {model_path}")
        
        try:
            print(f"[INFO] Loading {model_type} model: {model_path}")
            
            # Tạo ONNX Runtime session
            self._session = ort.InferenceSession(
                model_path,
                providers=['CPUExecutionProvider']
            )
            
            # Lấy input và output names
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            
            # In thông tin model
            input_shape = self._session.get_inputs()[0].shape
            print(f"[INFO] {model_type} input: {self._input_name}, shape: {input_shape}")
            print(f"[INFO] {model_type} output: {self._output_name}")
            print(f"[INFO] {model_type} loaded successfully with ONNX Runtime!")
            
        except Exception as e:
            print(f"[ERROR] Could not load {model_type} model: {e}")
            raise

    def extract_embedding(self, face_image: np.ndarray, target_size: tuple = (112, 112)) -> np.ndarray:
        """
        Extract embedding vector từ ảnh khuôn mặt
        
        Args:
            face_image: Ảnh khuôn mặt (BGR hoặc grayscale)
            target_size: Kích thước đầu vào của model (mặc định 112x112)
        
        Returns:
            Embedding vector
        """
        # Đảm bảo là ảnh màu (3 channels)
        if len(face_image.shape) == 2:  # Grayscale
            face_image = cv2.cvtColor(face_image, cv2.COLOR_GRAY2BGR)
        elif face_image.shape[2] == 4:  # BGRA
            face_image = cv2.cvtColor(face_image, cv2.COLOR_BGRA2BGR)
        
        # Resize về kích thước model (112x112)
        face_resized = cv2.resize(face_image, target_size)
        
        # Normalize cho MobileFaceNet/ResNet34: (x - 127.5) / 128.0
        face_normalized = (face_resized.astype('float32') - 127.5) / 128.0
        
        # Chuyển đổi BGR sang RGB
        face_rgb = cv2.cvtColor(face_normalized, cv2.COLOR_BGR2RGB)
        
        # Thêm batch dimension
        face_batch = np.expand_dims(face_rgb, axis=0).astype(np.float32)
        
        # Xử lý định dạng NCHW vs NHWC tùy thuộc vào model
        if self.model_type == "resnet34":
            # ResNet34 ONNX expects NCHW [1, 3, 112, 112]
            face_batch = np.transpose(face_batch, (0, 3, 1, 2))
        else:
            # MobileFaceNet expects NHWC [1, 112, 112, 3]
            pass
            
        # Chạy inference với ONNX Runtime
        embedding = self._session.run(
            [self._output_name],
            {self._input_name: face_batch}
        )[0][0]  # Lấy batch đầu tiên
        
        # Normalize embedding (L2 normalization)
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding

    @staticmethod
    def cosine_distance(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Tính cosine distance giữa 2 embedding (0-1, nhỏ = giống)"""
        # Các embedding đã được normalize trong extract_embedding
        # nên không cần normalize lại
        
        # Cosine similarity (1 = giống, -1 = khác)
        similarity = np.dot(emb1, emb2)
        
        # Clamp để tránh lỗi số học
        similarity = np.clip(similarity, -1.0, 1.0)
        
        # Convert to distance (0 = giống, 1 = khác)
        distance = 1.0 - similarity
        return max(0.0, min(1.0, distance))