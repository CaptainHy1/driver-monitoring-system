"""
Module theo dõi và thống kê phiên lái xe (Session Tracker).
Tính toán:
- Tần suất chớp mắt (Blinks Per Minute - BPM)
- Tổng số lần ngáp
- Tổng số lần mất tập trung & vi phạm
- Điểm đánh giá an toàn hành trình (Safety Score)
"""

import time
from config import EAR_DROWSY_THRESH, MAR_YAWN_THRESH

class SessionTracker:
    def __init__(self):
        self.start_time = time.time()
        self.total_frames = 0
        
        # Thống kê chớp mắt
        self.blink_count = 0
        self.eye_closed_streak = 0
        
        # Thống kê ngáp
        self.yawn_count = 0
        self.mouth_open_streak = 0
        
        # Thống kê vi phạm
        self.distraction_count = 0
        self.drowsy_event_count = 0
        self.phone_usage_count = 0
        
        # Trạng thái trước đó để phát hiện sườn lên (Rising Edge)
        self.prev_alert_level = 0
        self.prev_class_id = 0

    def update(self, face_info, evaluation_result):
        """Cập nhật thống kê từ frame hiện tại"""
        self.total_frames += 1
        
        if face_info and face_info.get("detected", False):
            ear = face_info.get("ear_avg", 0.3)
            mar = face_info.get("mar", 0.15)
            
            # Đếm chớp mắt: Mắt nhắm từ 1 đến 8 frames rồi mở lại
            if ear < EAR_DROWSY_THRESH:
                self.eye_closed_streak += 1
            else:
                if 1 <= self.eye_closed_streak <= 8:
                    self.blink_count += 1
                self.eye_closed_streak = 0
                
            # Đếm ngáp: Miệng mở lớn từ 15 đến 60 frames rồi ngậm lại
            if mar > MAR_YAWN_THRESH:
                self.mouth_open_streak += 1
            else:
                if 15 <= self.mouth_open_streak <= 70:
                    self.yawn_count += 1
                self.mouth_open_streak = 0

        # Đếm sự kiện vi phạm (chỉ tăng khi mới bắt đầu vi phạm)
        current_cls = evaluation_result.get("class_id", 0)
        if current_cls != self.prev_class_id:
            if current_cls == 1:
                self.drowsy_event_count += 1
            elif current_cls == 3:
                self.distraction_count += 1
            elif current_cls == 4:
                self.phone_usage_count += 1
        self.prev_class_id = current_cls

    def get_stats(self):
        """Lấy bản báo cáo thống kê phiên lái xe"""
        elapsed_sec = max(1.0, time.time() - self.start_time)
        elapsed_min = elapsed_sec / 60.0
        bpm = self.blink_count / elapsed_min if elapsed_min > 0 else 0.0

        return {
            "elapsed_seconds": elapsed_sec,
            "elapsed_formatted": time.strftime("%H:%M:%S", time.gmtime(elapsed_sec)),
            "blink_count": self.blink_count,
            "blinks_per_min": bpm,
            "yawn_count": self.yawn_count,
            "distraction_count": self.distraction_count,
            "drowsy_event_count": self.drowsy_event_count,
            "phone_usage_count": self.phone_usage_count
        }
