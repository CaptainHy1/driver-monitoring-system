"""
Module suy luận (Inference Engine) cho TCN.
Hỗ trợ cả ONNX Runtime (tối ưu hóa tốc độ cao, độ trễ < 5ms) và PyTorch (.pth).
"""

import os
import sys
import time
import numpy as np
import torch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from .tcn import TCNModel
from config import CLASS_NAMES, TCN_CONFIG

class TCNClassifier:
    def __init__(self, onnx_path=None, pth_path=None, device="cpu"):
        self.onnx_path = onnx_path
        self.pth_path = pth_path
        self.device = torch.device(device if torch.cuda.is_available() and device != "cpu" else "cpu")
        self.backend = None
        self.session = None
        self.model = None

        self._load_model()

    def _load_model(self):
        """Tự động ưu tiên tải mô hình ONNX nếu tồn tại, sau đó đến PyTorch"""
        # 1. Thử tải ONNX Runtime
        if self.onnx_path and os.path.exists(self.onnx_path):
            try:
                import onnxruntime as ort
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                self.session = ort.InferenceSession(self.onnx_path, providers=providers)
                self.backend = "onnx"
                self.input_name = self.session.get_inputs()[0].name
                print(f"[TCN] Nạp thành công mô hình ONNX: {self.onnx_path}")
                return
            except Exception as e:
                print(f"[TCN] Không thể nạp ONNX ({e}), chuyển sang PyTorch...")

        # 2. Thử tải PyTorch .pth
        self.model = TCNModel(
            input_size=TCN_CONFIG["input_channels"],
            num_classes=TCN_CONFIG["num_classes"],
            num_channels=TCN_CONFIG["num_channels"],
            kernel_size=TCN_CONFIG["kernel_size"],
            dropout=0.0  # Tắt dropout khi suy luận
        ).to(self.device)

        if self.pth_path and os.path.exists(self.pth_path):
            try:
                state_dict = torch.load(self.pth_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.model.eval()
                self.backend = "pytorch"
                print(f"[TCN] Nạp thành công trọng số PyTorch: {self.pth_path}")
                return
            except Exception as e:
                print(f"[TCN] Cảnh báo lỗi nạp file .pth ({e})")

        # 3. Sử dụng mô hình PyTorch chưa nạp trọng số (chế độ demo / khởi tạo ban đầu)
        self.model.eval()
        self.backend = "pytorch_uninitialized"
        print("[TCN] Đang chạy với kiến trúc TCN PyTorch mặc định.")

    def predict(self, sequence_array):
        """
        Dự đoán trạng thái từ chuỗi Feature Vectors.
        Input: numpy array shape (Sequence_Length, Feature_Dim) e.g. (30, 12)
        Output: dict kết quả gồm class_id, class_name, confidence, probabilities, latency_ms
        """
        start_time = time.perf_counter()

        # Chuẩn hóa shape: (L, C) -> (1, C, L) cho mạng Conv1D
        # sequence_array: shape (30, 12) -> transpose -> (12, 30) -> expand dim -> (1, 12, 30)
        x_input = np.transpose(sequence_array).astype(np.float32)
        x_input = np.expand_dims(x_input, axis=0)  # Shape (1, 12, 30)

        probs = np.zeros(len(CLASS_NAMES), dtype=np.float32)

        try:
            if self.backend == "onnx" and self.session is not None:
                ort_inputs = {self.input_name: x_input}
                ort_outs = self.session.run(None, ort_inputs)
                logits = ort_outs[0][0]  # Shape (6,)
                # Softmax
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / np.sum(exp_logits)
            else:
                with torch.no_grad():
                    tensor_in = torch.from_numpy(x_input).to(self.device)
                    logits = self.model(tensor_in)
                    probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

            pred_class_id = int(np.argmax(probs))
            confidence = float(probs[pred_class_id])
        except Exception as e:
            pred_class_id = 0
            confidence = 1.0
            probs[0] = 1.0

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "class_id": pred_class_id,
            "class_name": CLASS_NAMES[pred_class_id],
            "confidence": confidence,
            "probabilities": probs.tolist(),
            "latency_ms": elapsed_ms
        }
