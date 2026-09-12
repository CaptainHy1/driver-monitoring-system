# TÀI LIỆU YÊU CẦU PHẦN MỀM (SRS)
## Dự án: Hệ thống Giám sát & Cảnh báo An toàn Người Lái (GuardCabin DMS)

---

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)

### 1.1 Mục tiêu dự án
Xây dựng hệ thống nhúng/Edge AI giám sát trạng thái tài xế theo thời gian thực ($\ge 25 \text{ FPS}$), có khả năng phát hiện sớm các nguy cơ mất an toàn giao thông: **Xao nhãng (dùng điện thoại, hút thuốc), Buồn ngủ, Giấc ngủ trắng (Microsleep)** và **Bất thường sức khỏe (Co giật/Đột quỵ)**.

### 1.2 Kiến trúc Hệ thống (Pipeline Architecture)
Hệ thống hoạt động theo mô hình xử lý 2 giai đoạn độc lập (Spatial-Temporal Pipeline):

[Camera Cabin]
│
▼ (Luồng Video Real-time)
[Giai đoạn 1: Trích xuất Đặc trưng (Spatial)]
├─► MediaPipe Face Mesh & Hands (Tọa độ Landmark)
└─► YOLOv11n (Object Detection: Điện thoại, Thuốc lá, Vô-lăng, Tay)
│
▼ (Chuỗi Feature Vectors qua thời gian 3s–15s)
[Giai đoạn 2: Phân tích Chuỗi (Temporal)]
└─► Mô hình TCN (Temporal Convolutional Network)
│
▼
[Đầu ra (Output & Evaluation)]
├─► Cảnh báo Thời gian thực (Còi/Giọng nói trong Cabin)
└─► Đánh giá Metrics (mAP, F1-Score, FPS, Latency, False Alarm Rate)


### 1.3 Phạm vi & Ràng buộc Kỹ thuật
* **Môi trường vận hành:** Băng ghế lái cabin ô tô, hỗ trợ môi trường thiếu sáng bằng camera hồng ngoại (IR).
* **Thiết bị phần cứng mục tiêu (Edge Device):** NVIDIA Jetson (Orin Nano/Nano) hoặc máy tính tích hợp GPU tối thiểu.
* **Độ trễ hệ thống (Latency):** $\le 100\text{ ms}$ từ khi phát hiện hành vi nguy hiểm đến khi phát còi cảnh báo.

---

## 2. MÔ TẢ MÔ HÌNH AI (MODEL SPECIFICATION)

Hệ thống tích hợp **3 mô hình AI** với vai trò riêng biệt:

| Tên mô hình | Loại kiến trúc | Đầu vào (Input) | Đầu ra (Output) | Tình trạng Train |
| :--- | :--- | :--- | :--- | :--- |
| **MediaPipe Face Mesh** | Facial Landmark Estimation | Ảnh frame thô ($640 \times 480$) | Tọa độ 468 điểm mặt $\rightarrow$ Tính $EAR, MAR, Head Pose, Gaze$ | Pre-trained (Dùng sẵn) |
| **YOLOv11n** | Object Detection (One-stage) | Ảnh frame thô ($640 \times 480$) | Bounding Box + Score: `phone`, `cigarette`, `steering_wheel`, `hand` | **Fine-tuning** |
| **TCN (Temporal Convolutional Network)** | 1D Causal Dilated Convolution | Chuỗi $N$ Vector số liệu ($T = 3s \rightarrow 15s$) | Phân loại $5$ Trạng thái tài xế | **Train from Scratch** |

### Chi tiết mô hình TCN (Core Brain)
* **Khái niệm:** Mạng tích chập 1D theo thời gian, sử dụng lớp *Causal Convolutions* (không nhìn trước tương lai) và *Dilated Convolutions* (mở rộng trường nhìn quá khứ mà không làm tăng tải tính toán).
* **Ưu điểm chọn lựa:** Xử lý song song cực nhanh, ít tốn RAM/VRAM hơn LSTM/GRU, tối ưu hóa tốt bằng TensorRT.

---

## 3. THIẾT KẾ DỮ LIỆU & GIAO DIỆN VECTOR (DATA SPECIFICATION)

### 3.1 Cấu trúc Vector Đặc trưng (Feature Vector Schema)
Tại **mỗi frame $t$**, Module Trích xuất (MediaPipe + YOLO) đóng gói dữ liệu thành một Vector số liệu chuẩn $V_t$:

$$V_t = [EAR, MAR, Pitch, Yaw, Roll, Gaze_x, Gaze_y, Score_{phone}, Score_{cig}, Hand_{wheel}]$$

* **Cửa sổ thời gian (Time Window):** Tập hợp các vector trong khoảng $T$ giây (Ví dụ: 30 FPS $\times 5\text{ giây} = 150$ vectors liên tiếp) được đưa vào TCN.

### 3.2 Bộ Dữ liệu Huấn luyện (Datasets)

#### A. Dataset cho YOLOv11 (Object Detection)
* **Nguồn dữ liệu:** State Farm Distracted Driver Detection, AUC Distracted Driver Dataset, hoặc dữ liệu tự thu thập trong cabin.
* **Nhãn (Labels):** Bounding Box cho 4 lớp: `phone`, `cigarette`, `steering_wheel`, `hand`.

#### B. Dataset cho TCN (Sequence Classification)
* **Nguồn dữ liệu:** NTHU-DMS Dataset, YawDD, hoặc trích xuất từ video giả lập hành vi thực tế.
* **Định dạng lưu trữ:** File `.csv` hoặc `.npy` chứa mảng 2D $(\text{Frames} \times \text{Features})$.
* **Các lớp nhãn phân loại (Target Classes):**
  1. `Class 0`: Lái xe an toàn / Tập trung (Normal)
  2. `Class 1`: Mất tập trung / Xao nhãng (Distracted - dùng điện thoại, hút thuốc)
  3. `Class 2`: Buồn ngủ / Ngáp tần suất cao (Drowsy)
  4. `Class 3`: Giấc ngủ trắng (Microsleep - nhắm mắt $\ge 2s$)
  5. `Class 4`: Bất thường sức khỏe (Co giật / Đột quỵ)

---

## 4. QUY TRÌNH HUẤN LUYỆN (TRAINING PIPELINE)

Quy trình train được chia làm **2 nhánh độc lập**:

[Nhánh 1: Train YOLOv11] ──> File weights: yolo_dms.pt / yolo_dms.engine
──> [Ghép nối System Real-time]
[Nhánh 2: Train TCN]     ──> File weights: tcn_dms.pth / tcn_dms.onnx


### 4.1 Quy trình Train YOLOv11 (Độc lập - Thành viên A)
1. **Tiền xử lý:** Resize ảnh về $640 \times 640$, Augmentation (Xoay nhẹ, đổi độ sáng IR, thêm nhiễu).
2. **Train:** Transfer learning từ `yolov11n.pt` với 50–100 Epochs.
3. **Đánh giá:** Đo chỉ số $mAP@0.5$ và $mAP@0.5:0.95$.
4. **Xuất mô hình:** Export sang TensorRT FP16 (`.engine`).

### 4.2 Quy trình Train TCN (Độc lập - Thành viên B)
1. **Chuẩn bị Dữ liệu Vector:** 
   * Trích xuất các chuỗi vector từ video mẫu thông qua MediaPipe & YOLO giả lập/thật.
   * Cắt dữ liệu thành các đoạn cửa sổ trượt (Sliding Window) độ dài 150 frames, bước nhảy (stride) 10 frames.
2. **Train TCN:**
   * **Loss Function:** Cross-Entropy Loss (hoặc Focal Loss nếu mất cân bằng lớp).
   * **Optimizer:** AdamW, Learning Rate = $0.001$ có Cosine Annealing Scheduler.
   * **Epochs:** 100–150 Epochs.
3. **Đánh giá:** Đo Precision, Recall, F1-Score từng lớp và Temporal IoU.
4. **Xuất mô hình:** Export sang ONNX (`.onnx`) hoặc TensorRT INT8.

---

## 5. BỘ CHỈ SỐ ĐÁNH GIÁ METRICS (EVALUATION & TARGETS)

| Hạng mục | Chỉ số đo lường (Metric) | Mục tiêu tối thiểu (Target) |
| :--- | :--- | :--- |
| **Object Detection (YOLO)** | $mAP@0.5$ | $\ge 85\%$ |
| **Phân loại trạng thái (TCN)** | $Precision, Recall, F1\text{-}Score$ | $F1 \ge 88\%$ |
| **Độ chính xác thời gian** | $Temporal\ IoU$ | $\ge 0.75$ |
| **Mức độ an toàn thực tế** | $False\ Alarm\ Rate$ (Tỷ lệ báo sai) | $\le 3\%$ |
| **Hiệu năng hệ thống** | Tốc độ xử lý (FPS) | $\ge 25\text{ FPS}$ |
| **Tối ưu phần cứng** | Định dạng nén mô hình | TensorRT FP16 / INT8 |

---

## 6. PHÂN CHIA NHIỆM VỤ DỰ ÁN (TEAMWORK)

* **Thành viên A (Module Trích xuất - Spatial Features):**
  * Tích hợp MediaPipe Face Mesh & Hands.
  * Fine-tune YOLOv11n cho vật thể cabin.
  * Viết mã nguồn gom nhóm Feature Vector $V_t$ thời gian thực.
* **Thành viên B (Module Chuỗi thời gian - Temporal Model):**
  * Thiết kế kiến trúc TCN bằng PyTorch/TensorFlow.
  * Xử lý Dataset dạng Vector chuỗi thời gian ($3s - 15s$).
  * Train, đánh giá chỉ số $F1\text{-}Score/Temporal\ IoU$ và đóng gói file `.onnx`/`.engine`.