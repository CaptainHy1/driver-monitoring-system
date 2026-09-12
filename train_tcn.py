"""
Script huấn luyện mô hình TCN (Temporal Convolutional Network) cho DMS.
Quy trình:
1. Tự động sinh hoặc tải tập dữ liệu chuỗi (Train/Val Dataset)
2. Huấn luyện mạng TCN với AdamW, Cosine Annealing, CrossEntropyLoss
3. Đánh giá chi tiết Precision, Recall, F1-Score từng lớp
4. Tự động xuất mô hình sang cả 2 định dạng:
   - PyTorch Weights: weights/tcn_dms.pth
   - ONNX Model: weights/tcn_dms.onnx
"""

import os
import sys
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import classification_report, f1_score

# Đảm bảo mã hóa UTF-8 an toàn trên mọi terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from config import (
    TCN_CONFIG, TCN_WEIGHTS_PATH, TCN_ONNX_PATH,
    CLASS_NAMES, WEIGHTS_DIR
)
from models.tcn import TCNModel
from dataset.generate_synthetic_data import create_dataset
from dataset.data_loader import get_dataloaders

def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()
        outputs = model(x_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()

        total_loss += loss.item() * len(y_batch)
        _, preds = torch.max(outputs, 1)
        correct += (preds == y_batch).sum().item()
        total += len(y_batch)

    avg_loss = total_loss / total
    acc = correct / total
    return avg_loss, acc

def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for x_batch, y_batch in loader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)

            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)

            total_loss += loss.item() * len(y_batch)
            _, preds = torch.max(outputs, 1)

            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(y_batch.cpu().numpy())

    avg_loss = total_loss / len(all_targets)
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    acc = (all_preds == all_targets).mean()
    macro_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)

    return avg_loss, acc, macro_f1, all_preds, all_targets

def export_to_onnx(model, onnx_path, device):
    """Xuất mô hình PyTorch sang định dạng ONNX tiêu chuẩn"""
    model.eval()
    dummy_input = torch.randn(1, TCN_CONFIG["input_channels"], 30, device=device)

    os.makedirs(os.path.dirname(onnx_path), exist_ok=True)
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["feature_sequence"],
        output_names=["class_logits"]
    )
    print(f"[Export ONNX] Đã xuất thành công mô hình sang ONNX: {onnx_path}")

    # Kiểm tra tính hợp lệ bằng ONNX Runtime
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
        dummy_np = dummy_input.cpu().numpy()
        outs = session.run(None, {"feature_sequence": dummy_np})
        print(f"[Export ONNX] Kiểm tra ONNX Runtime thành công! Output shape: {outs[0].shape}")
    except Exception as e:
        print(f"[Export ONNX] Cảnh báo kiểm tra ONNX Runtime: {e}")

def main(epochs=40, batch_size=32, lr=0.001):
    print("=" * 65)
    print("🚀 BẮT ĐẦU HUẤN LUYỆN MÔ HÌNH TCN (TEMPORAL CONVOLUTIONAL NETWORK)")
    print("=" * 65)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Device] Thiết bị tính toán: {device}")

    # 1. Chuẩn bị tập dữ liệu
    dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    train_path = os.path.join(dataset_dir, "train_sequences.npz")
    val_path = os.path.join(dataset_dir, "val_sequences.npz")

    if not os.path.exists(train_path) or not os.path.exists(val_path):
        print("[Dataset] Chưa tìm thấy file dữ liệu, tiến hành sinh tập dữ liệu mẫu...")
        train_path, val_path = create_dataset(samples_per_class=500, output_dir=dataset_dir)

    train_loader, val_loader = get_dataloaders(train_path, val_path, batch_size=batch_size)
    print(f"[Dataset] Đã nạp thành công: {len(train_loader.dataset)} mẫu Train, {len(val_loader.dataset)} mẫu Val")

    # 2. Khởi tạo mô hình
    model = TCNModel(
        input_size=TCN_CONFIG["input_channels"],
        num_classes=TCN_CONFIG["num_classes"],
        num_channels=TCN_CONFIG["num_channels"],
        kernel_size=TCN_CONFIG["kernel_size"],
        dropout=TCN_CONFIG["dropout"]
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[Model] Kiến trúc TCN 4 tầng Residual. Tổng số tham số có thể huấn luyện: {total_params:,}")

    # 3. Cấu hình Loss & Optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    # 4. Vòng lặp huấn luyện
    best_val_f1 = 0.0
    start_train_time = time.time()

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_f1, _, _ = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        epoch_time = time.time() - t0

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            torch.save(model.state_dict(), TCN_WEIGHTS_PATH)
            save_mark = "⭐ (Saved Best)"
        else:
            save_mark = ""

        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs:02d}] ({epoch_time:.2f}s) | "
                  f"Train Loss: {train_loss:.4f} Acc: {train_acc*100:.1f}% | "
                  f"Val Loss: {val_loss:.4f} Acc: {val_acc*100:.1f}% F1: {val_f1*100:.1f}% {save_mark}")

    total_time = time.time() - start_train_time
    print("-" * 65)
    print(f"✅ Hoàn thành huấn luyện trong {total_time:.1f} giây! Best Val F1: {best_val_f1*100:.2f}%")

    # 5. Đánh giá mô hình tốt nhất
    print("\n📊 BÁO CÁO PHÂN LOẠI CHI TIẾT TRÊN TẬP VALIDATION:")
    model.load_state_dict(torch.load(TCN_WEIGHTS_PATH, map_location=device))
    _, _, final_f1, final_preds, final_targets = evaluate(model, val_loader, criterion, device)
    
    report = classification_report(final_targets, final_preds, target_names=CLASS_NAMES, digits=3)
    print(report)

    # 6. Xuất mô hình sang định dạng ONNX
    print("\n📦 ĐÓNG GÓI MÔ HÌNH SANG ONNX:")
    export_to_onnx(model, TCN_ONNX_PATH, device)

    print("\n🎉 Toàn bộ quy trình hoàn tất! Sẵn sàng vận hành hệ thống thời gian thực.")

if __name__ == "__main__":
    main(epochs=35, batch_size=32, lr=0.001)
