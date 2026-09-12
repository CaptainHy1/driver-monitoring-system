"""
Bộ kiểm thử tự động toàn diện cho hệ thống DMS (Automated System Test Suite).
Kiểm tra tính đúng đắn và hiệu năng của từng module trước khi vận hành thực tế.
"""

import sys
import os
import time
import numpy as np
import torch

# Đảm bảo mã hóa UTF-8 an toàn trên mọi terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def test_tcn_architecture():
    print("[TEST 1/6] Kiểm tra kiến trúc mạng TCN PyTorch...")
    from models.tcn import TCNModel
    from config import TCN_CONFIG

    batch_size = 8
    seq_len = 30
    feat_dim = 12

    model = TCNModel(
        input_size=feat_dim,
        num_classes=6,
        num_channels=TCN_CONFIG["num_channels"],
        kernel_size=TCN_CONFIG["kernel_size"]
    )

    dummy_input = torch.randn(batch_size, feat_dim, seq_len)
    outputs = model(dummy_input)

    assert outputs.shape == (batch_size, 6), f"Shape không khớp: {outputs.shape} vs (8, 6)"
    print(" -> Đạt: TCN forward pass thành công, shape chuẩn (8, 6).")

def test_sliding_window():
    print("\n[TEST 2/6] Kiểm tra bộ đệm SlidingWindowBuffer...")
    from core.sliding_window import SlidingWindowBuffer

    buf = SlidingWindowBuffer(window_size=30, feature_dim=12)
    assert not buf.is_ready(), "Buffer rỗng không được xem là ready"

    # Nạp 15 vectors
    for i in range(15):
        vec = np.ones(12, dtype=np.float32) * i
        buf.append(vec)

    win = buf.get_window()
    assert win.shape == (30, 12), f"Window shape sai: {win.shape}"

    # Nạp tiếp 20 vectors nữa
    for i in range(15, 35):
        vec = np.ones(12, dtype=np.float32) * i
        buf.append(vec)

    assert buf.is_ready(), "Buffer phải ready sau khi nạp > 30 frames"
    win_full = buf.get_window()
    # Phần tử cuối cùng phải là 34
    assert np.allclose(win_full[-1], np.ones(12) * 34), "Thứ tự FIFO bị sai"
    print(" -> Đạt: SlidingWindowBuffer hoạt động chính xác theo nguyên tắc FIFO.")

def test_decision_engine():
    print("\n[TEST 3/6] Kiểm tra bộ phán quyết lai DecisionEngine...")
    from core.decision_engine import DecisionEngine

    engine = DecisionEngine()
    dummy_tcn = {"class_id": 0, "confidence": 0.85, "probabilities": [0.85, 0.03, 0.03, 0.03, 0.03, 0.03]}

    # Kịch bản 1: Lái xe bình thường
    normal_face = {"detected": True, "ear_avg": 0.32, "mar": 0.15, "pitch": 0.0, "yaw": 0.0}
    res_normal = engine.evaluate(normal_face, None, dummy_tcn)
    assert res_normal["alert_level"] == 0, f"Lái xe bình thường không được báo động: {res_normal}"

    # Kịch bản 2: Nhắm mắt liên tục 40 frames (Buồn ngủ / Microsleep)
    drowsy_face = {"detected": True, "ear_avg": 0.12, "mar": 0.15, "pitch": 0.0, "yaw": 0.0}
    for _ in range(40):
        res_drowsy = engine.evaluate(drowsy_face, None, dummy_tcn)

    assert res_drowsy["alert_level"] == 2, f"Nhắm mắt 40 frames phải kích hoạt Level 2: {res_drowsy}"
    assert res_drowsy["class_id"] == 1, "Class ID phải là 1 (Drowsy)"

    # Kịch bản 3: Sử dụng điện thoại
    engine_phone = DecisionEngine()
    phone_yolo = {"phone_score": 0.85, "cig_score": 0.0, "hand_face_dist": 0.3}
    for _ in range(20):
        res_phone = engine_phone.evaluate(normal_face, phone_yolo, dummy_tcn)

    assert res_phone["alert_level"] == 2, f"Dùng điện thoại phải kích hoạt Level 2: {res_phone}"
    assert res_phone["class_id"] == 4, "Class ID phải là 4 (Phone)"
    print(" -> Đạt: DecisionEngine phán quyết chính xác các tình huống khẩn cấp theo Failsafe Rules.")

def test_feature_extractor():
    print("\n[TEST 4/6] Kiểm tra FeatureExtractor...")
    from features.feature_extractor import FeatureExtractor

    fe = FeatureExtractor(feature_dim=12)
    face_data = {
        "detected": True,
        "ear_left": 0.31,
        "ear_right": 0.29,
        "ear_avg": 0.30,
        "mar": 0.18,
        "pitch": 10.0,
        "yaw": -15.0,
        "roll": 5.0,
        "gaze_x": 0.1,
        "gaze_y": -0.05
    }
    yolo_data = {
        "phone_score": 0.8,
        "cig_score": 0.0,
        "hand_face_dist": 0.6
    }

    vec = fe.extract_vector(face_data, yolo_data)
    assert vec.shape == (12,), f"Vector shape không đúng: {vec.shape}"
    assert not np.isnan(vec).any(), "Vector không được chứa giá trị NaN"
    print(" -> Đạt: FeatureExtractor chuẩn hóa vector 12 chiều hợp lệ.")

def test_alert_manager():
    print("\n[TEST 5/6] Kiểm tra AlertManager...")
    from core.alert_manager import AlertManager

    am = AlertManager(enabled=True)
    # Thử kích hoạt cảnh báo Level 1
    triggered = am.trigger(1, "Test Level 1")
    assert triggered, "Cảnh báo Level 1 lần đầu phải được chấp nhận"

    # Kích hoạt lại ngay lập tức -> Phải bị cooldown chặn
    triggered_again = am.trigger(1, "Test spam")
    assert not triggered_again, "Cooldown phải ngăn chặn việc spam còi liên tiếp"

    am.stop()
    print(" -> Đạt: AlertManager xử lý bất đồng bộ và cooldown thành công.")

def test_synthetic_data_and_inference():
    print("\n[TEST 6/6] Kiểm tra sinh dữ liệu mẫu và Inference TCN...")
    from dataset.generate_synthetic_data import generate_sequence
    from models.tcn_classifier import TCNClassifier

    # Sinh chuỗi mẫu
    seq = generate_sequence(class_id=1, seq_len=30, feat_dim=12)
    assert seq.shape == (30, 12), f"Chuỗi sinh ra shape sai: {seq.shape}"

    # Chạy qua TCNClassifier
    clf = TCNClassifier()
    t0 = time.perf_counter()
    res = clf.predict(seq)
    lat_ms = (time.perf_counter() - t0) * 1000.0

    assert "class_id" in res and "confidence" in res
    print(f" -> Đạt: Inference TCN thành công trong {lat_ms:.2f} ms (Dự đoán: {res['class_name']}).")

def main():
    print("=" * 65)
    print("🧪 BẮT ĐẦU CHẠY TOÀN BỘ TEST SUITE HỆ THỐNG GUARDCABIN DMS")
    print("=" * 65)

    test_tcn_architecture()
    test_sliding_window()
    test_decision_engine()
    test_feature_extractor()
    test_alert_manager()
    test_synthetic_data_and_inference()

    print("\n" + "=" * 65)
    print("🎉 TẤT CẢ 6 BÀI KIỂM THỬ ĐỀU ĐẠT CHUẨN XUẤT SẮC (100% PASS)!")
    print("=" * 65)

if __name__ == "__main__":
    main()
