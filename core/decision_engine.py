"""
Module bộ suy luận lai (Hybrid Decision Engine).
Kết hợp mô hình Deep Learning TCN và các luật sinh lý Heuristic tức thời (Failsafe Rules)
để đảm bảo không có độ trễ và không bỏ sót các tình huống nguy hiểm khẩn cấp.
"""

from config import (
    CLASS_NAMES,
    EAR_DROWSY_THRESH, MAR_YAWN_THRESH,
    HEAD_YAW_THRESH, HEAD_PITCH_THRESH,
    CONSEC_DROWSY_FRAMES, CONSEC_YAWN_FRAMES,
    CONSEC_DISTRACT_FRAMES, CONSEC_PHONE_FRAMES,
    PHONE_CONF_THRESH, CIGARETTE_CONF_THRESH
)

class DecisionEngine:
    def __init__(self):
        # Bộ đếm số frame liên tiếp vi phạm
        self.drowsy_frames = 0
        self.yawn_frames = 0
        self.distracted_frames = 0
        self.phone_frames = 0
        self.smoking_frames = 0

        # Điểm tập trung của tài xế (Attention Score: 0 -> 100%)
        self.attention_score = 100.0

    def evaluate(self, face_info, yolo_info, tcn_result):
        """
        Đánh giá trạng thái tổng hợp dựa trên:
        - face_info: Dict chứa EAR, MAR, Head Pose
        - yolo_info: Dict phát hiện vật thể (phone, cigarette)
        - tcn_result: Kết quả dự đoán từ mô hình TCN
        """
        alert_level = 0
        alert_reason = ""
        final_class_id = 0

        # Nếu không có mặt trong khung hình (tài xế quay hẳn đầu đi hoặc rời vị trí)
        if face_info is None or not face_info.get("detected", False):
            self.distracted_frames += 1
            if self.distracted_frames >= CONSEC_DISTRACT_FRAMES:
                final_class_id = 3
                alert_level = 1
                alert_reason = "Không phát hiện người lái trong vùng quan sát!"
            return self._format_result(final_class_id, alert_level, alert_reason, tcn_result)

        ear = face_info.get("ear_avg", 0.3)
        mar = face_info.get("mar", 0.15)
        yaw = abs(face_info.get("yaw", 0.0))
        pitch = abs(face_info.get("pitch", 0.0))
        phone_score = yolo_info.get("phone_score", 0.0) if yolo_info else 0.0
        cig_score = yolo_info.get("cig_score", 0.0) if yolo_info else 0.0
        hand_dist = yolo_info.get("hand_face_dist", 1.0) if yolo_info else 1.0

        # 1. Cập nhật các bộ đếm số frame vi phạm
        # Buồn ngủ (Mắt nhắm liên tục)
        if ear < EAR_DROWSY_THRESH:
            self.drowsy_frames += 1
        else:
            self.drowsy_frames = max(0, self.drowsy_frames - 2)

        # Ngáp (Miệng mở to)
        if mar > MAR_YAWN_THRESH:
            self.yawn_frames += 1
        else:
            self.yawn_frames = max(0, self.yawn_frames - 2)

        # Mất tập trung (Quay đầu Yaw hoặc gật gù Pitch)
        if yaw > HEAD_YAW_THRESH or pitch > HEAD_PITCH_THRESH:
            self.distracted_frames += 1
        else:
            self.distracted_frames = max(0, self.distracted_frames - 2)

        # Dùng điện thoại
        if phone_score > PHONE_CONF_THRESH and hand_dist < 1.0:
            self.phone_frames += 1
        else:
            self.phone_frames = max(0, self.phone_frames - 2)

        # Hút thuốc / Uống nước
        if cig_score > CIGARETTE_CONF_THRESH:
            self.smoking_frames += 1
        else:
            self.smoking_frames = max(0, self.smoking_frames - 2)

        # 2. Xử lý logic phán quyết kết hợp (Hybrid Logic)
        tcn_id = tcn_result.get("class_id", 0)
        tcn_conf = tcn_result.get("confidence", 0.0)

        # Ưu tiên cấp 1: Buồn ngủ / Giấc ngủ trắng (Nguy hiểm nhất -> Level 2)
        if self.drowsy_frames >= CONSEC_DROWSY_FRAMES or (tcn_id == 1 and tcn_conf > 0.65 and self.drowsy_frames >= 15):
            final_class_id = 1
            alert_level = 2
            alert_reason = "NGUY HIỂM: Phát hiện mắt nhắm kéo dài (Buồn ngủ / Microsleep)!"
            self.attention_score = max(0.0, self.attention_score - 1.5)

        # Ưu tiên cấp 2: Dùng điện thoại khi lái xe -> Level 2
        elif self.phone_frames >= CONSEC_PHONE_FRAMES or (tcn_id == 4 and tcn_conf > 0.65):
            final_class_id = 4
            alert_level = 2
            alert_reason = "VI PHẠM: Phát hiện đang sử dụng điện thoại khi lái xe!"
            self.attention_score = max(0.0, self.attention_score - 1.0)

        # Ưu tiên cấp 3: Mất tập trung / Nhìn lệch hướng -> Level 1
        elif self.distracted_frames >= CONSEC_DISTRACT_FRAMES or (tcn_id == 3 and tcn_conf > 0.65 and self.distracted_frames >= 15):
            final_class_id = 3
            alert_level = 1
            alert_reason = "CHÚ Ý: Hướng nhìn bị lệch, hãy tập trung quan sát phía trước!"
            self.attention_score = max(0.0, self.attention_score - 0.8)

        # Ưu tiên cấp 4: Ngáp liên tục -> Level 1
        elif self.yawn_frames >= CONSEC_YAWN_FRAMES or (tcn_id == 2 and tcn_conf > 0.65):
            final_class_id = 2
            alert_level = 1
            alert_reason = "NHẮC NHỞ: Phát hiện ngáp liên tục, tài xế có dấu hiệu mệt mỏi!"
            self.attention_score = max(0.0, self.attention_score - 0.5)

        # Ưu tiên cấp 5: Hút thuốc / Uống nước -> Cảnh báo nhẹ
        elif self.smoking_frames >= 20 or (tcn_id == 5 and tcn_conf > 0.65):
            final_class_id = 5
            alert_level = 1
            alert_reason = "NHẮC NHỞ: Tránh hút thuốc / cầm nắm vật thể khi đang vận hành xe!"
            self.attention_score = max(0.0, self.attention_score - 0.4)

        # Mặc định: Bình thường / An toàn
        else:
            final_class_id = 0
            alert_level = 0
            alert_reason = "Lái xe an toàn"
            self.attention_score = min(100.0, self.attention_score + 0.2)

        return self._format_result(final_class_id, alert_level, alert_reason, tcn_result)

    def _format_result(self, class_id, alert_level, alert_reason, tcn_result):
        return {
            "class_id": class_id,
            "class_name": CLASS_NAMES[class_id],
            "alert_level": alert_level,
            "alert_reason": alert_reason,
            "attention_score": self.attention_score,
            "tcn_class_id": tcn_result.get("class_id", 0),
            "tcn_confidence": tcn_result.get("confidence", 0.0),
            "drowsy_frames": self.drowsy_frames,
            "yawn_frames": self.yawn_frames,
            "distracted_frames": self.distracted_frames
        }
