"""
Main Entry Point for Multimodal Driver Monitoring System (DMS)
Supports Live Webcam, Video File, or Synthetic Demo Mode with full UTF-8 Vietnamese HUD.
"""

import os
import sys

# Suppress verbose TensorFlow / Keras warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import warnings
warnings.filterwarnings("ignore")

import argparse
import json
import time
import cv2
import numpy as np

from pipeline import DMSPipeline
from config import AlertLevel


def generate_mock_driver_frame(step: int) -> np.ndarray:
    """Generates a synthetic cabin frame for testing and demonstration."""
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Background cabin gradient
    frame[:] = (40, 42, 45)

    # Windshield zone
    cv2.rectangle(frame, (200, 50), (1080, 400), (90, 85, 75), -1)

    # Steering wheel
    cv2.circle(frame, (640, 600), 160, (20, 20, 20), 28)
    cv2.circle(frame, (640, 600), 160, (60, 60, 60), 4)

    # Driver head representation
    head_y = 280
    cv2.circle(frame, (640, head_y), 70, (180, 190, 210), -1)

    # Driver eyes
    eye_offset = 25
    cv2.circle(frame, (640 - eye_offset, head_y - 10), 10, (20, 20, 20), -1)
    cv2.circle(frame, (640 + eye_offset, head_y - 10), 10, (20, 20, 20), -1)

    # Driver body shoulders
    cv2.ellipse(frame, (640, 480), (160, 110), 0, 0, 180, (70, 60, 140), -1)

    # Dynamic scenario simulation based on step
    phase = (step // 60) % 4
    if phase == 1:
        # Simulate Phone near ear
        cv2.rectangle(frame, (700, head_y - 20), (745, head_y + 60), (30, 30, 30), -1)
        cv2.putText(frame, "MOPHONG: DUNG DIEN THOAI", (50, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    elif phase == 2:
        # Simulate Closed Eyes (Drowsiness)
        cv2.line(frame, (640 - eye_offset - 10, head_y - 10), (640 - eye_offset + 10, head_y - 10), (240, 240, 240), 3)
        cv2.line(frame, (640 + eye_offset - 10, head_y - 10), (640 + eye_offset + 10, head_y - 10), (240, 240, 240), 3)
        cv2.putText(frame, "MOPHONG: NGU GAT (NHAM MAT)", (50, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    elif phase == 3:
        cv2.putText(frame, "MOPHONG: BUONG 2 TAY KHOI VO-LANG", (50, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

    return frame


def open_camera_stream(source_str: str):
    """Safely opens camera or video stream with DirectShow fallback on Windows."""
    if source_str.isdigit():
        source_idx = int(source_str)
        # Try DirectShow on Windows for fastest and most reliable webcam initialization
        if sys.platform.startswith("win"):
            cap = cv2.VideoCapture(source_idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                return cap
        # Default backend fallback
        cap = cv2.VideoCapture(source_idx)
        return cap
    else:
        # Video file path
        return cv2.VideoCapture(source_str)


def main():
    parser = argparse.ArgumentParser(description="Multimodal Driver Monitoring System (DMS)")
    parser.add_argument("--source", type=str, default="0", help="Camera index (0) or path to video file")
    parser.add_argument("--demo", action="store_true", help="Run in synthetic demonstration mode")
    parser.add_argument("--save-log", type=str, default="dms_event_log.jsonl", help="Path to write JSONL events")
    parser.add_argument("--headless", action="store_true", help="Run without cv2.imshow window (for server/CI)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 for infinite)")
    args = parser.parse_args()

    pipeline = DMSPipeline()
    print("=" * 60)
    print("HỆ THỐNG GIÁM SÁT TÀI XẾ ĐA MÔ THỨC (MULTIMODAL DMS) ĐÃ KHỞI ĐỘNG")
    print(f"Chế độ: {'MÔ PHỎNG DEMO' if args.demo else f'NGUỒN VIDEO: {args.source}'}")
    print("Bấm phím 'q' trên cửa sổ video để dừng.")
    print("=" * 60)

    cap = None
    if not args.demo:
        cap = open_camera_stream(args.source)
        if not cap.isOpened():
            print(f"[Main] Cảnh báo: Không thể mở camera '{args.source}'. Tự động chuyển sang chế độ --demo.")
            args.demo = True
            cap = None
        else:
            # Camera warmup: try reading a frame with retries
            warmup_ok = False
            for _ in range(10):
                ret, test_frame = cap.read()
                if ret and test_frame is not None and test_frame.size > 0:
                    warmup_ok = True
                    break
                time.sleep(0.1)

            if not warmup_ok:
                print(f"[Main] Cảnh báo: Camera '{args.source}' không trả về khung hình (có thể đang bận). Chuyển sang --demo.")
                cap.release()
                cap = None
                args.demo = True

    frame_idx = 0
    log_file = open(args.save_log, "a", encoding="utf-8") if args.save_log else None

    try:
        while True:
            frame_idx += 1
            if args.max_frames > 0 and frame_idx > args.max_frames:
                break

            if args.demo:
                frame = generate_mock_driver_frame(frame_idx)
                time.sleep(0.03)  # simulate ~30 FPS
            else:
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("[Main] Kết thúc luồng video hoặc mất tín hiệu camera.")
                    break

            # Process frame through full M1-M9 pipeline
            vis_frame, decision, json_event = pipeline.process_frame(frame)

            # Log events with warning levels
            if log_file and decision.level > AlertLevel.LEVEL_0:
                log_file.write(json.dumps(json_event, ensure_ascii=False) + "\n")
                log_file.flush()

            # Console output on alert status changes
            if decision.level >= AlertLevel.LEVEL_2:
                print(f"[CẢNH BÁO MỨC {decision.level}] Frame {frame_idx}: {decision.message} (Thời gian vi phạm: {decision.violation_duration}s)")

            if not args.headless:
                cv2.imshow("Multimodal DMS - Live Cabin HUD", vis_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
    finally:
        if cap:
            cap.release()
        if log_file:
            log_file.close()
        cv2.destroyAllWindows()
        print("[Main] Hệ thống DMS đã dừng an toàn.")


if __name__ == "__main__":
    main()
