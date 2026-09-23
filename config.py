import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import torch

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------------------------------------------------------
# Model Checkpoint & Pre-trained Weights Paths (3 NHÁNH CHÍNH)
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")
os.makedirs(WEIGHTS_DIR, exist_ok=True)

# 👤 [NHÁNH 1 - FACE]: Khuôn mặt, hướng nhìn Gaze, PERCLOS nhắm mắt, ngáp
FACE_STREAM_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "face_vit.pth")
FACE_VIT_WEIGHTS_PATH = FACE_STREAM_WEIGHTS_PATH

# 🧍 [NHÁNH 2 - BODY]: Khung xương 17 khớp & phân tích cử động ST-GCN
BODY_POSE_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "yolov8n-pose.pt")
YOLO_POSE_WEIGHTS_PATH = BODY_POSE_WEIGHTS_PATH
ST_GCN_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "st_gcn.pth")

# ✋ [NHÁNH 3 - HAND]: Ước lượng vị trí bàn tay & vật thể tương tác (Điện thoại, Chai nước, Đồ ăn)
COCKPIT_CUSTOM_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "yolo_cockpit.pt")
HAND_STREAM_WEIGHTS_PATH = COCKPIT_CUSTOM_WEIGHTS_PATH if os.path.exists(COCKPIT_CUSTOM_WEIGHTS_PATH) else os.path.join(WEIGHTS_DIR, "yolov8n.pt")
YOLO_HAND_WEIGHTS_PATH = HAND_STREAM_WEIGHTS_PATH
YOLO_OBJECT_WEIGHTS_PATH = HAND_STREAM_WEIGHTS_PATH

# 🔗 [HẬU KỲ]: Dung hợp đa mô thức & Phân tích chuỗi thời gian (Tùy chọn)
FUSION_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "multimodal_fusion.pth")
TEMPORAL_TRANSFORMER_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "temporal_transformer.pth")

# ---------------------------------------------------------
# Distraction Classes Definition (5 Lớp Hành vi Chính)
# ---------------------------------------------------------
DISTRACTION_CLASSES: Dict[str, str] = {
    "C0": "Safe Driving",
    "C1": "Phone Usage - Call / Text",
    "C2": "Drowsiness / Yawning",
    "C3": "Reaching Behind / Side",
    "C4": "Eating / Drinking",
}

CLASS_TO_IDX: Dict[str, int] = {k: idx for idx, k in enumerate(DISTRACTION_CLASSES.keys())}
IDX_TO_CLASS: Dict[int, str] = {idx: k for k, idx in CLASS_TO_IDX.items()}
NUM_CLASSES: int = len(DISTRACTION_CLASSES)

# ---------------------------------------------------------
# Alert Severity Levels
# ---------------------------------------------------------
class AlertLevel:
    LEVEL_0 = 0  # Normal / Safe (No action)
    LEVEL_1 = 1  # Notice / Mild Warning (Yellow visual banner)
    LEVEL_2 = 2  # Danger / Immediate Reminder (Orange banner + Audio beep)
    LEVEL_3 = 3  # Critical Emergency (Red flashing banner + Continuous buzzer)

# ---------------------------------------------------------
# Time Thresholds (in seconds) for violation triggering
# ---------------------------------------------------------
GAZE_AWAY_TIME_THRESHOLD: float = 2.0     # Eyes off road > 2.0s triggers warning
EYE_CLOSURE_TIME_THRESHOLD: float = 1.5   # Eyes closed > 1.5s triggers drowsiness alarm
PHONE_USAGE_TIME_THRESHOLD: float = 1.5   # Phone near ear/hands > 1.5s triggers warning
REACHING_TIME_THRESHOLD: float = 1.8      # Awkward leaning/reaching > 1.8s
EATING_TIME_THRESHOLD: float = 3.0        # Eating/drinking > 3.0s

# ---------------------------------------------------------
# Physiological Face Analysis Thresholds
# ---------------------------------------------------------
EAR_THRESHOLD: float = 0.20               # Eye Aspect Ratio below this means closed eye
MAR_THRESHOLD: float = 0.65               # Mouth Aspect Ratio above this means yawn
PERCLOS_WINDOW_SECONDS: float = 60.0      # Evaluation window for PERCLOS (seconds)
PERCLOS_DROWSY_THRESHOLD: float = 0.40    # If eyes closed for > 40% of window -> drowsy

# ---------------------------------------------------------
# Tensor Input Resolutions & Feature Dimensions
# ---------------------------------------------------------
FACE_INPUT_SIZE: Tuple[int, int] = (224, 224)
POSE_INPUT_SIZE: Tuple[int, int] = (256, 256)
COCKPIT_INPUT_SIZE: Tuple[int, int] = (640, 640)

FACE_FEAT_DIM: int = 256
POSE_FEAT_DIM: int = 256
HAND_FEAT_DIM: int = 256
FUSED_FEAT_DIM: int = 256

TEMPORAL_WINDOW_SIZE: int = 30           # Number of frames in sliding window (~1.0s at 30 FPS)
DEFAULT_FPS: float = 30.0

# ---------------------------------------------------------
# YOLO Object Detection Classes & Proximity Settings
# ---------------------------------------------------------
OBJECT_CLASSES_OF_INTEREST: List[str] = [
    "cell phone",
    "bottle",
    "cup",
    "sandwich",
    "banana",
    "apple",
    "hand",
]
