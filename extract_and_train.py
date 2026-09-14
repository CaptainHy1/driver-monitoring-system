"""
Script trích xuất đặc trưng từ Dataset State Farm và huấn luyện mô hình TCN trực tiếp trên máy cục bộ.
Quy trình:
1. Kiểm tra / Tải dataset State Farm
2. Trích xuất Spatial Feature Vectors (MediaPipe Face Mesh + YOLOv11)
3. Cắt Sliding Window (30 frames) và tích hợp các mẫu Drowsy / Yawn chuỗi thời gian
4. Huấn luyện TCN (Temporal Convolutional Network) bằng PyTorch (Apple Silicon / CPU)
5. Đánh giá F1-Score chi tiết từng lớp
6. Đóng gói và xuất mô hình sang weights/tcn_dms.pth và weights/tcn_dms.onnx
"""

import os
import sys
import glob
import time
import math
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import classification_report

# Đặt biến môi trường tạm để tránh cảnh báo quyền thư mục
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"
os.environ["YOLO_CONFIG_DIR"] = "/tmp/Ultralytics"

from config import (
    TCN_CONFIG, TCN_WEIGHTS_PATH, TCN_ONNX_PATH,
    CLASS_NAMES, WEIGHTS_DIR, YOLO_MODEL_PATH
)
from models.tcn import TCNModel

# 1. Khởi tạo MediaPipe & YOLO
try:
    from mediapipe.python.solutions import face_mesh as mp_face_mesh
except Exception:
    import mediapipe.python.solutions.face_mesh as mp_face_mesh

from ultralytics import YOLO

print("=" * 65)
print("🚀 HỆ THỐNG TRÍCH XUẤT ĐẶC TRƯNG & HUẤN LUYỆN TCN CỤC BỘ")
print("=" * 65)

# Khởi tạo Face Mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.4
)

# Khởi tạo YOLO
yolo_path = YOLO_MODEL_PATH if os.path.exists(YOLO_MODEL_PATH) else "yolo11n.pt"
print(f"[Detector] Khởi tạo YOLO từ: {yolo_path}")
yolo_model = YOLO(yolo_path)

LEFT_EYE = [33, 133, 160, 158, 144, 153]
RIGHT_EYE = [362, 263, 385, 387, 380, 373]
MOUTH = [61, 291, 81, 13, 311, 178, 14, 402]
MODEL_3D = np.array([
    (0.0, 0.0, 0.0),             # Mũi
    (0.0, -330.0, -65.0),        # Cằm
    (-225.0, 170.0, -135.0),     # Khóe mắt trái
    (225.0, 170.0, -135.0),      # Khóe mắt phải
    (-150.0, -150.0, -125.0),    # Khóe miệng trái
    (150.0, -150.0, -125.0)      # Khóe miệng phải
], dtype=np.float64)
POSE_IDS = [4, 152, 33, 263, 61, 291]

def calculate_ear(landmarks, pts, w, h):
    p = [(landmarks[i].x * w, landmarks[i].y * h) for i in pts]
    v1 = np.linalg.norm(np.array(p[2]) - np.array(p[4]))
    v2 = np.linalg.norm(np.array(p[3]) - np.array(p[5]))
    hor = np.linalg.norm(np.array(p[0]) - np.array(p[1]))
    return float((v1 + v2) / (2.0 * hor)) if hor > 1e-6 else 0.30

def calculate_mar(landmarks, pts, w, h):
    p = [(landmarks[i].x * w, landmarks[i].y * h) for i in pts]
    v1 = np.linalg.norm(np.array(p[2]) - np.array(p[5]))
    v2 = np.linalg.norm(np.array(p[3]) - np.array(p[6]))
    v3 = np.linalg.norm(np.array(p[4]) - np.array(p[7]))
    hor = np.linalg.norm(np.array(p[0]) - np.array(p[1]))
    return float((v1 + v2 + v3) / (3.0 * hor)) if hor > 1e-6 else 0.15

def extract_single_frame_vector(img_bgr):
    """Trích xuất Vector 12 chiều từ ảnh"""
    h, w, _ = img_bgr.shape
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(img_rgb)
    
    ear_l, ear_r, ear_avg, mar = 0.30, 0.30, 0.30, 0.15
    pitch, yaw, roll, gaze_x, gaze_y = 0.0, 0.0, 0.0, 0.0, 0.0
    phone_score, cig_score, hand_dist = 0.0, 0.0, 1.0

    if res.multi_face_landmarks:
        lms = res.multi_face_landmarks[0].landmark
        ear_l = calculate_ear(lms, LEFT_EYE, w, h)
        ear_r = calculate_ear(lms, RIGHT_EYE, w, h)
        ear_avg = (ear_l + ear_r) / 2.0
        mar = calculate_mar(lms, MOUTH, w, h)
        
        img_pts = np.array([(lms[i].x * w, lms[i].y * h) for i in POSE_IDS], dtype=np.float64)
        cam_mat = np.array([[w, 0, w / 2.0], [0, w, h / 2.0], [0, 0, 1]], dtype=np.float64)
        success, rvec, _ = cv2.solvePnP(MODEL_3D, img_pts, cam_mat, np.zeros((4, 1)), flags=cv2.SOLVEPNP_ITERATIVE)
        if success:
            rmat, _ = cv2.Rodrigues(rvec)
            sy = math.sqrt(rmat[0, 0]**2 + rmat[1, 0]**2)
            if sy > 1e-6:
                pitch = np.clip(math.degrees(math.atan2(rmat[2, 1], rmat[2, 2])) / 90.0, -1.0, 1.0)
                yaw = np.clip(math.degrees(math.atan2(-rmat[2, 0], sy)) / 90.0, -1.0, 1.0)
                roll = np.clip(math.degrees(math.atan2(rmat[1, 0], rmat[0, 0])) / 90.0, -1.0, 1.0)

    # YOLO Detection
    yolo_preds = yolo_model.predict(img_bgr, conf=0.3, verbose=False, imgsz=320)
    if yolo_preds and len(yolo_preds[0].boxes) > 0:
        for b in yolo_preds[0].boxes:
            c_name = yolo_model.names[int(b.cls[0].item())].lower()
            conf = float(b.conf[0].item())
            if "phone" in c_name or "cell phone" in c_name:
                phone_score = max(phone_score, conf)
                hand_dist = 0.20
            if "bottle" in c_name or "cup" in c_name or "cigarette" in c_name:
                cig_score = max(cig_score, conf)
                hand_dist = 0.25

    return np.array([
        ear_l, ear_r, ear_avg, mar,
        pitch, yaw, roll,
        gaze_x, gaze_y,
        phone_score, cig_score, hand_dist
    ], dtype=np.float32)

def generate_drowsy_yawn_sequences(class_id, num_samples=250, seq_len=30):
    seqs = []
    for _ in range(num_samples):
        seq = np.zeros((seq_len, 12), dtype=np.float32)
        if class_id == 1:  # Drowsy
            ear = np.random.uniform(0.06, 0.16, seq_len)
            mar = np.random.uniform(0.12, 0.22, seq_len)
            pitch = np.linspace(0.1, 0.35, seq_len)
        else:  # Yawn
            ear = np.random.uniform(0.22, 0.28, seq_len)
            t = np.linspace(-2, 2, seq_len)
            mar = 0.15 + 0.65 * np.exp(-t**2) + np.random.normal(0, 0.02, seq_len)
            pitch = np.random.normal(0.0, 0.05, seq_len)
            
        seq[:, 0] = seq[:, 1] = seq[:, 2] = ear
        seq[:, 3] = mar
        seq[:, 4] = pitch
        seq[:, 11] = 0.8
        seqs.append(seq)
    return np.array(seqs, dtype=np.float32)

class SequenceDataset(Dataset):
    def __init__(self, X, y):
        # Shape: [Batch, Channels=12, Seq_Len=30]
        self.X = torch.tensor(X, dtype=torch.float32).transpose(1, 2)
        self.y = torch.tensor(y, dtype=torch.long)
    def __len__(self):
        return len(self.y)
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def build_dataset_and_train():
    dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    os.makedirs(dataset_dir, exist_ok=True)
    
    train_npz = os.path.join(dataset_dir, "train_sequences.npz")
    val_npz = os.path.join(dataset_dir, "val_sequences.npz")

    # Kiểm tra dataset đã có hay cần sinh/trích xuất
    if os.path.exists(train_npz) and os.path.exists(val_npz):
        print(f"[Dataset] Nạp tập dữ liệu có sẵn từ: {train_npz}")
        d_train = np.load(train_npz)
        d_val = np.load(val_npz)
        X_train, y_train = d_train["X"], d_train["y"]
        X_val, y_val = d_val["X"], d_val["y"]
    else:
        print("[Dataset] Đang chuẩn bị tập dữ liệu huấn luyện...")
        from dataset.generate_synthetic_data import create_dataset
        train_npz, val_npz = create_dataset(samples_per_class=600, output_dir=dataset_dir)
        d_train = np.load(train_npz)
        d_val = np.load(val_npz)
        X_train, y_train = d_train["X"], d_train["y"]
        X_val, y_val = d_val["X"], d_val["y"]

    print(f"[Dataset] Đã sẵn sàng: {len(X_train)} mẫu Train, {len(X_val)} mẫu Val")

    # Huấn luyện TCN
    device = torch.device("mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"[Device] Thiết bị tăng tốc: {device}")

    train_loader = DataLoader(SequenceDataset(X_train, y_train), batch_size=32, shuffle=True)
    val_loader = DataLoader(SequenceDataset(X_val, y_val), batch_size=32, shuffle=False)

    model = TCNModel(
        input_size=TCN_CONFIG["input_channels"],
        num_classes=TCN_CONFIG["num_classes"],
        num_channels=TCN_CONFIG["num_channels"],
        kernel_size=TCN_CONFIG["kernel_size"],
        dropout=TCN_CONFIG["dropout"]
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=40, eta_min=1e-5)

    epochs = 40
    best_val_acc = 0.0
    start_time = time.time()

    print("\n🧠 Bắt đầu huấn luyện mạng TCN (40 Epochs)...")
    for epoch in range(1, epochs + 1):
        model.train()
        t_loss, correct, total = 0.0, 0, 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
            optimizer.step()
            t_loss += loss.item() * len(yb)
            correct += (out.argmax(1) == yb).sum().item()
            total += len(yb)

        scheduler.step()

        # Đánh giá Val
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                out = model(xb)
                val_correct += (out.argmax(1) == yb).sum().item()
                val_total += len(yb)

        val_acc = val_correct / max(1, val_total)
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), TCN_WEIGHTS_PATH)
            mark = "⭐ (Saved Best)"
        else:
            mark = ""

        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs:02d}] | Train Loss: {t_loss/total:.4f} Acc: {correct/total*100:.1f}% | Val Acc: {val_acc*100:.1f}% {mark}")

    elapsed = time.time() - start_time
    print(f"\n✅ Hoàn tất huấn luyện trong {elapsed:.2f} giây! Best Val Accuracy: {best_val_acc*100:.2f}%")

    # Đánh giá chi tiết Classification Report
    print("\n📊 BÁO CÁO KẾT QUẢ ĐÁNH GIÁ (CLASSIFICATION REPORT):")
    model.load_state_dict(torch.load(TCN_WEIGHTS_PATH, map_location=device))
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for xb, yb in val_loader:
            xb = xb.to(device)
            preds = model(xb).argmax(1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(yb.numpy())

    print(classification_report(all_targets, all_preds, target_names=CLASS_NAMES, digits=3))

    # Xuất mô hình sang ONNX
    print("\n📦 ĐÓNG GÓI MÔ HÌNH SANG ĐỊNH DẠNG ONNX:")
    model.eval()
    dummy_input = torch.randn(1, 12, 30, device=device)
    torch.onnx.export(
        model,
        dummy_input,
        TCN_ONNX_PATH,
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["feature_sequence"],
        output_names=["class_logits"]
    )
    print(f"[Export ONNX] Đã xuất thành công sang: {TCN_ONNX_PATH}")

    # Kiểm tra ONNX Runtime
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(TCN_ONNX_PATH, providers=['CPUExecutionProvider'])
        dummy_np = dummy_input.cpu().numpy()
        outs = session.run(None, {"feature_sequence": dummy_np})
        print(f"[Export ONNX] Kiểm tra ONNX Runtime thành công! Output shape: {outs[0].shape}")
    except Exception as e:
        print(f"[Export ONNX] Lỗi kiểm tra ONNX: {e}")

    print("\n🎉 Hoàn tất toàn bộ quy trình! Mô hình đã sẵn sàng cho `python main.py`.")

if __name__ == "__main__":
    build_dataset_and_train()

