"""
Module phát hiện vật thể can thiệp (Điện thoại, Thuốc lá, Bình nước) bằng YOLOv11.
Hỗ trợ cả chế độ ONNX Runtime và Ultralytics PyTorch với cơ chế Fallback an toàn.
"""

import os
import sys
import cv2
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

class YOLODetector:
    def __init__(self, model_path="yolo11n.pt", conf_thresh=0.35):
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.backend = None
        self.model = None
        self.classes_map = {}
        self._initialize_model()

    def _initialize_model(self):
        """Khởi tạo mô hình dựa trên định dạng và thư viện có sẵn"""
        # Thử nạp ONNX Runtime nếu là file .onnx
        if self.model_path.endswith(".onnx") and os.path.exists(self.model_path):
            try:
                import onnxruntime as ort
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                self.model = ort.InferenceSession(self.model_path, providers=providers)
                self.backend = "onnx"
                print(f"[YOLO] Khởi tạo thành công mô hình ONNX: {self.model_path}")
                return
            except Exception as e:
                print(f"[YOLO] Không thể tải ONNX ({e}), thử sang Ultralytics...")

        # Nạp qua Ultralytics YOLO
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self.backend = "ultralytics"
            print(f"[YOLO] Khởi tạo thành công Ultralytics YOLO: {self.model_path}")
        except Exception as e:
            print(f"[YOLO] Cảnh báo: Không thể tải mô hình YOLO ({e}). Chuyển sang chế độ Safe Fallback.")
            self.backend = "fallback"

    def detect(self, frame_bgr, face_bbox=None):
        """
        Thực hiện inference phát hiện vật thể.
        Trả về dictionary kết quả:
        - phone_score: float (0.0 - 1.0)
        - cig_score: float (0.0 - 1.0)
        - phone_box: [x, y, w, h] hoặc None
        - cig_box: [x, y, w, h] hoặc None
        - hand_face_dist: float (khoảng cách tương đối chuẩn hóa tới mặt)
        - raw_detections: danh sách các bbox phát hiện được để vẽ lên HUD
        """
        results = {
            "phone_score": 0.0,
            "cig_score": 0.0,
            "phone_box": None,
            "cig_box": None,
            "hand_face_dist": 1.0,
            "raw_detections": []
        }

        if self.backend == "fallback" or self.model is None:
            return results

        try:
            if self.backend == "ultralytics":
                # Chạy inference Ultralytics
                preds = self.model.predict(
                    frame_bgr,
                    conf=self.conf_thresh,
                    verbose=False,
                    imgsz=640
                )

                if not preds or len(preds) == 0:
                    return results

                boxes = preds[0].boxes
                if boxes is None:
                    return results

                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    cls_name = self.model.names.get(cls_id, "").lower()
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                    w_box = x2 - x1
                    h_box = y2 - y1

                    results["raw_detections"].append({
                        "class": cls_name,
                        "conf": conf,
                        "box": (x1, y1, w_box, h_box)
                    })

                    # Nhận diện điện thoại (cell phone)
                    if "cell phone" in cls_name or "phone" in cls_name:
                        if conf > results["phone_score"]:
                            results["phone_score"] = conf
                            results["phone_box"] = (x1, y1, w_box, h_box)

                    # Nhận diện thuốc lá / chai nước (cigarette / bottle / cup)
                    if "cigarette" in cls_name or "smoke" in cls_name or "bottle" in cls_name or "cup" in cls_name:
                        if conf > results["cig_score"]:
                            results["cig_score"] = conf
                            results["cig_box"] = (x1, y1, w_box, h_box)

            # Tính khoảng cách từ vật thể tới tâm khuôn mặt nếu có face_bbox
            if face_bbox is not None and results["phone_box"] is not None:
                fx, fy, fw, fh = face_bbox
                px, py, pw, ph = results["phone_box"]
                face_center = np.array([fx + fw / 2.0, fy + fh / 2.0])
                phone_center = np.array([px + pw / 2.0, py + ph / 2.0])
                dist = np.linalg.norm(face_center - phone_center)
                # Chuẩn hóa khoảng cách theo đường kính khuôn mặt
                face_size = max(fw, fh, 1.0)
                results["hand_face_dist"] = float(np.clip(dist / face_size, 0.0, 3.0))

        except Exception as e:
            pass

        return results
