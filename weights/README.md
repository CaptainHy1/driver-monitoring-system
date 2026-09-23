# THƯ MỤC CHỨA CÁC MODEL PRE-TRAINED / CHECKPOINTS

Thư mục này dùng để lưu trữ toàn bộ các trọng số mô hình (weights `.pt` hoặc `.pth`) đã huấn luyện hoặc tải về.

---

## 1. Danh sách tên tệp trọng số mặc định

| Model | Chức năng | Tên tệp trọng số mặc định | Định dạng | Ghi chú |
| :--- | :--- | :--- | :---: | :--- |
| **Face ViT (M2)** | Nhận diện hướng nhìn Gaze, PERCLOS, Ngáp | `face_vit.pth` | PyTorch | Huấn luyện trên tập ảnh khuôn mặt cabin |
| **YOLO-Pose (M3)** | Trích xuất 17 điểm khớp xương cơ thể | `yolov8n-pose.pt` | Ultralytics YOLO | Tự động tải từ Ultralytics hoặc dùng bản custom |
| **ST-GCN (M4)** | Nhận diện chuỗi cử động tư thế khung xương | `st_gcn.pth` | PyTorch | Huấn luyện trên chuỗi khớp xương 17 điểm |
| **YOLO Cockpit (M5)** | Phát hiện tay, điện thoại, chai nước trong cabin | `yolo_cockpit.pt` (hoặc `yolov8n.pt`) | Ultralytics YOLO | Mô hình YOLOv8/v11 fine-tune vật thể cabin & tay |
| **Multimodal Fusion (M6)** | Lớp dung hợp đặc trưng đa luồng | `multimodal_fusion.pth` | PyTorch | Trọng số mạng dung hợp chiếu không gian |
| **Temporal Transformer (M7)** | Phân loại hành vi theo chuỗi thời gian | `temporal_transformer.pth` | PyTorch | Huấn luyện phân loại 5 lớp hành vi phân tâm (C0 - C4) |

---

## 2. Cách hệ thống tự động nhận diện mô hình Fine-tuned của bạn:

Hệ thống được thiết kế theo cơ chế **linh hoạt tự động (Auto-discovery & Priority Fallback)**:
1. Đối với mô hình khoang lái (M5): Hệ thống sẽ **tự động kiểm tra và ưu tiên nạp tệp `weights/yolo_cockpit.pt` trước**. Nếu chưa có tệp này, hệ thống mới dùng `weights/yolov8n.pt`.
2. Đối với các class đầu ra của mô hình fine-tune:
   * Nếu có nhãn chứa chữ `phone` (ví dụ `cell phone`, `phone`, `smartphone`) $\implies$ Hệ thống nhận diện sử dụng điện thoại.
   * Nếu có nhãn chứa chữ `hand` (ví dụ `hand`, `driver_hand`) $\implies$ Hệ thống nhận diện vị trí và số lượng bàn tay.
   * Nếu có nhãn chứa chữ `bottle` hoặc `cup` $\implies$ Hệ thống nhận diện đồ uống.
3. Nếu bạn chưa huấn luyện xong hoặc chưa có file `.pth`:
   * Hệ thống sẽ tự động dùng chế độ mặc định (hoặc MediaPipe / Heuristic zero-shot) để pipeline vẫn chạy mượt mà không bị crash.
   * `YOLO-Pose` và `YOLO Object` nếu chưa có sẵn trong `weights/` thì sẽ tự động tải file nhẹ từ Ultralytics release về.

---

## 3. Nếu bạn muốn đổi tên file hoặc đường dẫn:
Bạn chỉ cần mở tệp `config.py` và chỉnh sửa các biến đường dẫn:
```python
FACE_VIT_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "ten_file_cua_ban.pth")
YOLO_POSE_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "ten_file_cua_ban.pt")
ST_GCN_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "ten_file_cua_ban.pth")
YOLO_OBJECT_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "ten_file_cua_ban.pt")
```
