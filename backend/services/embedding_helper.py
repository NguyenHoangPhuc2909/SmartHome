import os
import numpy as np
import cv2
import onnxruntime as ort
from config import Config


class EmbeddingModel:
    _instance = None
    _session = None
    _input_name = None
    _output_name = None

    @staticmethod
    def get_instance():
        """Singleton pattern — load model chỉ 1 lần"""
        if EmbeddingModel._instance is None:
            EmbeddingModel._instance = EmbeddingModel()
        return EmbeddingModel._instance

    def __init__(self):
        """Load model ONNX (MobileFaceNet)"""
        # Kiểm tra cả file .onnx (ưu tiên) và .h5 (fallback)
        onnx_path = Config.FACE_MODEL_PATH.replace('.h5', '.onnx')
        h5_path = Config.FACE_MODEL_PATH
        
        if os.path.exists(onnx_path):
            model_path = onnx_path
            print(f"[INFO] Tìm thấy model ONNX: {model_path}")
        elif os.path.exists(h5_path):
            model_path = h5_path
            print(f"[INFO] Tìm thấy model H5: {model_path}")
            # Nếu chỉ có H5, bạn cần chuyển đổi hoặc báo lỗi
            raise FileNotFoundError(
                f"Chỉ tìm thấy file H5: {h5_path}\n"
                f"Vui lòng chuyển đổi sang ONNX trước khi sử dụng onnxruntime.\n"
                f"Cách chuyển đổi: python -m tf2onnx.convert --keras {h5_path} --output {onnx_path}"
            )
        else:
            raise FileNotFoundError(
                f"Không tìm thấy model ONNX hoặc H5:\n"
                f"  - ONNX: {onnx_path}\n"
                f"  - H5: {h5_path}"
            )
        
        try:
            print(f"[INFO] Đang load model: {model_path}")
            
            # Tạo ONNX Runtime session
            EmbeddingModel._session = ort.InferenceSession(
                model_path,
                providers=['CPUExecutionProvider']  # Có thể thay bằng ['CUDAExecutionProvider'] nếu có GPU
            )
            
            # Lấy input và output names
            EmbeddingModel._input_name = EmbeddingModel._session.get_inputs()[0].name
            EmbeddingModel._output_name = EmbeddingModel._session.get_outputs()[0].name
            
            # In thông tin model
            input_shape = EmbeddingModel._session.get_inputs()[0].shape
            print(f"[INFO] Model input: {EmbeddingModel._input_name}, shape: {input_shape}")
            print(f"[INFO] Model output: {EmbeddingModel._output_name}")
            print("[INFO] Model loaded thành công với ONNX Runtime!")
            
        except Exception as e:
            print(f"[ERROR] Không thể load model: {e}")
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
        
        # Resize về kích thước model
        face_resized = cv2.resize(face_image, target_size)
        
        # Normalize cho MobileFaceNet (quan trọng!): (x - 127.5) / 128.0
        face_normalized = (face_resized.astype('float32') - 127.5) / 128.0
        
        # Chuyển đổi BGR sang RGB (nếu model yêu cầu)
        # Một số model ONNX chuyển từ Keras cần input RGB
        # Nếu model của bạn dùng BGR, hãy comment dòng này
        face_rgb = cv2.cvtColor(face_normalized, cv2.COLOR_BGR2RGB)
        
        # Thêm batch dimension và chuyển sang NCHW nếu cần
        # MobileFaceNet thường dùng NHWC (batch, height, width, channels)
        face_batch = np.expand_dims(face_rgb, axis=0).astype(np.float32)
        
        # Chạy inference với ONNX Runtime
        embedding = EmbeddingModel._session.run(
            [EmbeddingModel._output_name],
            {EmbeddingModel._input_name: face_batch}
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