"""
Module sinh tập dữ liệu chuỗi Vector sinh trắc học chuẩn hóa (Synthetic Sequence Generator).
Mô phỏng chính xác các biến động sinh lý thời gian thực theo 6 trạng thái:
0: Normal, 1: Drowsy, 2: Yawn, 3: Distracted, 4: Phone, 5: Smoking.
Dữ liệu đầu ra: Mảng 3D (Số mẫu, Độ dài chuỗi=30, Số đặc trưng=12).
"""

import os
import numpy as np

def generate_sequence(class_id, seq_len=30, feat_dim=12):
    """
    Sinh 1 chuỗi 30 frames cho 1 trạng thái cụ thể.
    Vector V_t = [EAR_l, EAR_r, EAR_avg, MAR, Pitch, Yaw, Roll, Gaze_x, Gaze_y, Score_phone, Score_cig, Hand_dist]
    """
    seq = np.zeros((seq_len, feat_dim), dtype=np.float32)

    # 1. Trạng thái 0: Lái xe bình thường (Normal)
    if class_id == 0:
        base_ear = np.random.uniform(0.28, 0.35)
        ear_wave = base_ear + np.random.normal(0, 0.015, seq_len)
        # Chớp mắt tự nhiên ngẫu nhiên kéo dài 2-4 frame
        if np.random.rand() > 0.5:
            blink_start = np.random.randint(5, seq_len - 5)
            blink_len = np.random.randint(2, 4)
            ear_wave[blink_start:blink_start + blink_len] = np.random.uniform(0.08, 0.15)

        mar = np.random.uniform(0.10, 0.20) + np.random.normal(0, 0.02, seq_len)
        pitch = np.random.normal(0.0, 0.05, seq_len)
        yaw = np.random.normal(0.0, 0.06, seq_len)
        roll = np.random.normal(0.0, 0.04, seq_len)
        gaze_x = np.random.normal(0.0, 0.08, seq_len)
        gaze_y = np.random.normal(0.0, 0.08, seq_len)
        score_phone = np.random.uniform(0.0, 0.08, seq_len)
        score_cig = np.random.uniform(0.0, 0.08, seq_len)
        hand_dist = np.random.uniform(0.6, 0.9, seq_len)

    # 2. Trạng thái 1: Buồn ngủ / Mệt mỏi (Drowsy - Mắt nhắm kéo dài)
    elif class_id == 1:
        # Mắt sụp mí dần hoặc nhắm hẳn suốt hơn nửa chuỗi
        drowsy_type = np.random.choice(["closed", "drooping"])
        if drowsy_type == "closed":
            ear_wave = np.random.uniform(0.06, 0.16, seq_len)  # Nhắm mắt < 0.20
        else:
            # Sụp mí dần từ 0.25 xuống 0.12
            ear_wave = np.linspace(0.25, 0.11, seq_len) + np.random.normal(0, 0.01, seq_len)

        mar = np.random.uniform(0.12, 0.22, seq_len)
        # Gật gù đầu (Pitch cúi xuống)
        pitch = np.linspace(0.05, 0.35, seq_len) + np.random.normal(0, 0.03, seq_len)
        yaw = np.random.normal(0.0, 0.08, seq_len)
        roll = np.random.normal(0.0, 0.08, seq_len)
        gaze_x = np.random.normal(0.0, 0.05, seq_len)
        gaze_y = np.random.normal(-0.2, 0.1, seq_len)  # Mắt nhìn sụp xuống
        score_phone = np.random.uniform(0.0, 0.05, seq_len)
        score_cig = np.random.uniform(0.0, 0.05, seq_len)
        hand_dist = np.random.uniform(0.5, 0.8, seq_len)

    # 3. Trạng thái 2: Ngáp (Yawn - Miệng mở to dạng chu kỳ hình chuông)
    elif class_id == 2:
        ear_wave = np.random.uniform(0.22, 0.28, seq_len)  # Mắt hơi híp lại khi ngáp
        # Tạo đỉnh ngáp hình Parabol / Gaussian
        t = np.linspace(-2, 2, seq_len)
        mar_peak = np.random.uniform(0.58, 0.82)
        mar = 0.15 + (mar_peak - 0.15) * np.exp(-t**2) + np.random.normal(0, 0.02, seq_len)

        pitch = np.random.normal(0.0, 0.08, seq_len)
        yaw = np.random.normal(0.0, 0.08, seq_len)
        roll = np.random.normal(0.0, 0.05, seq_len)
        gaze_x = np.random.normal(0.0, 0.1, seq_len)
        gaze_y = np.random.normal(0.0, 0.1, seq_len)
        score_phone = np.random.uniform(0.0, 0.05, seq_len)
        score_cig = np.random.uniform(0.0, 0.05, seq_len)
        hand_dist = np.random.uniform(0.4, 0.7, seq_len)

    # 4. Trạng thái 3: Mất tập trung (Distracted - Quay đầu sang trái/phải)
    elif class_id == 3:
        ear_wave = np.random.uniform(0.26, 0.32, seq_len)
        mar = np.random.uniform(0.12, 0.20, seq_len)

        # Hướng quay: Trái hoặc Phải (|Yaw| > 25 độ -> |Yaw/90| > 0.28)
        direction = np.random.choice([-1.0, 1.0])
        yaw_val = direction * np.random.uniform(0.35, 0.65)
        yaw = yaw_val + np.random.normal(0, 0.04, seq_len)
        pitch = np.random.normal(0.05, 0.08, seq_len)
        roll = np.random.normal(0.0, 0.05, seq_len)
        gaze_x = direction * np.random.uniform(0.4, 0.9, seq_len)
        gaze_y = np.random.normal(0.0, 0.1, seq_len)
        score_phone = np.random.uniform(0.0, 0.06, seq_len)
        score_cig = np.random.uniform(0.0, 0.06, seq_len)
        hand_dist = np.random.uniform(0.5, 0.9, seq_len)

    # 5. Trạng thái 4: Sử dụng điện thoại (Phone)
    elif class_id == 4:
        ear_wave = np.random.uniform(0.24, 0.30, seq_len)
        mar = np.random.uniform(0.12, 0.20, seq_len)
        # Đầu thường cúi nhẹ nhìn điện thoại
        pitch = np.random.uniform(0.15, 0.35, seq_len)
        yaw = np.random.uniform(-0.25, 0.25, seq_len)
        roll = np.random.normal(0.0, 0.08, seq_len)
        gaze_y = np.random.uniform(-0.3, -0.7, seq_len)  # Mắt nhìn xuống
        gaze_x = np.random.normal(0.0, 0.15, seq_len)
        # Điểm tin cậy phát hiện điện thoại cao
        score_phone = np.random.uniform(0.65, 0.96, seq_len)
        score_cig = np.random.uniform(0.0, 0.05, seq_len)
        hand_dist = np.random.uniform(0.08, 0.30, seq_len)  # Tay gần sát mặt

    # 6. Trạng thái 5: Hút thuốc / Uống nước (Smoking / Drinking)
    else:
        ear_wave = np.random.uniform(0.25, 0.32, seq_len)
        # Miệng hơi biến động khi ngậm thuốc / uống nước
        mar = np.random.uniform(0.15, 0.35, seq_len)
        pitch = np.random.normal(0.0, 0.08, seq_len)
        yaw = np.random.normal(0.0, 0.08, seq_len)
        roll = np.random.normal(0.0, 0.05, seq_len)
        gaze_x = np.random.normal(0.0, 0.1, seq_len)
        gaze_y = np.random.normal(0.0, 0.1, seq_len)
        score_phone = np.random.uniform(0.0, 0.05, seq_len)
        # Điểm tin cậy thuốc lá / bình nước cao
        score_cig = np.random.uniform(0.55, 0.92, seq_len)
        hand_dist = np.random.uniform(0.10, 0.35, seq_len)  # Tay đưa lên gần miệng

    # Đóng gói vector 12 chiều
    seq[:, 0] = np.clip(ear_wave, 0.0, 0.6)  # EAR left
    seq[:, 1] = np.clip(ear_wave, 0.0, 0.6)  # EAR right
    seq[:, 2] = np.clip(ear_wave, 0.0, 0.6)  # EAR avg
    seq[:, 3] = np.clip(mar, 0.0, 1.2)       # MAR
    seq[:, 4] = np.clip(pitch, -1.0, 1.0)
    seq[:, 5] = np.clip(yaw, -1.0, 1.0)
    seq[:, 6] = np.clip(roll, -1.0, 1.0)
    seq[:, 7] = np.clip(gaze_x, -1.0, 1.0)
    seq[:, 8] = np.clip(gaze_y, -1.0, 1.0)
    seq[:, 9] = np.clip(score_phone, 0.0, 1.0)
    seq[:, 10] = np.clip(score_cig, 0.0, 1.0)
    seq[:, 11] = np.clip(hand_dist, 0.0, 1.0)

    return seq

def create_dataset(samples_per_class=400, output_dir=None):
    """Tạo tập train và val lưu dưới dạng .npz"""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)

    X_train, y_train = [], []
    X_val, y_val = [], []

    num_classes = 6
    val_ratio = 0.2

    for c in range(num_classes):
        for i in range(samples_per_class):
            seq = generate_sequence(c)
            if np.random.rand() < val_ratio:
                X_val.append(seq)
                y_val.append(c)
            else:
                X_train.append(seq)
                y_train.append(c)

    X_train = np.array(X_train, dtype=np.float32)
    y_train = np.array(y_train, dtype=np.int64)
    X_val = np.array(X_val, dtype=np.float32)
    y_val = np.array(y_val, dtype=np.int64)

    train_path = os.path.join(output_dir, "train_sequences.npz")
    val_path = os.path.join(output_dir, "val_sequences.npz")

    np.savez_compressed(train_path, X=X_train, y=y_train)
    np.savez_compressed(val_path, X=X_val, y=y_val)

    print(f"[Dataset] Đã tạo thành công tập dữ liệu:")
    print(f" - Train: {X_train.shape[0]} mẫu, shape: {X_train.shape} -> {train_path}")
    print(f" - Val:   {X_val.shape[0]} mẫu, shape: {X_val.shape} -> {val_path}")

    return train_path, val_path

if __name__ == "__main__":
    create_dataset(samples_per_class=500)
