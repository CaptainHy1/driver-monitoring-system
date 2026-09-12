"""
Bộ đệm cửa sổ trượt vòng (Sliding Window Ring Buffer) cho chuỗi thời gian.
Tối ưu hóa bộ nhớ và tốc độ xử lý hàng đợi vector liên tục.
"""

import numpy as np

class SlidingWindowBuffer:
    def __init__(self, window_size=30, feature_dim=12):
        self.window_size = window_size
        self.feature_dim = feature_dim
        self.buffer = np.zeros((window_size, feature_dim), dtype=np.float32)
        self.count = 0

    def append(self, vector):
        """Thêm 1 vector đặc trưng mới vào cuối cửa sổ trượt (FIFO)"""
        # Đẩy dịch sang trái 1 hàng
        self.buffer[:-1] = self.buffer[1:]
        # Ghi vector mới vào hàng cuối cùng
        self.buffer[-1] = vector.astype(np.float32)
        if self.count < self.window_size:
            self.count += 1

    def is_ready(self):
        """Kiểm tra xem cửa sổ đã gom đủ số frame cần thiết hay chưa"""
        return self.count >= self.window_size

    def get_window(self):
        """
        Lấy chuỗi dữ liệu trong cửa sổ hiện tại (shape: [window_size, feature_dim]).
        Nếu chưa đủ frame, tự động sao chép lặp lại các frame đầu để đủ kích thước.
        """
        if self.count >= self.window_size:
            return self.buffer.copy()
        
        # Nếu mới khởi động chưa đủ frame, lấp đầy bằng các frame đã có hoặc hàng cuối
        res = self.buffer.copy()
        if self.count > 0:
            filled_part = self.buffer[-self.count:]
            res[:self.window_size - self.count] = filled_part[0]
        return res

    def reset(self):
        """Đặt lại bộ đệm"""
        self.buffer.fill(0.0)
        self.count = 0
