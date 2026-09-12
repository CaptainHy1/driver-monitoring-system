# 🚗 Hệ Thống Giám Sát Và Cảnh Báo Trạng Thái Tài Xế (Driver Monitoring System - DMS)

---

## 📌 1. Giới Thiệu Dự Án (Project Overview)

Trong các vụ tai nạn giao thông đường bộ, **sự mất tập trung, buồn ngủ và các hành vi vi phạm của tài xế** (như sử dụng điện thoại, hút thuốc) là những nguyên nhân hàng đầu. Dự án **DMS** này được xây dựng nhằm phát hiện và cảnh báo theo thời gian thực (Real-time) các trạng thái nguy hiểm của người lái xe bằng công nghệ Computer Vision và Deep Learning.

Khác với các hệ thống truyền thống chỉ phân tích hình ảnh đơn lẻ, hệ thống này ứng dụng **Kiến trúc hai giai đoạn (Two-Stage Pipeline)** kết hợp xử lý không gian (Spatial Feature) và chuỗi thời gian (Temporal Feature) để đạt độ chính xác cao và tối ưu tốc độ xử lý ($> 30\text{ FPS}$).

---

## 🎯 2. Mục Tiêu Dự Án (Key Objectives)

1. **Giám sát sinh học thời gian thực**: Phát hiện dấu hiệu mệt mỏi, buồn ngủ (chớp mắt chậm, nhắm mắt kéo dài) và ngáp liên tục.
2. **Giám sát tư thế & hướng chú ý**: Xác định góc quay của đầu (Head Pose - Pitch, Yaw, Roll) để nhận biết tài xế có đang quay mặt nhìn sang hướng khác hay gật gù hay không.
3. **Phát hiện hành vi vi phạm**: Nhận diện vật thể can thiệp như việc sử dụng điện thoại di động, hút thuốc, uống nước khi đang vận hành xe.
4. **Tối ưu hóa phần cứng**: Đảm bảo hệ thống chạy mượt mà trên các thiết bị nhúng / máy tính cá nhân bằng cách chuyển đổi mô hình sang định dạng **ONNX** và nén dữ liệu thành dạng Vector $1\text{D}$.

---

## 🧱 3. Kiến Trúc Hệ Thống (System Architecture)

Hệ thống được thiết kế theo mô hình **Two-Stage Pipeline**:

[Camera Video Stream]
│
▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 1: Trích Xuất Đặc Trưng Không Gian (Spatial)      │
│                                                             │
│  ┌────────────────────────┐    ┌─────────────────────────┐  │
│  │    YOLOv11n (ONNX)     │    │   MediaPipe Face Mesh   │  │
│  │ (Detect Face/ROI/Phone)│    │ (468 Facial Landmarks)  │  │
│  └───────────┬────────────┘    └────────────┬────────────┘  │
└──────────────┼──────────────────────────────┼───────────────┘
│                              │
└──────────────┬───────────────┘
▼
[Feature Vector (Chuỗi Con Số)]
(EAR, MAR, Head Pose, Confidence Scores)
│
▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 2: Phân Tích Chuỗi Thời Gian (Temporal)           │
│                                                             │
│   Sliding Window (Gom chuỗi N = 30 Frames ~ 1 giây)         │
│                              │                              │
│                              ▼                              │
│             Mô hình TCN (Temporal ConvNet)                  │
│                              │                              │
│                              ▼                              │
│        [Phán Quyết Trạng Thái & Cảnh Báo Âm Thanh]           │
└─────────────────────────────────────────────────────────────┘


---

## 💡 4. Nguyên Lý Hoạt Động Chi Tiết (Technical Workflow)

### 🔹 Giai đoạn 1: YOLOv11 + MediaPipe (Trích xuất Feature Vector)
* **YOLOv11n (ONNX Runtime)**: Đóng vai trò làm "mắt thần" định vị vùng quan tâm (ROI - Region of Interest). Cắt chính xác vùng khuôn mặt, bàn tay và nhận diện sự xuất hiện của các vật thể như `Phone`, `Cigarette`, `Bottle`.
* **MediaPipe Face Mesh**: Định vị $468$ điểm đặc trưng 3D trên khuôn mặt để tính toán các chỉ số sinh học:
  * **EAR (Eye Aspect Ratio)**: Tỷ lệ mở của mắt (xác định nhắm/mở mắt).
  * **MAR (Mouth Aspect Ratio)**: Độ mở của miệng (xác định ngáp).
  * **Head Pose Estimation ($Pitch, Yaw, Roll$)**: Góc nghiêng và hướng nhìn của đầu.

=> Kết quả của Giai đoạn 1 chuyển đổi toàn bộ hình ảnh $2\text{D}$ phức tạp thành một **Feature Vector $1\text{D}$** bao gồm các con số đại diện cho từng khung hình.

### 🔹 Giai đoạn 2: TCN (Temporal Convolutional Network)
* Chuỗi $30$ Feature Vectors liên tiếp (tương đương $\approx 1$ giây video) được đưa vào mô hình **TCN**.
* TCN phân tích sự biến thiên của các chỉ số theo thời gian để đưa ra phán quyết cuối cùng (ví dụ: Chớp mắt nhanh là bình thường, nhưng $EAR < \text{threshold}$ kéo dài liên tục $1.5$ giây sẽ kích hoạt cảnh báo ngủ gật).

---

## 📊 5. Danh Mục Trạng Thái Dự Đoán (Classification Classes)

Mô hình phân loại đầu ra gồm $6$ trạng thái chính:

| STT | Trạng Thái (Class) | Dấu Hiệu Nhận Biết Kỹ Thuật | Hành Động Cảnh Báo |
| :---: | :--- | :--- | :--- |
| **0** | `Lái xe bình thường` | $EAR$ bình thường, hướng nhìn thẳng, không có vật thể vi phạm | Trạng thái an toàn (Đèn Xanh) |
| **1** | `Buồn ngủ / Mệt mỏi` | $EAR < 0.2$ kéo dài liên tục $\ge 45\text{ frames}$ | **Phát tiếng chuông Cảnh báo Level 2** |
| **2** | `Ngáp` | $MAR > 0.5$ xuất hiện dạng chu kỳ | Hiển thị nhắc nhở nghỉ ngơi |
| **3** | `Mất tập trung` | Góc xoay đầu $|Yaw| > 25^\circ$ hoặc $|Pitch| > 20^\circ$ kéo dài $> 2\text{s}$ | **Phát âm thanh Cảnh báo Level 1** |
| **4** | `Sử dụng điện thoại` | Detect `Phone` + khoảng cách Bounding Box điện thoại sát vùng mặt | Hiển thị cảnh báo vi phạm |
| **5** | `Hút thuốc / Uống nước` | Detect `Cigarette` / `Bottle` nằm tại vùng miệng | Hiển thị cảnh báo vi phạm |

---

## ⚡ 6. Lý Do Chọn Kiến Trúc Này (Advantages)

1. **Loại bỏ nhiễu môi trường (Background Noise)**: Việc crop vùng mặt bằng YOLO giúp loại bỏ toàn bộ cảnh vật bên ngoài xe, bóng cây, ánh sáng thay đổi.
2. **Tốc độ cực nhanh (High FPS)**: TCN chỉ tính toán trên chuỗi Vector con số $1\text{D}$ nhẹ thay vì tính toán trên mảng ảnh $3\text{D}$ nặng nề, giúp hệ thống đạt tốc độ $\ge 30\text{ FPS}$ dễ dàng trên GPU tầm trung hoặc CPU.
3. **Tương thích cao**: Mô hình YOLO được export sang định dạng **ONNX** giúp tối ưu phần cứng và dễ dàng tích hợp đa nền tảng (C++, Python, OpenCV).

---

## 🛠️ 7. Công Nghệ Sử Dụng (Tech Stack)

* **Language**: Python 3.9+
* **Object Detection**: YOLOv11n (`ultralytics`, ONNX Runtime)
* **Facial Landmarks**: MediaPipe Face Mesh
* **Sequence Modeling**: PyTorch (Temporal Convolutional Network - TCN)
* **Computer Vision Processing**: OpenCV, NumPy

---

## 📬 8. Hướng Phát Triển Tiếp Theo (Future Work)

- [ ] Hoàn thiện việc thu thập tập dữ liệu chuỗi Vector để train mô hình TCN.
- [ ] Tích hợp giao diện màn hình HUD / Dashboard hiển thị thông số trực tiếp cho tài xế.
- [ ] Đóng gói hệ thống lên các bo mạch nhúng như Jetson Nano hoặc Raspberry Pi 4 để thử nghiệm