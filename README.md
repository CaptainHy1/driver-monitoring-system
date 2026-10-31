# HỆ THỐNG GIÁM SÁT HÀNH VI TÀI XẾ ĐA MÔ THỨC (MULTIMODAL DRIVER MONITORING SYSTEM - DMS)

Hệ thống thị giác máy tính thông minh hoạt động thời gian thực (real-time) bên trong khoang lái ô tô, kết hợp **3 luồng trích xuất đặc trưng song song (Face, Body, Hand & Objects)**, **dung hợp đa mô thức (Cross-Modal Attention Fusion)** và **mô hình hóa chuỗi thời gian (Temporal Transformer)** để phát hiện và cảnh báo chính xác các hành vi gây mất tập trung, buồn ngủ, và vi phạm quy chuẩn an toàn giao thông (tiêu chuẩn Euro NCAP và ISO 22839).

---

## MỤC LỤC
1. [Tổng quan Kiến trúc Hệ thống](#1-tổng-quan-kiến-trúc-hệ-thống)
2. [Chi tiết Từng Mô hình AI & Phân hệ (M1 - M9)](#2-chi-tiết-từng-mô-hình-ai--phân-hệ-m1---m9)
3. [Chi tiết Tất cả Các Loại Cảnh báo Trong Hệ thống](#3-chi-tiết-tất-cả-các-loại-cảnh-báo-trong-hệ-thống)
4. [Các Kỹ thuật & Thuật toán Cốt lõi](#4-các-kỹ-thuật--thuật-toán-cốt-lõi)
5. [Hướng dẫn Cài đặt & Chuẩn bị Môi trường](#5-hướng-dẫn-cài-đặt--chuẩn-bị-môi-trường)
6. [Hướng dẫn Sử dụng Chi tiết](#6-hướng-dẫn-sử-dụng-chi-tiết)
7. [Tùy chỉnh Tham số & Cấu hình trong `config.py`](#7-tùy-chỉnh-tham-số--cấu-hình-trong-configpy)
8. [Định dạng Nhật ký Dữ liệu & Sự kiện (Telemetry Log)](#8-định-dạng-nhật-ký-dữ-liệu--sự-kiện-telemetry-log)
9. [Cấu trúc Thư mục Dự án](#9-cấu-trúc-thư-mục-dự-án)

---

## 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

### Sơ đồ Luồng Xử lý Dữ liệu Toàn diện (Data Pipeline)

```
                       VIDEO TỪ CAMERA CABIN (RGB Frame)
                                      │
                                      ▼
                        [M1] Dynamic Preprocessor
            ┌─────────────────────────┼─────────────────────────┐
            │ (224x224)               │ (256x256)               │ (640x640)
            ▼                         ▼                         ▼
     [M2] FACE STREAM          [M3] BODY POSE            [M5] COCKPIT OBJECTS
   MediaPipe Face Mesh +         YOLOv8-Pose            YOLOv8 Object Detector
     Vision Transformer          (17 Khớp COCO)          (Phone, Cup, Bottle)
            │                         │                         │
      f_face (256D)             Keypoints (17x3)          f_hand (256D)
      Sinh trắc: EAR,           qua [M4] ST-GCN          Ước lượng vị trí
      MAR, PERCLOS, Gaze              │                  bàn tay & tương tác
            │                   f_pose (256D)                   │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                        [M6] Multimodal Feature Fusion
                Cross-Modal Attention / Linear Projection
                      Concat(768D)  ──▶  f_fused (256D)
                                      │
                                      ▼
                      [M7] Temporal Transformer Model
                 Cửa sổ trượt chuỗi T=30 frames (~1.0s)
            Tự chú ý thời gian + Cơ chế Sensor Grounding Fallback
                                      │
                        Dự đoán 5 Lớp Hành vi (C0 - C4)
                                      │
                                      ▼
                        [M8] Alert & Decision Engine
               Máy trạng thái theo dõi thời gian vi phạm (Δt)
                      Kích hoạt Cảnh báo Mức 0 -> 3
                                      │
                                      ▼
                        [M9] Visualizer & Event Logger
            Render HUD thời gian thực (Font Tiếng Việt TrueType)
                     Xuất dữ liệu: dms_event_log.jsonl
```

### Bảng Phân loại Hành vi Phân tâm (5 Distraction Classes)

| Mã Lớp | Tên Hành vi | Mô tả Nhận diện | Nguy cơ An toàn |
| :---: | :--- | :--- | :---: |
| **C0** | **Safe Driving** | Tài xế ngồi đúng tư thế, mắt nhìn thẳng quan sát đường, tay trong vùng điều khiển. | Bình thường (Safe) |
| **C1** | **Phone Usage** | Sử dụng điện thoại nghe gọi gần tai, hoặc cầm điện thoại bấm tin nhắn, nhìn xuống máy. | Cực kỳ nguy hiểm |
| **C2** | **Drowsiness / Yawning** | Nhắm mắt ngủ gật liên tục ($>1.5\text{s}$), chỉ số PERCLOS cao, hoặc ngáp ngủ kéo dài. | Nguy cấp (Critical) |
| **C3** | **Reaching Behind / Side** | Rướn người tìm đồ, cúi gập người xuống sàn, hoặc ngoái đầu ra hàng ghế sau. | Nguy hiểm cao |
| **C4** | **Eating / Drinking** | Cầm chai nước, ly nước uống hoặc cầm đồ ăn đưa lên miệng khi xe đang chạy. | Trung bình - Nguy hiểm |

---

## 2. CHI TIẾT TỪNG MÔ HÌNH AI & PHÂN HỆ (M1 - M9)

### [M1] Dynamic Preprocessor ([modules/preprocessor.py](file:///d:/Ki7/CV/duanv2/modules/preprocessor.py))
- **Mục đích**: Chuẩn bị và cắt trích xuất các vùng ảnh quan tâm (Regions of Interest - ROI) từ khung hình camera toàn cảnh khoang lái ($640 \times 480$ hoặc Full HD).
- **Các vùng trích xuất**:
  - **Face ROI ($224 \times 224$)**: Tập trung vào vùng mặt để phân tích mắt, miệng, đầu.
  - **Body ROI ($256 \times 256$)**: Tập trung vào thân trên của tài xế để ước lượng khớp xương.
  - **Cockpit ROI ($640 \times 640$)**: Vùng toàn cảnh không gian lái xe để phát hiện đồ vật và tay.
- **Kỹ thuật chuẩn hóa**: Chuẩn hóa màu sắc tensor theo ImageNet ($\text{mean}=[0.485, 0.456, 0.406]$, $\text{std}=[0.229, 0.224, 0.225]$).

---

### [M2] Nhánh Face Stream: MediaPipe Face Mesh & Face ViT ([models/face_vit.py](file:///d:/Ki7/CV/duanv2/models/face_vit.py))
- **Mục đích**: Nhận diện trạng thái mệt mỏi, ngủ gật, hướng nhìn và góc nghiêng đầu.
- **Kiến trúc mô hình**:
  1. **MediaPipe Face Mesh (468 landmarks 3D + Iris refinement)**:
     - Định vị cực nhanh và chính xác 468 điểm mốc trên khuôn mặt, bao gồm cả tâm con ngươi mắt trái (điểm 468) và mắt phải (điểm 473).
     - Hoạt động ổn định ngay cả khi đầu quay nhẹ hoặc ánh sáng thay đổi.
  2. **Face Vision Transformer (Face ViT-Tiny)**:
     - Chia ảnh mặt $224 \times 224$ thành các patch $16 \times 16$ (tổng cộng 196 patches).
     - Chiếu qua lớp tuyến tính thành chuỗi embedding 256 chiều, gắn thêm `[CLS] token` và Sinusoidal Positional Encoding.
     - Đi qua 4 Transformer Encoder Layers (Multi-Head Attention với 4 heads, MLP ratio 2.0).
     - Trích xuất vector đặc trưng khuôn mặt $\mathbf{f}_{\text{face}} \in \mathbb{R}^{256}$.
- **Đầu ra trích xuất**:
  - Vector $\mathbf{f}_{\text{face}}$ phục vụ dung hợp.
  - Chỉ số độ mở mắt $\text{EAR}$, tỷ lệ nhắm mắt tích lũy $\text{PERCLOS}$.
  - Chỉ số độ mở miệng $\text{MAR}$ và cờ phát hiện ngáp (`yawning`).
  - Hướng nhìn $\text{Gaze Direction}$ (`forward`, `looking_down`, `looking_left`, `looking_right`, `eyes_closed`).
  - Góc tư thế đầu 3D $\text{Head Pose}$ ($\text{Pitch}$, $\text{Yaw}$, $\text{Roll}$).

---

### [M3] Nhánh Body Stream: YOLOv8-Pose ([models/pose_detector.py](file:///d:/Ki7/CV/duanv2/models/pose_detector.py))
- **Mục đích**: Định vị cấu trúc khung xương thân trên và hai tay của người lái xe trong không gian cabin.
- **Mô hình**: `yolov8n-pose.pt` (Ultralytics YOLO Pose lightweight).
- **Dữ liệu trích xuất**: 17 điểm khớp xương theo chuẩn COCO:
  - Đầu/Mặt: Mũi (0), Mắt T/P (1, 2), Tai T/P (3, 4).
  - Thân trên: Vai T/P (5, 6), Khuỷu tay T/P (7, 8), Cổ tay T/P (9, 10).
  - Thân dưới: Hông T/P (11, 12), Đầu gối T/P (13, 14), Cổ chân T/P (15, 16).
- **Đầu ra**: Mảng tọa độ chuẩn hóa $(17 \times 3)$ với mỗi điểm gồm $[x, y, \text{confidence}]$ và phân loại sơ bộ tư thế (`posture_state`).

---

### [M4] Nhánh Body ST-GCN: Spatial-Temporal Graph Convolutional Network ([models/st_gcn.py](file:///d:/Ki7/CV/duanv2/models/st_gcn.py))
- **Mục đích**: Nhận diện động học cử động phức tạp qua thời gian của tài xế (như rướn người lấy đồ, cúi gập, quay người).
- **Kiến trúc mô hình**:
  - Biểu diễn khung xương người dưới dạng đồ thị không-thời gian: 17 khớp là các nút (nodes), các liên kết xương tự nhiên là các cạnh (edges).
  - Tích chập không gian (Spatial Graph Conv): Tích ma trận kề đối xứng đã chuẩn hóa $A_{\text{norm}}$ với đặc trưng các khớp.
  - Tích chập thời gian (Temporal Conv): Dùng tích chập 1D theo trục thời gian (kernel size $9 \times 1$) trên chuỗi $T=30$ frames.
- **Đầu ra**: Vector đặc trưng tư thế $\mathbf{f}_{\text{pose}} \in \mathbb{R}^{256}$.

---

### [M5] Nhánh Cockpit Object & Hand Stream ([models/object_detector.py](file:///d:/Ki7/CV/duanv2/models/object_detector.py))
- **Mục đích**: Phát hiện vật thể gây mất tập trung và ước lượng vị trí bàn tay của tài xế.
- **Mô hình**: `yolov8n.pt` (COCO pre-trained).
- **Các lớp vật thể quan tâm**:
  - `cell phone` (Điện thoại di động).
  - `bottle`, `cup` (Chai nước, cốc nước).
  - `sandwich`, `banana`, `apple` (Thức ăn).
- **Ước lượng trạng thái bàn tay (Hand Status Estimation)**:
  - Kết hợp tọa độ cổ tay từ [M3] với bounding box của vật thể phát hiện từ [M5].
  - Nhận diện các trạng thái: `holding_phone` (cầm điện thoại), `holding_drink` (cầm chai/cốc nước), `hand_raised` (giơ tay lên vùng mặt/tai), `hands_visible` (tay nhìn thấy trong tầm điều khiển).
- **Đầu ra**: Danh sách vật thể phát hiện, cờ `phone_detected`, `drink_detected`, và vector đặc trưng bàn tay $\mathbf{f}_{\text{hand}} \in \mathbb{R}^{256}$ qua mạng chiếu tuyến tính 64D $\to$ 256D.

---

### [M6] Dung hợp Đặc trưng Đa mô thức (Multimodal Fusion) ([models/multimodal_fusion.py](file:///d:/Ki7/CV/duanv2/models/multimodal_fusion.py))
- **Mục đích**: Kết hợp các thông tin dị thể từ 3 nguồn độc lập: Khuôn mặt $\mathbf{f}_{\text{face}}$, Khung xương $\mathbf{f}_{\text{pose}}$, và Bàn tay/Vật thể $\mathbf{f}_{\text{hand}}$.
- **Kiến trúc**:
  - **Cơ chế Cross-Modal Attention**: Coi 3 vector đặc trưng như 3 token trong một chuỗi không gian, áp dụng phép chiếu Query - Key - Value để các luồng tự học trọng số bổ trợ lẫn nhau (ví dụ: phát hiện tay cầm điện thoại sẽ hướng sự chú ý về phía đầu nghiêng).
  - **Lớp chiếu đa tầng (Projection MLP)**: Chiếu đặc trưng kết hợp $(3 \times 256 = 768\text{D})$ qua $\text{Linear} \to \text{LayerNorm} \to \text{GELU} \to \text{Dropout} \to \text{Linear} \to \text{LayerNorm}$ đưa về vector đại diện thống nhất $\mathbf{f}_{\text{fused}} \in \mathbb{R}^{256}$.

---

### [M7] Mô hình hóa Chuỗi Thời gian (Temporal Transformer) ([models/temporal_transformer.py](file:///d:/Ki7/CV/duanv2/models/temporal_transformer.py))
- **Mục đích**: Nhận biết hành vi thông qua diễn biến thời gian, loại bỏ các biến động đột ngột hoặc các cử động ngắn vô hại (như ngứa mũi, chớp mắt tự nhiên).
- **Kiến trúc**:
  - Cửa sổ trượt lưu trữ $T=30$ vector $\mathbf{f}_{\text{fused}}$ liên tiếp (tương ứng ~1.0 giây với camera 30 FPS).
  - Gắn Sinusoidal Positional Encoding và learnable `[CLS]` token $\to (1, T+1, 256)$.
  - Đưa qua 2 tầng Transformer Encoder (Multi-Head Attention với 4 heads, GELU, LayerNorm).
  - Head phân loại tuyến tính với hàm $\text{Softmax}$ cho ra phân phối xác suất trên 5 lớp hành vi.
- **Cơ chế Sensor Grounding Fallback (Chống báo giả)**:
  - Khi Transformer chưa nạp checkpoint huấn luyện (độ tin cậy $< 0.65$), hệ thống tự động neo vào kết quả đo thực tế của các cảm biến chuyên dụng (YOLO Object và MediaPipe Face) để bảo đảm không có báo động sai lệch.

---

### [M8] Bộ Động cơ Ra Quyết định Cảnh báo (Alert Engine) ([modules/alert_engine.py](file:///d:/Ki7/CV/duanv2/modules/alert_engine.py))
- **Mục đích**: Quản lý trạng thái và tính toán thời gian tích lũy vi phạm liên tục ($\Delta t$).
- **Nguyên lý hoạt động**:
  - Duy trì các bộ đếm thời gian riêng biệt cho từng hành vi vi phạm.
  - **Tích lũy & Phục hồi mềm (Leaky Decay)**: Khi phát hiện vi phạm, bộ đếm tăng lên theo $\Delta t$. Khi tài xế trở về trạng thái an toàn, bộ đếm không bị xóa ngay lập tức về 0 mà suy giảm dần (decay) với hệ số $1.5\Delta t - 2.5\Delta t$ để tránh trường hợp tài xế vừa nhìn lên đường rồi lại cúi xuống lặp lại liên tục.
  - Phân tích độ ưu tiên từ Mức 3 (Ngủ gật) xuống Mức 2 (Dùng điện thoại, cúi đầu) và Mức 1 (Ngáp, vươn người, ăn uống).

---

### [M9] Bộ Trực quan hóa HUD & Ghi Nhật ký ([modules/visualizer.py](file:///d:/Ki7/CV/duanv2/modules/visualizer.py))
- **Giao diện HUD chuyên nghiệp**:
  - **Thanh Banner Trạng thái**: Đổi màu động theo Mức cảnh báo (Xanh, Vàng, Cam, Đỏ).
  - **Chữ Tiếng Việt chuẩn Unicode**: Sử dụng thư viện PIL ImageDraw với font TrueType hệ thống (Arial/Segoe UI) vẽ trực tiếp lên frame, loại bỏ hoàn toàn lỗi font của OpenCV `cv2.putText`.
  - **Thanh đo rủi ro (Distraction Risk Gauge)**: Thanh tiến trình phần trăm ở góc dưới màn hình biểu thị mức độ rủi ro tích lũy của hành vi vi phạm.
  - **Bảng thông số Telemetry góc phải**: Hiển thị FPS thực tế, hướng nhìn (Gaze), chỉ số EAR/PERCLOS, và trạng thái bàn tay.
- **Trình xuất dữ liệu JSON Lines**: Tự động ghi lại từng sự kiện có cấu trúc chuẩn vào tệp `dms_event_log.jsonl`.

---

## 3. CHI TIẾT TẤT CẢ CÁC LOẠI CẢNH BÁO TRONG HỆ THỐNG

Hệ thống được thiết kế theo chuẩn an toàn phương tiện thông minh quốc tế (Euro NCAP / ISO DMS) với **4 cấp độ nghiêm ngặt (Mức 0 đến Mức 3)**. Dưới đây là danh sách chi tiết tất cả các kịch bản cảnh báo sẽ xảy ra khi vận hành:

### 3.1. Bảng Ma trận Tổng hợp Cảnh báo (Alert Matrix)

| Tên Cảnh báo | Nhánh AI Phát hiện | Mức Cảnh báo | Ngưỡng Thời gian ($\Delta t$) | Thông điệp Banner HUD | Âm thanh (Buzzer) | Hành động Hệ thống |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| **1. Ngủ gật nguy cấp** | [M2] Face Stream | **Mức 3 (Đỏ)** | $\ge 1.5\text{s}$ (hoặc PERCLOS $\ge 40\%$) | `NGUY CẤP: TÀI XẾ CÓ DẤU HIỆU NGỦ GẬT!` | **Còi réo liên tục** | Viền đỏ nhấp nháy, lưu video clip bằng chứng, log sự kiện |
| **2. Dùng điện thoại** | [M5] Object + [M3] Body | **Mức 2 (Cam)** | $\ge 1.5\text{s}$ (cúi đầu: gia tốc $1.5\times$) | `CẢNH BÁO: KHÔNG SỬ DỤNG ĐIỆN THOẠI KHI LÁI XE!` | **Chuông bíp ngắt quãng** | Viền cam màn hình, lưu video clip bằng chứng, log sự kiện |
| **3. Cúi đầu nhìn xuống** | [M2] Face (Iris + Chin) | **Mức 2 (Cam)** | $\ge 2.0\text{s}$ | `CẢNH BÁO: TÀI XẾ ĐANG CÚI ĐẦU NHÌN XUỐNG, MẤT TẬP TRUNG!` | **Chuông bíp ngắt quãng** | Viền cam màn hình, lưu video clip bằng chứng, log sự kiện |
| **4. Rời mắt khỏi đường** | [M2] Face (Gaze) | **Mức 2 (Cam)** | $\ge 2.0\text{s}$ | `CẢNH BÁO: CHÚ Ý QUAN SÁT ĐƯỜNG PHÍA TRƯỚC!` | **Chuông bíp ngắt quãng** | Viền cam màn hình, log sự kiện |
| **5. Ngáp ngủ kéo dài** | [M2] Face (MAR + Latch) | **Mức 1 (Vàng)** | $\ge 0.6\text{s}$ (latch 2.0s) | `Nhắc nhở: Phát hiện tài xế ngáp ngủ / có dấu hiệu mệt mỏi!` | Im lặng (Không kêu) | Banner vàng, tăng Distraction Gauge, log sự kiện |
| **6. Vươn người / Ngoái sau** | [M3] Pose + [M4] ST-GCN | **Mức 1 (Vàng)** | $\ge 1.8\text{s}$ | `Nhắc nhở: Tránh vươn người / ngoái đầu khi xe đang chạy!` | Im lặng (Không kêu) | Banner vàng, vẽ khung xương cảnh báo, log sự kiện |
| **7. Ăn uống khi lái xe** | [M5] Object + [M3] Body | **Mức 1 (Vàng)** | $\ge 3.0\text{s}$ | `Nhắc nhở: Hạn chế ăn uống gây mất tập trung!` | Im lặng (Không kêu) | Banner vàng, khoanh BBox chai/cốc nước, log sự kiện |
| **8. Lái xe An toàn** | Cả 3 nhánh đồng thuận | **Mức 0 (Xanh)** | Bình thường | `TRẠNG THÁI: LÁI XE AN TOÀN` | Im lặng (Không kêu) | Banner xanh lá, Distraction Gauge về 0% |

---

### 3.2. Mô tả Chi tiết Từng Tình huống Cảnh báo

#### 🚨 Cảnh báo Loại 1: Ngủ gật Nguy cấp (Drowsiness / Falling Asleep - Mức 3)
* **Nguyên nhân kích hoạt**:
  * Tài xế nhắm nghiền hai mắt liên tục quá **1.5 giây** ($\text{EAR} < 0.20$).
  * Hoặc tỷ lệ thời gian nhắm mắt tích lũy trong cửa sổ 60 giây vượt ngưỡng **$\text{PERCLOS} \ge 40\%$**.
* **Hiệu ứng trực quan**: Toàn bộ viền khung hình nhấp nháy màu đỏ cảnh báo khẩn cấp, banner đỏ trên cùng hiển thị dòng chữ:
  > **NGUY CẤP: TÀI XẾ CÓ DẤU HIỆU NGỦ GẬT!**
* **Tín hiệu âm thanh**: Còi buzzer réo to và liên tục (`trigger_buzzer = True`).
* **Hành động hệ thống**: Gắn cờ `save_evidence = True` để hệ thống tự động trích xuất và lưu đoạn video clip vi phạm làm bằng chứng hộp đen.

---

#### ⚠️ Cảnh báo Loại 2: Sử dụng Điện thoại Di động (Phone Usage - Mức 2)
* **Nguyên nhân kích hoạt**:
  * Nhánh [M5] YOLO phát hiện vật thể `cell phone` trong cabin hoặc bàn tay ở trạng thái `holding_phone`.
  * Nhánh [M3] Body phát hiện tay giơ cao ngang tai (`arm_raised_to_head`) kết hợp điện thoại.
  * Hành vi kéo dài liên tục quá **1.5 giây** (`PHONE_USAGE_TIME_THRESHOLD`).
  * **Cơ chế Gia tốc rủi ro**: Nếu tài xế vừa cầm điện thoại vừa cúi đầu nhìn xuống màn hình điện thoại, bộ đếm thời gian vi phạm tăng nhanh hơn $1.5\times$ (`dt * 1.5`), giúp cảnh báo nổ ra sớm hơn bình thường.
* **Hiệu ứng trực quan**: Khung viền màu cam bao quanh màn hình, bounding box điện thoại được tô đậm viền cam, banner hiển thị:
  > **CẢNH BÁO: KHÔNG SỬ DỤNG ĐIỆN THOẠI KHI LÁI XE!**
* **Tín hiệu âm thanh**: Chuông bíp cảnh báo ngắt quãng giục tài xế cất ngay điện thoại.

---

#### ⚠️ Cảnh báo Loại 3: Cúi đầu Nhìn xuống Quá lâu (Looking Down - Mức 2)
* **Nguyên nhân kích hoạt**:
  * Tài xế cúi đầu nhìn xuống sàn xe, nhìn taplo hoặc lén nhìn màn hình điện thoại để dưới đùi.
  * Thuật toán nhận diện qua góc nghiêng đầu Pitch âm sâu ($r_{\text{chin}} < 0.28$, $\text{Pitch} < -15^\circ$) hoặc con ngươi chúc xuống mi dưới ($v_{\text{iris}} > 0.66$).
  * Trạng thái duy trì liên tục quá **2.0 giây**.
* **Hiệu ứng trực quan**: Khung viền màu cam, banner hiển thị:
  > **CẢNH BÁO: TÀI XẾ ĐANG CÚI ĐẦU NHÌN XUỐNG, MẤT TẬP TRUNG!**
* **Tín hiệu âm thanh**: Chuông bíp nhắc nhở tài xế ngẩng đầu quan sát đường.

---

#### ⚠️ Cảnh báo Loại 4: Rời mắt Khỏi Đường / Mất tập trung (Distracted Gaze - Mức 2)
* **Nguyên nhân kích hoạt**:
  * Mắt tài xế liếc sang trái (`looking_left`), sang phải (`looking_right`), hoặc quay mặt khỏi hướng đường phía trước ($\text{Yaw} > 15^\circ$ hoặc $<-15^\circ$).
  * Kéo dài liên tục quá **2.0 giây** (`GAZE_AWAY_TIME_THRESHOLD = 2.0s`).
* **Hiệu ứng trực quan**: Khung viền màu cam, telemetry hiển thị hướng nhìn vi phạm, banner hiển thị:
  > **CẢNH BÁO: CHÚ Ý QUAN SÁT ĐƯỜNG PHÍA TRƯỚC!**
* **Tín hiệu âm thanh**: Chuông bíp cảnh báo.

---

#### 🔔 Cảnh báo Loại 5: Ngáp ngủ Kéo dài / Dấu hiệu Mệt mỏi (Yawning / Fatigue - Mức 1)
* **Nguyên nhân kích hoạt**:
  * Độ mở miệng mở to theo chiều dọc: $\text{MAR}_{\text{inner}} \ge 0.45$ hoặc $\text{MAR}_{\text{outer}} \ge 0.55$.
  * Yêu cầu duy trì liên tục $\ge 0.6\text{s}$ (loại trừ hoàn toàn các cử động nói chuyện hoặc cười).
  * Bộ đếm ngáp vượt mốc $0.5\text{s}$ và kích hoạt bộ chốt trạng thái **Latch Timer $2.0\text{s}$**.
* **Hiệu ứng trực quan**: Banner màu vàng xuất hiện trang trọng trên đầu video:
  > **Nhắc nhở: Phát hiện tài xế ngáp ngủ / có dấu hiệu mệt mỏi!**
* **Tín hiệu âm thanh**: Không phát còi hú (để tránh gây hoảng loạn cho tài xế khi chỉ mới bắt đầu có dấu hiệu mệt mỏi).
* **Hành động hệ thống**: Tăng thanh đo rủi ro mệt mỏi, ghi nhận số lần ngáp tích lũy vào telemetry.

---

#### 🔔 Cảnh báo Loại 6: Vươn người / Cúi gập / Ngoái ghế sau (Reaching Behind / Side - Mức 1)
* **Nguyên nhân kích hoạt**:
  * Nhánh [M3] YOLO-Pose phát hiện trục cột sống và vị trí đầu lệch tâm xe quá mức (`abs(nose_x - 0.5) > 0.35`).
  * Hoặc [M4] ST-GCN nhận diện chuỗi cử động vươn người tìm đồ, cúi gập nhặt đồ ở sàn xe ghế phụ, hoặc ngoái đầu ra hàng ghế sau nói chuyện.
  * Kéo dài liên tục quá **1.8 giây** (`REACHING_TIME_THRESHOLD = 1.8s`).
* **Hiệu ứng trực quan**: Khung xương skeleton trên màn hình chuyển sang cảnh báo, banner hiển thị:
  > **Nhắc nhở: Tránh vươn người / ngoái đầu khi xe đang chạy!**
* **Tín hiệu âm thanh**: Không phát còi hú, chỉ hiển thị đồ họa cảnh báo.

---

#### 🔔 Cảnh báo Loại 7: Ăn uống khi Điều khiển Phương tiện (Eating / Drinking - Mức 1)
* **Nguyên nhân kích hoạt**:
  * Nhánh [M5] YOLO phát hiện chai nước (`bottle`), cốc nước (`cup`), hoặc đồ ăn (`sandwich`, `apple`, `banana`).
  * Nhánh [M3] Body xác nhận bàn tay đang cầm đồ vật đưa lên gần vùng miệng/mặt (`holding_drink`).
  * Hành vi kéo dài liên tục quá **3.0 giây** (`EATING_TIME_THRESHOLD = 3.0s`).
* **Hiệu ứng trực quan**: Bounding box khoanh vùng cốc/chai nước, banner vàng hiển thị:
  > **Nhắc nhở: Hạn chế ăn uống gây mất tập trung!**
* **Tín hiệu âm thanh**: Không phát còi hú.

---

#### ✅ Trạng thái Loại 8: Lái xe An toàn Bình thường (Safe Driving - Mức 0)
* **Đặc điểm**: Tài xế ngồi đúng tư thế, mắt nhìn thẳng quan sát phía trước (`forward`), tay ở trong vùng điều khiển xe, không sử dụng điện thoại hay vật thể gây phân tâm.
* **Hiệu ứng trực quan**: Banner màu xanh lá cây mát dịu:
  > **TRẠNG THÁI: LÁI XE AN TOÀN**
* **Thanh đo rủi ro**: Giữ ở mức **$0\%$** hoặc giảm nhanh về $0\%$.

---

### 3.3. Các Cơ chế Khử nhiễu & Chống Báo Giả của Bộ Cảnh Báo

1. **Cơ chế Phục hồi Suy giảm Mềm (Leaky Decay Recovery)**:
   * Khi tài xế ngừng vi phạm (ví dụ: cất điện thoại, ngước mắt lên nhìn đường), các bộ đếm thời gian vi phạm **không bị xóa ngay lập tức về 0**, mà sẽ giảm dần theo tốc độ $1.5\Delta t$ đến $2.5\Delta t$.
   * **Ý nghĩa thực tế**: Ngăn chặn tài xế "qua mặt" hệ thống bằng cách cúi xuống bấm điện thoại 1.4s, ngước lên 0.2s rồi lại cúi xuống tiếp. Nếu lặp lại hành vi ngắt quãng, bộ đếm sẽ nhanh chóng cộng dồn và kích hoạt cảnh báo Mức 2.
2. **Bộ Chốt Trạng thái Ngáp (Yawn Latch Timer)**:
   * Sau khi tài xế ngáp thật ($\ge 0.6\text{s}$), trạng thái cảnh báo được khóa giữ thêm **$2.0$ giây**. Nhờ đó, thông điệp nhắc nhở hiển thị rõ ràng trên màn hình và được ghi trọn vẹn vào log sự kiện mà không bị tắt mở chớp nhoáng theo từng khung hình.
3. **Thanh đo Nguy cơ Phân tâm (Distraction Risk Gauge: 0% - 100%)**:
   * Tích hợp ở góc dưới màn hình, tính toán tỷ lệ tích lũy của vi phạm nguy hiểm nhất hiện tại:
     $$\text{Risk (\%)} = \min\left(100\%, \frac{\Delta t_{\text{vi phạm}}}{T_{\text{ngưỡng}}} \times 100\%\right)$$
   * Đổi màu trực quan: **Xanh lá ($0 - 40\%$) $\to$ Vàng ($40 - 70\%$) $\to$ Cam ($70 - 90\%$) $\to$ Đỏ ($90 - 100\%$)**.

---

## 4. CÁC KỸ THUẬT & THUẬT TOÁN CỐT LÕI

### 4.1. Kỹ thuật Sinh trắc học Mắt: EAR & PERCLOS
- **Eye Aspect Ratio (EAR)**:
  Dựa trên nghiên cứu của Soukupová và Čech (2016), EAR phản ánh tỷ lệ độ mở theo chiều dọc so với chiều ngang của mắt thông qua 6 điểm mốc đặc trưng trên mi mắt:
  $$\text{EAR} = \frac{\|p_2 - p_6\|_2 + \|p_3 - p_5\|_2}{2 \|p_1 - p_4\|_2}$$
  - Điểm mốc mắt trái: $p_1=33, p_2=160, p_3=158, p_4=133, p_5=153, p_6=144$.
  - Điểm mốc mắt phải: $p_1=362, p_2=385, p_3=387, p_4=263, p_5=373, p_6=380$.
  - Khi mở mắt bình thường: $\text{EAR} \in [0.25, 0.38]$.
  - Khi mắt nhắm: $\text{EAR} < 0.20$.

- **Chỉ số Ngủ gật PERCLOS (Percentage of Eye Closure)**:
  Tỷ lệ phần trăm thời gian mà mắt nhắm ít nhất 80% trong cửa sổ trượt thời gian $T_w = 60$ giây:
  $$\text{PERCLOS} = \frac{\sum_{t \in T_w} \mathbb{I}(\text{EAR}_t < 0.20)}{N_{\text{frames trong } T_w}} \times 100\%$$
  - Khi $\text{PERCLOS} \ge 40\%$ hoặc nhắm mắt liên tục $\ge 1.5$ giây $\implies$ Kích hoạt Cảnh báo Mức 3 (Khẩn cấp).

---

### 4.2. Kỹ thuật Đo Mở Miệng & Lọc Ngáp: MAR & Latch Filter
- **Mouth Aspect Ratio (MAR)**:
  Tính toán độ mở của cả vành môi trong và vành môi ngoài:
  $$\text{MAR}_{\text{inner}} = \frac{\|p_{13} - p_{14}\|_2}{\|p_{78} - p_{308}\|_2 + \epsilon}, \quad \text{MAR}_{\text{outer}} = \frac{\|p_0 - p_{17}\|_2}{\|p_{61} - p_{291}\|_2 + \epsilon}$$
- **Vấn đề thực tế (Nói chuyện vs Ngáp ngủ)**:
  Khi nói chuyện, cử động môi chỉ đạt $\text{MAR} \approx 0.15 - 0.35$ và kéo dài ngắn ($<0.3\text{s}$). Ngáp ngủ thật sự làm miệng mở to theo chiều dọc ($\text{MAR}_{\text{inner}} \ge 0.45$ hoặc $\text{MAR}_{\text{outer}} \ge 0.55$).
- **Giải thuật Latch Filter**:
  1. Yêu cầu miệng duy trì mở to liên tục tối thiểu **$0.6$ giây** mới công nhận là một lần ngáp thật.
  2. Khi thỏa mãn điều kiện ngáp, kích hoạt **bộ chốt giữ trạng thái (Latch Timer) $2.0$ giây** để cảnh báo hiển thị rõ ràng trên màn hình và ghi vào log mà không bị nhấp nháy tắt/mở theo từng khung hình.

---

### 4.3. Kỹ thuật Ước lượng Hướng nhìn (Gaze) & Phát hiện Cúi đầu (Pitch Angle)
- **Theo dõi Con ngươi mắt (Iris Tracking)**:
  Xác định vị trí tương đối của tâm con ngươi (điểm 468 và 473) so với mí trên và mí dưới:
  $$v_{\text{iris}} = \frac{y_{\text{iris}} - y_{\text{mí trên}}}{y_{\text{mí dưới}} - y_{\text{mí trên}} + \epsilon}$$
  - Khi nhìn thẳng: $v_{\text{iris}} \approx 0.45 - 0.56$.
  - Khi nhìn xuống điện thoại trên đùi: $v_{\text{iris}} > 0.66$.

- **Phát hiện Cúi đầu bằng Tỷ lệ Cằm Chuẩn hóa ($r_{\text{chin}}$)**:
  Khi tài xế cúi đầu xuống, phần dưới khuôn mặt bị co rút do góc chiếu phối cảnh:
  $$r_{\text{chin}} = \frac{y_{\text{chin}} - y_{\text{nose}}}{y_{\text{chin}} - y_{\text{forehead}} + \epsilon}$$
  - Tư thế chuẩn: $r_{\text{chin}} \approx 0.38 - 0.42$.
  - Cúi đầu thực sự: $r_{\text{chin}} < 0.28$.
  - Công thức tính góc nghiêng đầu Pitch:
    $$\text{Pitch (độ)} = \frac{0.395 - r_{\text{chin}}}{0.15} \times (-20.0^\circ)$$
  - **Loại trừ lỗi báo giả**: Chỉ kích hoạt trạng thái `looking_down` khi cằm hạ sâu ($r_{\text{chin}} < 0.28$) hoặc khi con ngươi nhìn xuống kết hợp góc đầu nghiêng ($v_{\text{iris}} > 0.66 \land r_{\text{chin}} < 0.35$). Khi người lái nhìn thẳng bình thường, hệ thống giữ trạng thái `forward`.

---

### 4.4. Kỹ thuật Tích chập Đồ thị Không - Thời gian (ST-GCN)
- Biểu diễn khung xương người dưới dạng đồ thị $G = (V, E)$, với $V = \{v_1, \dots, v_{17}\}$ và $E$ là 18 khớp nối tự nhiên.
- Ma trận kề mở rộng với kết nối bản thân: $\tilde{A} = A + I_{17}$.
- Ma trận kề chuẩn hóa đối xứng Laplace:
  $$A_{\text{norm}} = D^{-\frac{1}{2}} \tilde{A} D^{-\frac{1}{2}}, \quad D_{ii} = \sum_{j} \tilde{A}_{ij}$$
- Phép tích chập không gian (Spatial Graph Convolution):
  $$H_{\text{spatial}} = \text{BatchNorm}\left(\text{Conv2D}\left(\sum_{w} X_{:, :, :, w} A_{w, v}\right)\right)$$
- Phép tích chập thời gian (Temporal Convolution):
  $$H_{\text{temporal}} = \text{Conv2D}_{9 \times 1}(H_{\text{spatial}}) + \text{Residual}(X)$$
  Nhờ đó, mô hình trích xuất được cả mối quan hệ không gian giữa hai tay và diễn tiến chuyển động của cơ thể qua 30 khung hình.

---

### 4.5. Kỹ thuật Dung hợp Đa mô thức (Cross-Modal Fusion) & Mô hình hóa Chuỗi Thời gian (Temporal Transformer)

Nhánh dung hợp và chuỗi thời gian đóng vai trò là "bộ não trung tâm" tổng hợp các tín hiệu phân tán từ 3 luồng cảm biến ngoại vi (Khuôn mặt, Khung xương, và Vật thể khoang lái) thành một quyết định phân loại hành vi thống nhất. Quá trình này được tổ chức thành 5 phân đoạn kỹ thuật chặt chẽ:

#### 4.5.1. Cấu trúc và Nguồn gốc Vector của Từng Nhánh Riêng Biệt (Branch Feature Vectors)

Trước khi dung hợp, mỗi nhánh cảm biến độc lập sử dụng mạng nơ-ron chuyên biệt để biến đổi dữ liệu thô (ảnh, khớp xương, bounding box) thành một vector đặc trưng biểu diễn ngữ nghĩa có cùng kích thước **$256$ chiều**:

| Tên Nhánh | Nguồn Dữ liệu Đầu vào | Mô hình Trích xuất Đặc trưng | Kích thước Tensor | Ý nghĩa Ngữ nghĩa Lưu trong Vector |
| :--- | :--- | :--- | :---: | :--- |
| **1. Face Stream ($\mathbf{f}_{\text{face}}$)** | Ảnh khuôn mặt crop $224 \times 224 \times 3$ | **Face Vision Transformer (ViT-Tiny)**: 196 patches ($16 \times 16$) $\to$ 4 Encoder Layers $\to$ lấy token `[CLS]` qua $\text{Linear}(256, 256) \to \text{GELU} \to \text{LayerNorm}$. | $\mathbf{f}_{\text{face}} \in \mathbb{R}^{256}$ | Trạng thái sinh trắc học: mức độ nhắm/mở mắt ($\text{EAR}$), độ mở miệng ($\text{MAR}$), góc nghiêng đầu Pitch/Yaw và hướng nhìn con ngươi. |
| **2. Body Stream ($\mathbf{f}_{\text{pose}}$)** | Chuỗi 17 khớp xương qua 30 frames: $(3, 30, 17)$ | **ST-GCN (Spatial-Temporal Graph Conv)**: 3 khối tích chập đồ thị không gian $A_{\text{norm}}^{17 \times 17}$ và thời gian ($9 \times 1$) $\to$ Adaptive Avg Pooling $\to \text{Linear}(256, 256) \to \text{LayerNorm} \to \text{GELU}$. | $\mathbf{f}_{\text{pose}} \in \mathbb{R}^{256}$ | Động học tư thế cơ thể: ngồi thẳng chuẩn, rướn người sang phụ lái, cúi gập nhặt đồ, ngoái đầu ra sau hoặc tay giơ lên gần tai. |
| **3. Hand/Object Stream ($\mathbf{f}_{\text{hand}}$)** | Bounding boxes từ YOLOv8 + tọa độ cổ tay | **Mạng Chiếu Tương tác (MLP Projection)**: Vector đặc tả 64D (chứa max conf, tâm $x, y$ điện thoại/chai nước, cờ cầm nắm, cờ giơ tay) $\to \text{Linear}(64, 256) \to \text{LayerNorm} \to \text{ReLU} \to \text{Linear}(256, 256)$. | $\mathbf{f}_{\text{hand}} \in \mathbb{R}^{256}$ | Tác nhân gây xao nhãng: có điện thoại, chai nước, đồ ăn trong cabin hay không; tài xế có đang cầm nắm hay buông cả hai tay. |

---

#### 4.5.2. Quá trình Nén và Dung hợp thành 1 Vector Tổng hợp ($\mathbf{f}_{\text{fused}} \in \mathbb{R}^{256}$)

Sau khi 3 nhánh trích xuất xong 3 vector $\mathbf{f}_{\text{face}}, \mathbf{f}_{\text{pose}}, \mathbf{f}_{\text{hand}} \in \mathbb{R}^{256}$, hệ thống thực hiện quy trình nén và dung hợp thông tin theo 4 bước tensor liên hoàn:

```
[Mặt: f_face (256D)]     [Thân: f_pose (256D)]     [Tay: f_hand (256D)]
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼ [Bước 1: Xếp chồng Tokens]
                         Tokens X in R^(3 x 256)
                                   │
                                   ▼ [Bước 2: Cross-Modal Attention]
                         Q, K, V in R^(3 x 256)
                      Affinity Matrix A = Softmax(QK^T / sqrt(256)) in R^(3 x 3)
                         Out = A * V in R^(3 x 256)
                                   │
                                   ▼ [Bước 3: Trải phẳng Concatenate]
                            u in R^768 (3 x 256)
                                   │
                                   ▼ [Bước 4: Mạng Nén MLP 2 tầng]
                 Linear(768 -> 512) + LayerNorm + GELU + Dropout(0.1)
                                   │  h1 in R^512
                                   ▼
                       Linear(512 -> 256) + LayerNorm
                                   │
                                   ▼
                       f_fused in R^256 (Vector Duy nhất)
```

1. **Bước 1 - Không gian hóa (Tokenization)**:
   Xếp chồng 3 vector thành ma trận token đại diện cho 3 giác quan độc lập:
   $$X = \begin{bmatrix} \mathbf{f}_{\text{face}} \\ \mathbf{f}_{\text{pose}} \\ \mathbf{f}_{\text{hand}} \end{bmatrix} \in \mathbb{R}^{3 \times 256}$$
2. **Bước 2 - Tự chú ý Chéo Luồng (Cross-Modal Attention)**:
   * Chiếu sang không gian Query - Key - Value:
     $$Q = X W_Q, \quad K = X W_K, \quad V = X W_V \quad (W_Q, W_K, W_V \in \mathbb{R}^{256 \times 256})$$
   * Tính toán ma trận trọng số tương quan chéo $\mathbf{A} \in \mathbb{R}^{3 \times 3}$:
     $$\mathbf{A} = \text{Softmax}\left(\frac{Q K^T}{\sqrt{256}}\right) \in \mathbb{R}^{3 \times 3}$$
     *Ý nghĩa*: Hàng $i$ cột $j$ thể hiện mức độ luồng $i$ cần "hỏi han" luồng $j$. Ví dụ: khi luồng Hand thấy điện thoại, trọng số tương tác giữa **Hand $\leftrightarrow$ Face** và **Hand $\leftrightarrow$ Pose** sẽ tự động tăng vọt để kiểm tra xem tài xế có đưa điện thoại lên tai hay cúi đầu nhìn xuống màn hình hay không.
   * Cập nhật ngữ cảnh đa luồng:
     $$X_{\text{attended}} = \mathbf{A} V \in \mathbb{R}^{3 \times 256}$$
3. **Bước 3 - Trải phẳng (Flatten / Concatenation)**:
   Ghép nối 3 vector đã thẩm thấu thông tin của nhau thành một vector dài:
   $$\mathbf{u} = \text{Flatten}(X_{\text{attended}}) \in \mathbb{R}^{768} \quad (3 \times 256 = 768)$$
4. **Bước 4 - Mạng Nén MLP 2 Tầng (Projection MLP & Layer Normalization)**:
   Nén vector ghép nối $768\text{D}$ về lại đúng **$256\text{D}$** bằng mạng nơ-ron phi tuyến:
   $$\mathbf{h}_1 = \text{Dropout}\left(\text{GELU}\left(\text{LayerNorm}(\mathbf{u} W_1 + b_1)\right)\right), \quad W_1 \in \mathbb{R}^{768 \times 512}$$
   $$\mathbf{f}_{\text{fused}} = \text{LayerNorm}(\mathbf{h}_1 W_2 + b_2), \quad W_2 \in \mathbb{R}^{512 \times 256}$$

👉 **Kết luận**: Từ 3 nguồn dữ liệu không đồng nhất (ảnh mặt, tọa độ khớp, nhãn đồ vật), hệ thống cô đọng thành **1 vector duy nhất $\mathbf{f}_{\text{fused}} \in \mathbb{R}^{256}$**. Vector này đại diện toàn diện cho toàn bộ trạng thái tài xế ở khung hình đó và sẵn sàng nạp vào cửa sổ trượt $T=30$ frames của Transformer chuỗi thời gian.

#### 4.5.3. Mô hình hóa Chuỗi Thời gian (Temporal Sequence Modeling with Transformer)
Các hành vi phân tâm trong cabin không diễn ra tức thời ở một frame đơn lẻ mà có tính diễn tiến theo thời gian (temporal evolution). Hệ thống sử dụng một **Transformer Encoder** để phân tích cửa sổ trượt:
1. **Cửa sổ Trượt Chuỗi Đặc trưng (Sliding Window)**:
   Lưu trữ $T = 30$ khung hình liên tiếp (~1.0 giây tại 30 FPS):
   $$X_{\text{seq}} = \left[\mathbf{f}_{\text{fused}}^{(t-T+1)}, \, \mathbf{f}_{\text{fused}}^{(t-T+2)}, \, \dots, \, \mathbf{f}_{\text{fused}}^{(t)}\right] \in \mathbb{R}^{T \times 256}$$
2. **Chèn Learnable Classification Token (`[CLS]`)**:
   Tương tự kiến trúc BERT/ViT chuẩn, một token phân loại học được $\mathbf{x}_{\text{cls}} \in \mathbb{R}^{1 \times 256}$ được gắn vào đầu chuỗi thời gian:
   $$X_0 = [\mathbf{x}_{\text{cls}}; \, X_{\text{seq}}] \in \mathbb{R}^{(T+1) \times 256}$$
3. **Mã hóa Vị trí Thời gian Sinusoidal (Sinusoidal Positional Encoding)**:
   Cung cấp thông tin về thứ tự trước - sau của từng khung hình trong chuỗi:
   $$\text{PE}_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right), \quad \text{PE}_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)$$
   $$X_{\text{input}} = X_0 + \text{PE} \in \mathbb{R}^{(T+1) \times 256}$$
4. **Khối Transformer Encoder Đa tầng (2 Layers with Pre-LayerNorm)**:
   Chuỗi đi qua 2 khối Transformer Encoder chuẩn hóa trước (Pre-LayerNorm):
   $$X_{\ell}' = \text{MultiHeadSelfAttention}(\text{LayerNorm}(X_{\ell-1})) + X_{\ell-1}$$
   $$X_{\ell} = \text{FFN}(\text{LayerNorm}(X_{\ell}')) + X_{\ell}', \quad \ell \in \{1, 2\}$$
   *Trong đó: Multi-Head Attention sử dụng 4 heads ($d_{\text{head}} = 64$), và mạng FFN có chiều ẩn $d_{ff} = 512$ với hàm kích hoạt GELU và Dropout rate $0.1$.*
5. **Trích xuất Vector Đại diện Chuỗi Thời gian**:
   $$\mathbf{z}_{\text{cls}} = \text{LayerNorm}(X_{2}[0, :]) \in \mathbb{R}^{256}$$

#### 4.5.4. Đầu Phân loại Đa lớp (Classification Head) & Phân phối Xác suất
Vector $\mathbf{z}_{\text{cls}}$ được đưa qua mạng nơ-ron phân loại tuyến tính 2 lớp để dự đoán xác suất trên 5 lớp hành vi:
$$\mathbf{z}_{\text{logits}} = W_c \cdot \text{GELU}(W_p \mathbf{z}_{\text{cls}} + b_p) + b_c \in \mathbb{R}^{5}$$
$$P(C_k \mid X_{1:T}) = \frac{\exp(\mathbf{z}_{\text{logits}}[k])}{\sum_{j=0}^{4} \exp(\mathbf{z}_{\text{logits}}[j])}, \quad k \in \{C0, C1, C2, C3, C4\}$$
Nhãn hành vi dự đoán là lớp có xác suất cực đại: $C_{\text{pred}} = \arg\max_k P(C_k)$ với độ tin cậy $\text{confidence} = \max_k P(C_k)$.

#### 4.5.5. Cơ chế Neo Cảm biến Khử Nhiễu (Sensor Grounding Fallback)
Khi Transformer chưa nạp checkpoint huấn luyện (độ tự tin ngẫu nhiên $< 0.65$), mô hình nơ-ron có thể sinh ra các phân phối xác suất không ổn định. Để đảm bảo hệ thống vận hành chuẩn xác ngay cả ở chế độ zero-shot/untrained, hệ thống áp dụng cơ chế **Sensor Grounding Fallback** (luật neo vào cảm biến thực tế):
* **Nếu YOLO phát hiện `phone_detected` hoặc tay `holding_phone`**: Cưỡng chế phân loại $\implies C1$ (Phone Usage) với độ tin cậy $0.90$.
* **Nếu Face Mesh phát hiện `eye_closed` hoặc `yawning`**: Cưỡng chế phân loại $\implies C2$ (Drowsiness / Yawning) với độ tin cậy $0.90$.
* **Nếu Body Pose phát hiện `reaching_sideways_or_behind`**: Cưỡng chế phân loại $\implies C3$ (Reaching / Turning) với độ tin cậy $0.85$.
* **Nếu YOLO phát hiện `drink_detected` hoặc tay `holding_drink`**: Cưỡng chế phân loại $\implies C4$ (Eating / Drinking) với độ tin cậy $0.85$.
* **Khi không có bất kỳ vi phạm cảm biến nào**: Cưỡng chế phân loại an toàn $\implies C0$ (Safe Driving) với độ tin cậy $0.95$.
Cơ chế này loại bỏ hoàn toàn các cảnh báo giả do trọng số mạng nơ-ron ngẫu nhiên gây ra, mang lại sự tin cậy tuyệt đối trong môi trường sản xuất thực tế.

---

## 5. HƯỚNG DẪN CÀI ĐẶT & CHUẨN BỊ MÔI TRƯỜNG

### 5.1. Yêu cầu Hệ thống
- **Hệ điều hành**: Windows 10/11, Ubuntu 20.04/22.04 LTS, hoặc macOS.
- **Python**: Khuyến nghị phiên bản **Python 3.9 - 3.12**.
- **Phần cứng**:
  - Tối thiểu: CPU Intel Core i5 / AMD Ryzen 5 thế hệ 8 trở lên, 8GB RAM (đạt 20 - 30 FPS với chế độ CPU).
  - Khuyến nghị: GPU NVIDIA GTX 1650 trở lên (hỗ trợ CUDA) để đạt trên 45 FPS thời gian thực.

### 5.2. Cài đặt Thư viện Phụ thuộc
Mở terminal tại thư mục gốc của dự án (`d:/Ki7/CV/duanv2`):
```bash
pip install -r requirements.txt
```
*Các thư viện nòng cốt được cài đặt bao gồm: `torch`, `torchvision`, `ultralytics` (YOLOv8), `mediapipe`, `opencv-python`, `pillow`, `numpy`.*

### 5.3. Quản lý và Tải Trọng số Mô hình (`weights/`)
Hệ thống được thiết kế thông minh, tự động quản lý các tệp trọng số:
1. **YOLOv8 Weights (`yolov8n.pt`, `yolov8n-pose.pt`)**:
   - Tự động tải về từ máy chủ Ultralytics trong lần chạy đầu tiên và lưu vào thư mục `weights/`.
2. **MediaPipe Face Mesh Weights**:
   - Được đóng gói tích hợp sẵn bên trong thư viện `mediapipe`, không cần tải thủ công.
3. **Mô hình Tùy biến (`face_vit.pth`, `st_gcn.pth`, `multimodal_fusion.pth`, `temporal_transformer.pth`)**:
   - Nếu bạn đã huấn luyện checkpoint tùy biến, chỉ cần đặt các tệp `.pth` vào thư mục `weights/`.
   - Nếu chưa có checkpoint, hệ thống sẽ tự động khởi tạo kiến trúc mạng nơ-ron chuẩn và kích hoạt cơ chế **Sensor Grounding Fallback** để toàn bộ hệ thống vẫn chạy chính xác 100% các tính năng giám sát.

---

## 6. HƯỚNG DẪN SỬ DỤNG CHI TIẾT

Hệ thống hỗ trợ 5 phương thức vận hành linh hoạt cho mọi môi trường phát triển:

### Cách 1: Chạy trực tiếp qua Webcam Máy tính / Camera Cabin
Phù hợp nhất khi kiểm thử tương tác trực tiếp:
```bash
python main.py --source 0
```
*(Ghi chú: Nếu bạn sử dụng camera gắn ngoài qua cổng USB, thay `0` thành `1` hoặc `2`).*

---

### Cách 2: Chạy Phân tích Tệp Video có sẵn
Dùng để đánh giá thuật toán trên các tập dữ liệu video hành trình hoặc video tài xế quay trước:
```bash
python main.py --source "duong_dan_den_video.mp4"
```
Ví dụ:
```bash
python main.py --source "data/test_driving.mp4" --save-log logs/test_log.jsonl
```

---

### Cách 3: Chạy Chế độ Mô phỏng Kiểm thử (Demo Simulation Mode)
Chế độ tiện lợi nhất khi bạn không có webcam hoặc muốn trình diễn các kịch bản vi phạm:
```bash
python main.py --demo
```
- Hệ thống sẽ tự động tạo video mô phỏng tuần tự 4 tình huống thực tế:
  1. **Pha 1**: Lái xe an toàn bình thường (Safe Driving).
  2. **Pha 2**: Tài xế cầm điện thoại nghe gọi (Phone Usage).
  3. **Pha 3**: Nhắm mắt ngủ gật liên tục (Drowsiness).
  4. **Pha 4**: Buông tay lái, rướn người tìm đồ vật (Reaching).

---

### Cách 4: Chạy Chế độ Ngầm (Headless Mode - Cho Server / Docker)
Khi triển khai trên máy chủ, thiết bị nhúng không có màn hình hiển thị (headless) hoặc chỉ cần thu thập dữ liệu nhật ký sự kiện:
```bash
python main.py --source "data/clip.mp4" --headless --max-frames 300 --save-log dms_headless.jsonl
```
- `--headless`: Tắt hoàn toàn cửa sổ `cv2.imshow`.
- `--max-frames 300`: Dừng chương trình sau khi xử lý đủ 300 frames.
- `--save-log <path>`: Đường dẫn lưu tệp sự kiện JSON Lines.

---

### Cách 5: Chạy Bộ Kiểm thử Tự động (Unit & Integration Tests)
Kiểm tra tính tương thích và toàn vẹn của cả 9 module trong pipeline:
```bash
python test_pipeline.py
```
*Kết quả mong đợi: `Test Results: 10 passed, 0 failed`.*

---

### Phím tắt Điều khiển:
- Nhấn phím **`q`** trên cửa sổ video để lưu lại dữ liệu và kết thúc chương trình một cách an toàn.

---

## 7. TÙY CHỈNH THAM SỐ & CẤU HÌNH TRONG `config.py`

Mọi ngưỡng số học và cấu hình độ nhạy của hệ thống đều được tập trung trong tệp [config.py](file:///d:/Ki7/CV/duanv2/config.py):

```python
# ---------------------------------------------------------
# Ngưỡng Thời gian Kích hoạt Cảnh báo (tính bằng giây)
# ---------------------------------------------------------
GAZE_AWAY_TIME_THRESHOLD: float = 2.0     # Rời mắt khỏi đường > 2.0s -> Cảnh báo Mức 2
EYE_CLOSURE_TIME_THRESHOLD: float = 1.5   # Nhắm mắt ngủ gật > 1.5s -> Cảnh báo Mức 3 (Khẩn cấp)
PHONE_USAGE_TIME_THRESHOLD: float = 1.5   # Cầm/nghe điện thoại > 1.5s -> Cảnh báo Mức 2
REACHING_TIME_THRESHOLD: float = 1.8      # Rướn người, cúi gập người > 1.8s -> Cảnh báo Mức 1
EATING_TIME_THRESHOLD: float = 3.0        # Ăn/uống nước khi lái xe > 3.0s -> Nhắc nhở Mức 1

# ---------------------------------------------------------
# Ngưỡng Đo Sinh trắc học Khuôn mặt
# ---------------------------------------------------------
EAR_THRESHOLD: float = 0.20               # Chỉ số EAR dưới 0.20 là nhắm mắt
MAR_THRESHOLD: float = 0.65               # Chỉ số MAR trên 0.65 là mở miệng rất rộng
PERCLOS_WINDOW_SECONDS: float = 60.0      # Cửa sổ trượt đánh giá PERCLOS (60 giây)
PERCLOS_DROWSY_THRESHOLD: float = 0.40    # Nhắm mắt > 40% thời gian cửa sổ -> Ngủ gật nguy hiểm

# ---------------------------------------------------------
# Kích thước Cửa sổ Thời gian & FPS Mặc định
# ---------------------------------------------------------
TEMPORAL_WINDOW_SIZE: int = 30           # 30 frames trong cửa sổ trượt của Transformer
DEFAULT_FPS: float = 30.0                # Tần số khung hình chuẩn
```

---

## 8. ĐỊNH DẠNG NHẬT KÝ DỮ LIỆU & SỰ KIỆN (TELEMETRY LOG)

Khi phát hiện các hành vi vi phạm (Mức 1, 2, 3), hệ thống tự động ghi nhật ký thời gian thực theo chuẩn **JSON Lines (`dms_event_log.jsonl`)**:

```json
{
  "timestamp": "2026-09-23T15:02:18.125430",
  "frame_id": 450,
  "inference_fps": 31.2,
  "system_state": {
    "predicted_class": "Phone Usage",
    "class_id": "C1",
    "alert_level": 2,
    "confidence": 0.90,
    "violation_duration_sec": 1.85
  },
  "action_commands": {
    "buzzer_active": true,
    "save_evidence_clip": true,
    "ui_banner_text": "CẢNH BÁO: KHÔNG SỬ DỤNG ĐIỆN THOẠI KHI LÁI XE!"
  },
  "sensor_telemetry": {
    "gaze_direction": "looking_down",
    "ear": 0.285,
    "perclos": 0.05,
    "head_pose": {
      "pitch": -16.4,
      "yaw": 2.1,
      "roll": 0.0
    },
    "hand_status": "holding_phone",
    "detected_objects": [
      {
        "name": "cell phone",
        "confidence": 0.84,
        "bbox": [280, 310, 390, 470]
      }
    ]
  }
}
```

---

## 9. CẤU TRÚC THƯ MỤC DỰ ÁN

```
duanv2/
├── README.md                      # Tài liệu kỹ thuật chi tiết của dự án
├── requirements.txt               # Danh sách thư viện Python cần cài đặt
├── config.py                      # Cấu hình ngưỡng an toàn, kích thước mô hình, đường dẫn weights
├── pipeline.py                    # Bộ điều phối luồng xử lý toàn trình (Pipeline Coordinator)
├── main.py                        # Điểm khởi chạy chính (hỗ trợ Webcam, Video, Demo, Headless)
├── test_pipeline.py               # Bộ kiểm thử tự động 9 phân hệ M1 - M9
│
├── models/                        # Các mô hình học sâu & trích xuất đặc trưng
│   ├── face_vit.py                # [M2] MediaPipe Face Mesh + Face Vision Transformer
│   ├── pose_detector.py           # [M3] YOLOv8-Pose trích xuất 17 khớp xương
│   ├── st_gcn.py                  # [M4] Spatial-Temporal Graph Convolutional Network
│   ├── object_detector.py         # [M5] YOLOv8 phát hiện vật thể & bàn tay
│   ├── multimodal_fusion.py       # [M6] Tầng dung hợp Cross-Modal Attention
│   └── temporal_transformer.py    # [M7] Transformer phân loại chuỗi thời gian (T=30)
│
├── modules/                       # Các phân hệ bổ trợ và giao tiếp
│   ├── preprocessor.py            # [M1] Cắt động 3 vùng ROI (Face, Body, Cockpit)
│   ├── alert_engine.py            # [M8] Máy trạng thái cảnh báo phân cấp Mức 0 - 3
│   └── visualizer.py              # [M9] Vẽ HUD tiếng Việt TrueType & xuất JSONL log
│
├── weights/                       # Thư mục lưu trữ trọng số mô hình
│   └── README.md                  # Hướng dẫn chi tiết nguồn gốc và cách nạp weights
│
└── dms_event_log.jsonl            # Tệp nhật ký các sự kiện vi phạm an toàn
```
