"""
Chương trình chính: Hệ Thống Giám Sát Và Cảnh Báo Trạng Thái Tài Xế (GuardCabin DMS)
Chạy thời gian thực từ Webcam hoặc luồng Video.
Hotkeys:
  'q' - Thoát chương trình
  'm' - Bật / Tắt âm thanh cảnh báo (Mute)
  'r' - Đặt lại số liệu thống kê phiên lái xe
  's' - Lưu ảnh chụp màn hình HUD
"""

import sys
import os
import time
import argparse
import cv2
import numpy as np

# Đảm bảo mã hóa UTF-8 an toàn trên mọi terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from config import (
    CAMERA_ID, FRAME_WIDTH, FRAME_HEIGHT,
    SEQUENCE_LENGTH, FEATURE_DIM,
    TCN_ONNX_PATH, TCN_WEIGHTS_PATH, YOLO_MODEL_PATH
)
from features.face_mesh import FaceMeshDetector
from features.feature_extractor import FeatureExtractor
from models.yolo_detector import YOLODetector
from models.tcn_classifier import TCNClassifier
from core.sliding_window import SlidingWindowBuffer
from core.decision_engine import DecisionEngine
from core.alert_manager import AlertManager
from core.session_tracker import SessionTracker
from ui.hud_overlay import HUDOverlay

def parse_args():
    parser = argparse.ArgumentParser(description="GuardCabin DMS - Real-time Driver Monitoring System")
    parser.add_argument("--source", type=str, default=str(CAMERA_ID), help="Chỉ số Camera (e.g. 0) hoặc đường dẫn file video")
    parser.add_argument("--yolo", type=str, default=YOLO_MODEL_PATH, help="Đường dẫn file trọng số YOLO (e.g. weights/best.pt)")
    parser.add_argument("--onnx", action="store_true", help="Ưu tiên suy luận bằng ONNX Runtime")
    parser.add_argument("--yolo-interval", type=int, default=3, help="Chu kỳ chạy YOLO (chạy mỗi N frame để tối ưu FPS cao nhất)")
    parser.add_argument("--no-sound", action="store_true", help="Tắt âm thanh cảnh báo")
    return parser.parse_args()

def main():
    args = parse_args()
    print("=" * 65)
    print("🚗 GUARDCABIN DMS - HỆ THỐNG GIÁM SÁT TÀI XẾ THỜI GIAN THỰC")
    print("=" * 65)

    # 1. Khởi tạo thiết bị đầu vào (Camera / Video File)
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"❌ LỖI: Không thể mở luồng video từ nguồn: {source}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    # 2. Khởi tạo các Module hệ thống
    print("\n[Hệ Thống] Đang khởi tạo các mô hình và module xử lý...")
    print(f"[Hệ Thống] Sử dụng mô hình YOLO: {args.yolo}")
    face_detector = FaceMeshDetector()
    yolo_detector = YOLODetector(model_path=args.yolo)
    feature_extractor = FeatureExtractor(feature_dim=FEATURE_DIM)
    window_buffer = SlidingWindowBuffer(window_size=SEQUENCE_LENGTH, feature_dim=FEATURE_DIM)

    # Khởi tạo mô hình TCN
    tcn_classifier = TCNClassifier(
        onnx_path=TCN_ONNX_PATH,
        pth_path=TCN_WEIGHTS_PATH
    )

    decision_engine = DecisionEngine()
    alert_manager = AlertManager(enabled=not args.no_sound)
    session_tracker = SessionTracker()
    hud = HUDOverlay()

    print("[Hệ Thống] Khởi tạo hoàn tất! Bắt đầu giám sát...")
    print("👉 Phím tắt: [Q] Thoát | [M] Bật/Tắt Còi | [R] Reset Thống Kê | [S] Chụp ảnh")

    frame_count = 0
    cached_yolo_info = None
    fps = 30.0
    prev_time = time.time()

    window_name = "GuardCabin DMS - Driver Monitoring System"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 720)

    try:
        while True:
            loop_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                print("[Video] Kết thúc luồng video hoặc mất tín hiệu camera.")
                break

            frame_count += 1

            # 3. Giai đoạn 1: Trích xuất đặc trưng không gian (Spatial Features)
            # A. MediaPipe Face Mesh (Chạy mỗi frame)
            face_info = face_detector.process_frame(frame)

            # B. YOLOv11 Object Detection (Chạy cách quãng để đạt FPS > 30)
            face_bbox = face_info.get("face_bbox") if face_info else None
            if frame_count % args.yolo_interval == 0 or cached_yolo_info is None:
                cached_yolo_info = yolo_detector.detect(frame, face_bbox=face_bbox)
            yolo_info = cached_yolo_info

            # C. Đóng gói Vector 1D (V_t)
            v_t = feature_extractor.extract_vector(face_info, yolo_info)

            # 4. Giai đoạn 2: Cửa sổ trượt & Mô hình TCN (Temporal Features)
            window_buffer.append(v_t)
            current_window = window_buffer.get_window()

            # Phân tích chuỗi qua TCN
            tcn_result = tcn_classifier.predict(current_window)

            # 5. Bộ suy luận lai (Hybrid Decision Engine)
            evaluation = decision_engine.evaluate(face_info, yolo_info, tcn_result)

            # 6. Kích hoạt cảnh báo âm thanh
            alert_lvl = evaluation.get("alert_level", 0)
            alert_msg = evaluation.get("alert_reason", "")
            if alert_lvl > 0:
                alert_manager.trigger(alert_lvl, alert_msg)

            # 7. Cập nhật thống kê phiên lái xe
            session_tracker.update(face_info, evaluation)
            stats = session_tracker.get_stats()

            # 8. Tính toán FPS & Độ trễ
            loop_time = time.perf_counter() - loop_start
            latency_ms = loop_time * 1000.0

            curr_time = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(1e-5, (curr_time - prev_time)))
            prev_time = curr_time

            # 9. Vẽ giao diện Cyber HUD Overlay
            hud_frame = hud.draw_hud(
                frame.copy(),
                face_info=face_info,
                yolo_info=yolo_info,
                evaluation_result=evaluation,
                session_stats=stats,
                fps=fps,
                latency_ms=latency_ms
            )

            # 10. Hiển thị khung hình
            cv2.imshow(window_name, hud_frame)

            # Xử lý phím tương tác
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' hoặc ESC
                break
            elif key == ord('m'):  # Toggle mute
                alert_manager.toggle_mute()
            elif key == ord('r'):  # Reset thống kê
                session_tracker = SessionTracker()
                window_buffer.reset()
                print("[Hệ Thống] Đã đặt lại dữ liệu phiên giám sát!")
            elif key == ord('s'):  # Chụp ảnh màn hình
                shot_name = f"dms_screenshot_{int(time.time())}.jpg"
                cv2.imwrite(shot_name, hud_frame)
                print(f"[HUD] Đã lưu ảnh chụp màn hình: {shot_name}")

    except KeyboardInterrupt:
        print("\n[Hệ Thống] Nhận lệnh dừng từ người dùng.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        alert_manager.stop()
        print("[Hệ Thống] Đã giải phóng tài nguyên. Tạm biệt!")

if __name__ == "__main__":
    main()
