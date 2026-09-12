"""
Chương trình kiểm thử và xử lý Video đã lưu trữ (Offline Video Benchmark / Demo).
Hỗ trợ xuất video đầu ra có tích hợp đầy đủ giao diện Cyber HUD.
Sử dụng:
  python run_video.py --input test_driver.mp4 --output demo_result.mp4
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
    FRAME_WIDTH, FRAME_HEIGHT,
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
    parser = argparse.ArgumentParser(description="Chạy GuardCabin DMS trên file video")
    parser.add_argument("--input", type=str, required=True, help="Đường dẫn file video đầu vào")
    parser.add_argument("--yolo", type=str, default=YOLO_MODEL_PATH, help="Đường dẫn file trọng số YOLO (e.g. weights/best.pt)")
    parser.add_argument("--output", type=str, default=None, help="Đường dẫn file video đầu ra (tùy chọn)")
    parser.add_argument("--no-display", action="store_true", help="Không mở cửa sổ GUI hiển thị (chạy ngầm)")
    return parser.parse_args()

def main():
    args = parse_args()
    print("=" * 65)
    print(f"🎬 GUARDCABIN DMS - XỬ LÝ VIDEO: {args.input}")
    print("=" * 65)

    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"❌ Lỗi: Không thể mở video: {args.input}")
        return

    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    out_writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_writer = cv2.VideoWriter(args.output, fourcc, src_fps, (src_w, src_h))
        print(f"[Xuất Video] Sẽ lưu video có HUD vào: {args.output}")

    # Khởi tạo modules
    print(f"[Hệ Thống] Sử dụng mô hình YOLO: {args.yolo}")
    face_detector = FaceMeshDetector()
    yolo_detector = YOLODetector(model_path=args.yolo)
    feature_extractor = FeatureExtractor(feature_dim=FEATURE_DIM)
    window_buffer = SlidingWindowBuffer(window_size=SEQUENCE_LENGTH, feature_dim=FEATURE_DIM)
    tcn_classifier = TCNClassifier(onnx_path=TCN_ONNX_PATH, pth_path=TCN_WEIGHTS_PATH)
    decision_engine = DecisionEngine()
    session_tracker = SessionTracker()
    hud = HUDOverlay()

    frame_idx = 0
    cached_yolo = None
    t0 = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        t_start = time.perf_counter()

        # Face Mesh
        face_info = face_detector.process_frame(frame)

        # YOLO mỗi 3 frames
        f_bbox = face_info.get("face_bbox") if face_info else None
        if frame_idx % 3 == 0 or cached_yolo is None:
            cached_yolo = yolo_detector.detect(frame, face_bbox=f_bbox)
        yolo_info = cached_yolo

        # Vector V_t
        v_t = feature_extractor.extract_vector(face_info, yolo_info)

        # Sliding Window & TCN
        window_buffer.append(v_t)
        cur_win = window_buffer.get_window()
        tcn_res = tcn_classifier.predict(cur_win)

        # Decision
        evaluation = decision_engine.evaluate(face_info, yolo_info, tcn_res)
        session_tracker.update(face_info, evaluation)
        stats = session_tracker.get_stats()

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        # Draw HUD
        hud_frame = hud.draw_hud(
            frame,
            face_info=face_info,
            yolo_info=yolo_info,
            evaluation_result=evaluation,
            session_stats=stats,
            fps=src_fps,
            latency_ms=latency_ms
        )

        if out_writer:
            out_writer.write(hud_frame)

        if not args.no_display:
            cv2.imshow("GuardCabin DMS - Video Benchmark", hud_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        if frame_idx % 60 == 0:
            pct = (frame_idx / max(1, total_frames)) * 100
            print(f"Xử lý: Frame [{frame_idx}/{total_frames}] ({pct:.1f}%) | "
                  f"Trạng thái: {evaluation['class_name']} | Alert: Level {evaluation['alert_level']}")

    cap.release()
    if out_writer:
        out_writer.release()
    cv2.destroyAllWindows()

    total_time = time.time() - t0
    fps_avg = frame_idx / max(0.1, total_time)
    print(f"\n✅ Hoàn thành phân tích video trong {total_time:.1f}s (Trung bình: {fps_avg:.1f} FPS)")
    print("📊 Báo cáo kết quả:")
    final_stats = session_tracker.get_stats()
    for k, v in final_stats.items():
        print(f" - {k}: {v}")

if __name__ == "__main__":
    main()
