"""
Module quản lý cảnh báo âm thanh và hình ảnh đa cấp (Multi-level Alert Manager).
Chạy luồng âm thanh độc lập (Non-blocking background thread) để không làm giảm FPS video.
Hỗ trợ Windows winsound Native Beep, không lo phụ thuộc file âm thanh ngoài.
"""

import time
import threading
import queue
import sys
from config import (
    AUDIO_ALERT_ENABLED, ALERT_COOLDOWN_SEC,
    LEVEL1_BEEP_FREQ, LEVEL1_BEEP_DUR,
    LEVEL2_BEEP_FREQ, LEVEL2_BEEP_DUR
)

class AlertManager:
    def __init__(self, enabled=AUDIO_ALERT_ENABLED):
        self.enabled = enabled
        self.muted = False
        self.last_alert_time = {1: 0.0, 2: 0.0}
        self.alert_queue = queue.Queue(maxsize=5)
        self.is_running = True
        
        # Khởi chạy worker thread phát âm thanh nền
        self.worker_thread = threading.Thread(target=self._sound_worker, daemon=True)
        self.worker_thread.start()

    def toggle_mute(self):
        """Bật/tắt chế độ im lặng"""
        self.muted = not self.muted
        status = "BẬT" if not self.muted else "TẮT (MUTE)"
        print(f"[Cảnh báo] Âm thanh: {status}")
        return self.muted

    def trigger(self, level, reason=""):
        """
        Kích hoạt cảnh báo cấp độ:
        - Level 1: Cảnh báo chú ý (Mất tập trung, ngáp)
        - Level 2: Cảnh báo khẩn cấp (Ngủ gật, dùng điện thoại)
        """
        if not self.enabled or self.muted or level not in (1, 2):
            return False

        now = time.time()
        # Kiểm tra khoảng cách thời gian giữa 2 lần phát còi
        if now - self.last_alert_time[level] < ALERT_COOLDOWN_SEC:
            return False

        self.last_alert_time[level] = now

        # Đẩy vào queue để thread nền xử lý
        try:
            self.alert_queue.put_nowait((level, reason))
            return True
        except queue.Full:
            return False

    def _sound_worker(self):
        """Hàm chạy trong thread nền phát âm thanh"""
        while self.is_running:
            try:
                level, reason = self.alert_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if self.muted:
                self.alert_queue.task_done()
                continue

            try:
                # Phát âm thanh trên hệ điều hành Windows
                if sys.platform == "win32":
                    import winsound
                    if level == 1:
                        # Beep 1 hồi nhẹ
                        winsound.Beep(LEVEL1_BEEP_FREQ, LEVEL1_BEEP_DUR)
                    elif level == 2:
                        # Chuỗi còi hú dồn dập 2 nhịp
                        winsound.Beep(LEVEL2_BEEP_FREQ, LEVEL2_BEEP_DUR)
                        time.sleep(0.08)
                        winsound.Beep(LEVEL2_BEEP_FREQ + 300, LEVEL2_BEEP_DUR)
                else:
                    # Linux / Mac fallback terminal bell
                    sys.stdout.write('\a')
                    sys.stdout.flush()
            except Exception as e:
                pass
            finally:
                self.alert_queue.task_done()

    def stop(self):
        """Dừng worker thread khi kết thúc ứng dụng"""
        self.is_running = False
