"""
Cấu hình tập trung cho Hệ thống Giám sát & Cảnh báo Trạng thái Tài xế (GuardCabin DMS)
"""

import os

# Đường dẫn thư mục gốc dự án
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")
os.makedirs(WEIGHTS_DIR, exist_ok=True)

# Đường dẫn mô hình
TCN_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "tcn_dms.pth")
TCN_ONNX_PATH = os.path.join(WEIGHTS_DIR, "tcn_dms.onnx")

# Tự động ưu tiên tìm file fine-tuned YOLO (best.pt) trong weights/ hoặc thư mục gốc
CUSTOM_YOLO_CANDIDATES = [
    os.path.join(WEIGHTS_DIR, "best.pt"),
    os.path.join(BASE_DIR, "best.pt"),
    os.path.join(WEIGHTS_DIR, "yolo_dms.pt"),
    os.path.join(BASE_DIR, "yolo_dms.pt"),
    os.path.join(WEIGHTS_DIR, "best.onnx"),
    os.path.join(BASE_DIR, "best.onnx")
]

YOLO_MODEL_PATH = "yolo11n.pt"  # Mặc định
for candidate in CUSTOM_YOLO_CANDIDATES:
    if os.path.exists(candidate):
        YOLO_MODEL_PATH = candidate
        break

# Định nghĩa các trạng thái (Classification Classes)
CLASS_NAMES = [
    "Normal",        # 0: Lái xe an toàn / Bình thường
    "Drowsy",        # 1: Buồn ngủ / Mệt mỏi (Mắt nhắm kéo dài)
    "Yawn",          # 2: Ngáp liên tục
    "Distracted",    # 3: Mất tập trung (Quay đầu Yaw/Pitch quá ngưỡng)
    "Phone",         # 4: Sử dụng điện thoại di động
    "Smoking"        # 5: Hút thuốc / Uống nước
]

CLASS_VIETNAMESE = {
    "Normal": "Bình thường (An toàn)",
    "Drowsy": "Buồn ngủ / Nguy hiểm",
    "Yawn": "Ngáp / Cần nghỉ ngơi",
    "Distracted": "Mất tập trung",
    "Phone": "Sử dụng điện thoại",
    "Smoking": "Hút thuốc / Uống nước"
}

# Nhãn hiển thị HUD chuẩn không dấu để fallback không bao giờ bị lỗi font ????
CLASS_HUD_LABELS = {
    "Normal": "BINH THUONG (AN TOAN)",
    "Drowsy": "BUON NGU / NGUY HIEM",
    "Yawn": "NGAP / CAN NGHI NGOI",
    "Distracted": "MAT TAP TRUNG",
    "Phone": "SU DUNG DIEN THOAI",
    "Smoking": "HUT THUOC / UONG NUOC"
}

# Cấu hình Feature Vector
# V_t = [EAR_l, EAR_r, EAR_avg, MAR, Pitch, Yaw, Roll, Gaze_x, Gaze_y, Score_phone, Score_cig, Hand_dist]
FEATURE_DIM = 12
SEQUENCE_LENGTH = 30  # Số frame trong cửa sổ trượt (30 frames ~ 1.0 giây tại 30 FPS)

# Ngưỡng sinh lý & heuristic (Failsafe Thresholds)
EAR_DROWSY_THRESH = 0.20        # Dưới ngưỡng này coi như mắt nhắm
MAR_YAWN_THRESH = 0.52          # Trên ngưỡng này coi như miệng mở rộng (ngáp)
HEAD_YAW_THRESH = 45.0          # Độ lệch góc quay ngang (trái/phải) vượt quá ngưỡng này là mất tập trung
HEAD_PITCH_THRESH = 35.0        # Độ gật gù/ngửa đầu vượt quá ngưỡng này là mất tập trung (tăng từ 20 lên 35 để phù hợp góc webcam)
HEAD_ROLL_THRESH = 25.0         # Độ nghiêng đầu sang vai

# Số frame tích lũy để kích hoạt cảnh báo tức thời
CONSEC_DROWSY_FRAMES = 35       # ~1.2 giây nhắm mắt liên tục -> Báo động Level 2
CONSEC_YAWN_FRAMES = 25         # ~0.8 giây mở miệng -> Báo Level 1
CONSEC_DISTRACT_FRAMES = 65     # ~2.2 giây quay mặt hướng khác -> Báo Level 1 (tăng từ 40 lên 65 để tránh báo liên tục)
CONSEC_PHONE_FRAMES = 15        # ~0.5 giây phát hiện điện thoại gần mặt -> Báo Level 2

# Ngưỡng tin cậy của Object Detector (YOLO)
PHONE_CONF_THRESH = 0.40
CIGARETTE_CONF_THRESH = 0.35

# Cấu hình kiến trúc mạng TCN (Temporal Convolutional Network)
TCN_CONFIG = {
    "input_channels": FEATURE_DIM,
    "num_channels": [32, 64, 64, 128],
    "kernel_size": 3,
    "dropout": 0.2,
    "num_classes": len(CLASS_NAMES)
}

# Cấu hình Camera & Stream
CAMERA_ID = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# Cấu hình Cảnh báo Âm thanh
AUDIO_ALERT_ENABLED = True
ALERT_COOLDOWN_SEC = 2.0        # Thời gian tối thiểu giữa 2 lần phát còi cùng loại
LEVEL1_BEEP_FREQ = 1000         # Tần số Beep cảnh báo mức nhẹ (Hz)
LEVEL1_BEEP_DUR = 180           # Thời lượng (ms)
LEVEL2_BEEP_FREQ = 2200         # Tần số Còi báo động khẩn cấp (Hz)
LEVEL2_BEEP_DUR = 350           # Thời lượng (ms)

# Màu sắc giao diện Cyber HUD (BGR format for OpenCV)
COLOR_GREEN = (50, 220, 50)     # An toàn
COLOR_YELLOW = (30, 210, 255)   # Cảnh báo nhẹ
COLOR_RED = (40, 40, 255)       # Báo động khẩn cấp
COLOR_CYAN = (240, 210, 0)      # Điểm nhấn công nghệ
COLOR_DARK_BG = (20, 20, 25)    # Nền panel HUD
COLOR_WHITE = (245, 245, 245)
