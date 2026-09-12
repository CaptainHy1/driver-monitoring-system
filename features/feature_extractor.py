"""
Module tổng hợp các đặc trưng không gian (Spatial Features) thành Vector 1D (V_t).
Chuẩn hóa các giá trị đầu vào cho mô hình TCN.
"""

import numpy as np

class FeatureExtractor:
    def __init__(self, feature_dim=12):
        self.feature_dim = feature_dim
        # Vector mặc định trạng thái trung hòa khi tạm thời mất dấu khuôn mặt
        self.default_vector = np.array([
            0.30,  # EAR left (mở mắt bình thường)
            0.30,  # EAR right
            0.30,  # EAR avg
            0.15,  # MAR (ngậm miệng)
            0.0,   # Pitch (nhìn thẳng)
            0.0,   # Yaw (nhìn thẳng)
            0.0,   # Roll (đầu thẳng)
            0.0,   # Gaze x (nhìn giữa)
            0.0,   # Gaze y
            0.0,   # Phone score
            0.0,   # Cigarette score
            1.5    # Hand face dist (xa mặt)
        ], dtype=np.float32)

        # Bộ lọc làm mịn (Exponential Moving Average)
        self.smooth_alpha = 0.7
        self.prev_vector = self.default_vector.copy()

    def extract_vector(self, face_info, yolo_info):
        """
        Tổng hợp dữ liệu từ FaceMesh và YOLO thành Vector V_t (12 chiều):
        Index:
        0: EAR_left
        1: EAR_right
        2: EAR_avg
        3: MAR
        4: Pitch (chuẩn hóa độ / 90.0)
        5: Yaw (chuẩn hóa độ / 90.0)
        6: Roll (chuẩn hóa độ / 90.0)
        7: Gaze_x (-1.0 -> 1.0)
        8: Gaze_y (-1.0 -> 1.0)
        9: Score_phone (0.0 -> 1.0)
        10: Score_cig (0.0 -> 1.0)
        11: Hand_dist (chuẩn hóa 0.0 -> 3.0 / 3.0)
        """
        if face_info is None or not face_info.get("detected", False):
            # Nếu không tìm thấy mặt, suy giảm dần về vector an toàn hoặc giữ nguyên
            vec = self.default_vector.copy()
            if yolo_info is not None:
                vec[9] = float(yolo_info.get("phone_score", 0.0))
                vec[10] = float(yolo_info.get("cig_score", 0.0))
            return vec

        # Trích xuất từ FaceMesh
        ear_l = float(face_info.get("ear_left", 0.3))
        ear_r = float(face_info.get("ear_right", 0.3))
        ear_avg = float(face_info.get("ear_avg", 0.3))
        mar = float(face_info.get("mar", 0.15))

        # Góc quay đầu (chuẩn hóa về khoảng [-1.0, 1.0] dựa trên 90 độ)
        pitch = float(face_info.get("pitch", 0.0)) / 90.0
        yaw = float(face_info.get("yaw", 0.0)) / 90.0
        roll = float(face_info.get("roll", 0.0)) / 90.0

        pitch = np.clip(pitch, -1.0, 1.0)
        yaw = np.clip(yaw, -1.0, 1.0)
        roll = np.clip(roll, -1.0, 1.0)

        gaze_x = float(face_info.get("gaze_x", 0.0))
        gaze_y = float(face_info.get("gaze_y", 0.0))

        # Trích xuất từ YOLO
        phone_score = 0.0
        cig_score = 0.0
        hand_dist = 1.0

        if yolo_info is not None:
            phone_score = float(yolo_info.get("phone_score", 0.0))
            cig_score = float(yolo_info.get("cig_score", 0.0))
            hand_dist = float(yolo_info.get("hand_face_dist", 1.0)) / 3.0
            hand_dist = np.clip(hand_dist, 0.0, 1.0)

        raw_vec = np.array([
            ear_l, ear_r, ear_avg, mar,
            pitch, yaw, roll,
            gaze_x, gaze_y,
            phone_score, cig_score, hand_dist
        ], dtype=np.float32)

        # Áp dụng EMA để giảm rung giật (jitter) giữa các frame
        smoothed_vec = self.smooth_alpha * raw_vec + (1.0 - self.smooth_alpha) * self.prev_vector
        self.prev_vector = smoothed_vec.copy()

        return smoothed_vec
