# 🚗 HƯỚNG DẪN CÀI ĐẶT & VẬN HÀNH HỆ THỐNG DMS (GUARDCABIN DMS)

Hệ thống **Giám sát & Cảnh báo Trạng thái Tài xế (Driver Monitoring System - GuardCabin DMS)** được thiết kế theo mô hình **Two-Stage Pipeline** hiện đại nhất:
- **Giai đoạn 1 (Spatial Features)**: MediaPipe Face Mesh (468 landmarks) + YOLOv11 phát hiện khuôn mặt, góc quay đầu 3D (solvePnP), tỷ lệ mở mắt EAR, mở miệng MAR, điện thoại, thuốc lá $\rightarrow$ Nén thành Feature Vector 12 chiều ($V_t$).
- **Giai đoạn 2 (Temporal Analysis)**: Cửa sổ trượt (Sliding Window $N=30$ frames) đưa vào mạng **TCN (Temporal Convolutional Network)** với các lớp Causal Dilated Convolutions để phán quyết trạng thái thời gian thực.
- **Cảnh báo & Cyber HUD**: Cảnh báo âm thanh đa cấp độ trễ thấp (Non-blocking Thread) và giao diện HUD hiển thị đồ thị sóng nhịp tim sinh học, la bàn đầu 3D, thanh đo độ tập trung.

---

## 📋 1. Yêu Cầu Môi Trường

- **Hệ điều hành**: Windows 10/11, Linux (Ubuntu 20.04+), macOS.
- **Python**: Khuyên dùng **Python 3.9 - 3.11** (Hệ thống đã kiểm thử hoàn hảo trên Python 3.11.9).
- **Phần cứng**:
  - Tối thiểu: CPU Intel Core i3 / AMD Ryzen 3 trở lên, RAM 4GB, Webcam USB hoặc Camera tích hợp Laptop.
  - Khuyến nghị: Máy tính có card đồ họa NVIDIA (CUDA) hoặc chip xử lý AI (NVIDIA Jetson) để tăng tốc ONNX Runtime.

---

## ⚙️ 2. Cài Đặt Thư Viện (Installation)

Mở terminal (PowerShell hoặc Command Prompt) tại thư mục dự án và chạy:

```bash
pip install -r requirements.txt
```

Các thư viện nòng cốt bao gồm:
- `opencv-python`: Thu nhận luồng hình ảnh và vẽ giao diện Cyber HUD.
- `mediapipe`: Trích xuất 468 điểm mốc khuôn mặt và con ngươi mắt.
- `torch` & `torchvision`: Huấn luyện và suy luận mạng TCN.
- `ultralytics`: Nhận diện vật thể cabin (điện thoại, thuốc lá, vô-lăng).
- `onnxruntime`: Công cụ suy luận siêu tốc độ cao cho mô hình ONNX.
- `scipy`, `scikit-learn`, `numpy`: Tính toán ma trận, góc quay 3D và sinh trắc học.

---

## 🧪 3. Kiểm Tra Hệ Thống Tự Động (Self-Test Suite)

Trước khi vận hành, bạn có thể chạy bộ kiểm thử toàn diện để đảm bảo mọi module hoạt động chính xác 100%:

```bash
python test_system.py
```

Bộ test sẽ tự động kiểm tra:
1. Kiến trúc mạng TCN Causal Dilated Convolutions.
2. Bộ đệm cửa sổ trượt vòng FIFO (SlidingWindowBuffer).
3. Bộ phán quyết lai Failsafe Rules (DecisionEngine).
4. Bộ trích xuất Feature Vector 12D (FeatureExtractor).
5. Luồng phát âm thanh cảnh báo bất đồng bộ (AlertManager).
6. Khả năng sinh dữ liệu mẫu và suy luận thời gian thực (Inference Latency).

---

## 🏋️ 4. Huấn Luyện Mô Hình TCN (Training Pipeline)

Dự án đã tích hợp sẵn pipeline huấn luyện tự động từ đầu đến cuối:

```bash
python train_tcn.py
```

### Quy trình tự động diễn ra:
1. **Sinh dữ liệu**: Tự động tạo tập dữ liệu mẫu sinh trắc học chuẩn hóa 6 lớp hành vi (`dataset/train_sequences.npz` và `val_sequences.npz`).
2. **Huấn luyện**: Chạy huấn luyện TCN với thuật toán tối ưu AdamW, Cosine Annealing Learning Rate Scheduler, Cross-Entropy Loss.
3. **Đánh giá**: Xuất báo cáo phân loại chi tiết (Precision, Recall, F1-Score từng lớp) trên tập validation.
4. **Đóng gói mô hình**: Tự động lưu trọng số PyTorch tại `weights/tcn_dms.pth` và xuất file mô hình ONNX tối ưu tại `weights/tcn_dms.onnx`.

---

## 🚀 5. Chạy Hệ Thống Thời Gian Thực Qua Webcam (Live DMS)

Để khởi động hệ thống giám sát trực tiếp qua webcam máy tính:

```bash
python main.py
```

### Các tùy chọn dòng lệnh mở rộng:
- **Tối ưu FPS cao nhất qua ONNX**:
  ```bash
  python main.py --onnx
  ```
- **Chỉ định camera khác (nếu cắm camera ngoài)**:
  ```bash
  python main.py --source 1
  ```
- **Điều chỉnh chu kỳ chạy YOLO (mặc định mỗi 3 frame chạy 1 lần để giữ FPS $\ge 30$)**:
  ```bash
  python main.py --yolo-interval 2
  ```
- **Tắt âm thanh cảnh báo (khi đang họp hoặc kiểm thử ban đêm)**:
  ```bash
  python main.py --no-sound
  ```

### 🎮 Phím tắt tương tác trực tiếp khi đang chạy:
| Phím | Chức năng |
| :---: | :--- |
| `Q` hoặc `ESC` | Thoát chương trình |
| `M` | Bật / Tắt nhanh âm thanh cảnh báo (Toggle Mute) |
| `R` | Đặt lại dữ liệu thống kê phiên lái xe (Reset Counters & Buffer) |
| `S` | Chụp ảnh màn hình lưu lại bằng chứng cảnh báo có giao diện HUD |

---

## 🎬 6. Chạy Thử Nghiệm Trên File Video (Video Benchmark / Demo)

Nếu bạn có sẵn video ghi lại cảnh lái xe (file `.mp4`, `.avi`, `.mov`) và muốn hệ thống phân tích, trích xuất video có kèm giao diện Cyber HUD:

```bash
python run_video.py --input test_driver.mp4 --output demo_hud_result.mp4
```

- Video kết quả sau xử lý sẽ hiển thị toàn bộ đồ thị sóng sinh học, nhận diện khuôn mặt, trạng thái cảnh báo và thống kê phiên lái.
- Nếu muốn chạy ngầm tốc độ cao không cần mở cửa sổ hiển thị:
  ```bash
  python run_video.py --input test_driver.mp4 --output demo_hud_result.mp4 --no-display
  ```

---

## 📊 7. Ý Nghĩa Các Thông Số Trên Màn Hình Cyber HUD

1. **Thanh Trạng Thái Đỉnh (Status Banner)**:
   - 🟢 **NORMAL (An toàn)**: Tài xế tỉnh táo, tập trung nhìn đường.
   - 🟡 **WARNING (Cảnh báo cấp 1)**: Mất tập trung (quay đầu $>25^\circ$), ngáp liên tục hoặc có dấu hiệu mệt mỏi. Kèm âm thanh Beep nhắc nhở nhẹ.
   - 🔴 **CRITICAL (Báo động cấp 2)**: Nhắm mắt kéo dài $\ge 1.2s$ (ngủ gật / Microsleep) hoặc sử dụng điện thoại khi đang lái. Kèm còi báo động hú dồn dập.
2. **Biểu Đồ Sóng Thời Gian Thực (Waveform Chart)**:
   - **Đường màu Cyan**: Chỉ số $EAR$ (độ mở của mắt). Có vạch tham chiếu đỏ tại ngưỡng $0.20$.
   - **Đường màu Cam**: Chỉ số $MAR$ (độ mở của miệng). Có vạch tham chiếu vàng tại ngưỡng $0.52$.
3. **Thẻ Dữ Liệu Sinh Học (Biometric Telemetry)**:
   - `Head Pitch`: Góc cúi / ngửa đầu ($^\circ$).
   - `Head Yaw`: Góc quay trái / phải ($^\circ$).
   - `Head Roll`: Góc nghiêng vai ($^\circ$).
4. **Trục 3D Head Pose**: 3 trục màu Đỏ (X), Xanh lá (Y), Xanh dương (Z) gắn trực tiếp vào vị trí mũi của tài xế để quan sát hướng quay đầu trong không gian 3D.
5. **Thanh Focus Score**: Đo lường mức độ tập trung từ $0\%$ đến $100\%$.
6. **Thanh Thống Kê Phiên Lái (Footer Telemetry)**:
   - Thời gian vận hành (`TIME: HH:MM:SS`).
   - Tần suất chớp mắt trung bình (`BLINKS: x.x / phút`).
   - Tổng số lần ngáp (`YAWNS`).
   - Tổng số lần mất tập trung (`DISTRACTS`).
   - Tổng số lần phát hiện buồn ngủ (`DROWSY`).

---

## 🔧 8. Tinh Chỉnh Cấu Hình Hệ Thống

Tất cả các ngưỡng sinh trắc học và tham số kỹ thuật được lưu tập trung trong file [config.py](file:///d:/Ki7/CV/duan/config.py):
- `EAR_DROWSY_THRESH = 0.20`: Ngưỡng nhận diện mắt nhắm. Nếu mắt nhỏ tự nhiên, có thể điều chỉnh xuống `0.18`.
- `MAR_YAWN_THRESH = 0.52`: Ngưỡng nhận diện ngáp.
- `HEAD_YAW_THRESH = 25.0`: Ngưỡng góc quay đầu coi là mất tập trung.
- `CONSEC_DROWSY_FRAMES = 35`: Số frame mắt nhắm liên tục để kích hoạt còi cấp 2 ($\approx 1.2s$).
- `ALERT_COOLDOWN_SEC = 2.0`: Thời gian giãn cách giữa các lần hú còi để tránh spam.

---

## ❓ 9. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

- **Lỗi không mở được Camera**:
  - Kiểm tra xem webcam có đang bị ứng dụng khác (Zoom, Teams, Camera App) chiếm dụng hay không.
  - Thử đổi ID camera: `python main.py --source 1`.
- **Lỗi hiển thị font chữ tiếng Việt trên terminal**:
  - Mã nguồn đã được cấu hình tự động `sys.stdout.reconfigure(encoding='utf-8')` tương thích 100% với Windows PowerShell và Command Prompt.
- **Tốc độ FPS chưa đạt 30 FPS**:
  - Sử dụng tham số `--onnx` để tăng tốc độ tính toán mạng TCN.
  - Tăng khoảng cách gọi YOLO: `python main.py --yolo-interval 4`.
