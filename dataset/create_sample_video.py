"""
Tạo một video mẫu ngắn 5 giây mô phỏng tài xế để kiểm thử hệ thống offline.
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

def create_demo_video(output_path="test_driver.mp4", duration_sec=4, fps=30):
    w, h = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    total_frames = duration_sec * fps

    for i in range(total_frames):
        # Tạo khung hình cabin xe mô phỏng
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Nền cabin
        frame[:] = (35, 30, 28)

        # Vẽ vô-lăng
        cv2.circle(frame, (320, 470), 180, (60, 60, 60), 16)

        # Vẽ khuôn mặt mô phỏng
        face_center_x = 320
        face_center_y = 230
        
        # Mô phỏng trạng thái bình thường -> nhắm mắt buồn ngủ
        is_eyes_closed = (i > total_frames // 2)

        # Đầu
        cv2.ellipse(frame, (face_center_x, face_center_y), (85, 115), 0, 0, 360, (190, 205, 235), -1)

        # Mắt trái & mắt phải
        if not is_eyes_closed:
            # Mắt mở
            cv2.ellipse(frame, (285, 210), (14, 8), 0, 0, 360, (255, 255, 255), -1)
            cv2.circle(frame, (285, 210), 4, (40, 40, 40), -1)
            cv2.ellipse(frame, (355, 210), (14, 8), 0, 0, 360, (255, 255, 255), -1)
            cv2.circle(frame, (355, 210), 4, (40, 40, 40), -1)
        else:
            # Mắt nhắm
            cv2.line(frame, (270, 210), (300, 210), (40, 40, 40), 3)
            cv2.line(frame, (340, 210), (370, 210), (40, 40, 40), 3)

        # Mũi
        cv2.line(frame, (320, 220), (320, 250), (150, 160, 190), 3)

        # Miệng
        cv2.ellipse(frame, (320, 285), (22, 6), 0, 0, 360, (80, 80, 180), -1)

        out.write(frame)

    out.release()
    print(f"[Demo Video] Đã tạo video mẫu kiểm thử: {output_path} ({total_frames} frames, {duration_sec}s)")

if __name__ == "__main__":
    create_demo_video()
