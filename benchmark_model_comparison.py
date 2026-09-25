"""
Script thử nghiệm, so sánh thực nghiệm đa mô hình (Model Exploration & Benchmarking):
1. LSTM (Baseline kinh điển chuỗi thời gian)
2. GRU (Gated Recurrent Unit)
3. Standard 1D-CNN (Mạng tích chập 1D truyền thống)
4. Customized TCN (Mô hình đề xuất của nhóm: Causal Dilated Convolutions + Residual)

Đo lường trên cùng bộ dữ liệu, cùng điều kiện phần cứng với bộ tiêu chí:
- Accuracy (%)
- Macro F1-Score (%)
- Inference Latency (ms/mẫu)
- FPS (khả năng xử lý thời gian thực)
- Số lượng tham số (Model Parameters)
"""

import os
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import accuracy_score, f1_score
import matplotlib.pyplot as plt

os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

from generate_report_data_and_charts import generate_realistic_driving_dataset, SeqDataset
from models.tcn import TCNModel

# -------------------------------------------------------------
# ĐỊNH NGHĨA CÁC MÔ HÌNH BASELINE ĐỂ SO SÁNH
# -------------------------------------------------------------
class LSTMClassifier(nn.Module):
    def __init__(self, input_size=12, hidden_size=64, num_layers=2, num_classes=6, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x: [B, C, L] -> chuyển sang [B, L, C] cho LSTM
        x = x.transpose(1, 2)
        out, (hn, cn) = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

class GRUClassifier(nn.Module):
    def __init__(self, input_size=12, hidden_size=64, num_layers=2, num_classes=6, dropout=0.2):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers=num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        x = x.transpose(1, 2)
        out, hn = self.gru(x)
        out = self.fc(out[:, -1, :])
        return out

class TemporalTransformer(nn.Module):
    def __init__(self, input_size=12, d_model=64, nhead=4, num_layers=2, num_classes=6, dropout=0.2):
        super().__init__()
        self.proj = nn.Linear(input_size, d_model)
        self.pos_emb = nn.Parameter(torch.randn(1, 30, d_model) * 0.02)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=128, dropout=dropout, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, num_classes)

    def forward(self, x):
        # x: [B, C=12, L=30] -> chuyển sang [B, L=30, C=12]
        x = x.transpose(1, 2)
        x = self.proj(x) + self.pos_emb
        out = self.transformer(x)
        out = self.fc(out.mean(dim=1))
        return out

class Standard1DCNN(nn.Module):
    def __init__(self, input_size=12, num_classes=6):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(input_size, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.net(x)

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

def train_and_eval(model, train_loader, val_loader, epochs=25, lr=0.002):
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    
    for epoch in range(epochs):
        model.train()
        for X_b, y_b in train_loader:
            optimizer.zero_grad()
            out = model(X_b)
            loss = criterion(out, y_b)
            loss.backward()
            optimizer.step()

    # Đánh giá Validation
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for X_b, y_b in val_loader:
            out = model(X_b)
            preds = torch.argmax(out, dim=1)
            all_preds.extend(preds.numpy())
            all_targets.extend(y_b.numpy())

    acc = accuracy_score(all_targets, all_preds) * 100
    f1 = f1_score(all_targets, all_preds, average="macro") * 100

    # Đo Inference Latency (chạy 300 lần 1 mẫu)
    dummy_input = torch.randn(1, 12, 30)
    for _ in range(50):
        _ = model(dummy_input)
    
    t0 = time.perf_counter()
    n_runs = 300
    for _ in range(n_runs):
        _ = model(dummy_input)
    t1 = time.perf_counter()
    latency_ms = ((t1 - t0) / n_runs) * 1000
    fps = 1000.0 / latency_ms

    return acc, f1, latency_ms, fps

def run_experiment():
    print("=" * 65)
    print("🔬 BẮT ĐẦU THỬ NGHIỆM SO SÁNH ĐA MÔ HÌNH (MODEL EXPLORATION)")
    print("=" * 65)

    X_train, y_train, X_val, y_val = generate_realistic_driving_dataset(samples_per_class=400)
    train_loader = DataLoader(SeqDataset(X_train, y_train), batch_size=32, shuffle=True)
    val_loader = DataLoader(SeqDataset(X_val, y_val), batch_size=32, shuffle=False)

    models = {
        "Standard 1D-CNN": Standard1DCNN(input_size=12, num_classes=6),
        "LSTM (2-Layers)": LSTMClassifier(input_size=12, hidden_size=64, num_layers=2, num_classes=6),
        "GRU (2-Layers)": GRUClassifier(input_size=12, hidden_size=64, num_layers=2, num_classes=6),
        "Temporal Transformer": TemporalTransformer(input_size=12, d_model=64, nhead=4, num_layers=2, num_classes=6),
        "Customized TCN (Đề xuất)": TCNModel(input_size=12, num_classes=6, num_channels=[32, 64, 64], kernel_size=3, dropout=0.25)
    }

    results = {}

    for name, model in models.items():
        params = count_parameters(model)
        print(f"\n⏳ Đang huấn luyện & benchmark: {name} (Tham số: {params:,})...")
        acc, f1, lat, fps = train_and_eval(model, train_loader, val_loader, epochs=25)
        results[name] = {
            "params": params,
            "accuracy": acc,
            "f1_score": f1,
            "latency_ms": lat,
            "fps": fps
        }
        print(f"   => Acc: {acc:.2f}% | F1: {f1:.2f}% | Latency: {lat:.2f}ms | FPS: {fps:.1f}")

    print("\n" + "=" * 65)
    print("📊 TỔNG HỢP KẾT QUẢ SO SÁNH CÁC MÔ HÌNH:")
    print("=" * 65)
    print(f"{'Mô hình':<28} | {'Params':<8} | {'Accuracy':<9} | {'Macro F1':<9} | {'Latency':<9} | {'FPS':<6}")
    print("-" * 75)
    for name, res in results.items():
        print(f"{name:<28} | {res['params']:<8,} | {res['accuracy']:<8.2f}% | {res['f1_score']:<8.2f}% | {res['latency_ms']:<7.2f}ms | {res['fps']:<6.1f}")

    # ---------------------------------------------------------
    # VẼ BIỂU ĐỒ SO SÁNH
    # ---------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")

    model_names = list(results.keys())
    short_names = ["1D-CNN", "LSTM", "GRU", "Customized TCN\n(Đề xuất)"]
    short_names = ["1D-CNN", "LSTM", "GRU", "Temporal\nTransformer", "Customized TCN\n(Đề xuất)"]
    f1_scores = [results[m]["f1_score"] for m in model_names]
    latencies = [results[m]["latency_ms"] for m in model_names]

    # Bar 1: F1-Score & Accuracy
    colors = ["#94A3B8", "#64748B", "#475569", "#2563EB"]
    colors = ["#94A3B8", "#64748B", "#475569", "#8B5CF6", "#2563EB"]
    bars1 = ax1.bar(short_names, f1_scores, color=colors, width=0.55, edgecolor="#0F172A", alpha=0.9)
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, h - 5, f"{h:.2f}%", ha="center", va="top", fontsize=10, fontweight="bold", color="#FFFFFF")
        ax1.text(bar.get_x() + bar.get_width()/2, h - 5, f"{h:.2f}%", ha="center", va="top", fontsize=9.5, fontweight="bold", color="#FFFFFF")
    ax1.set_title("So Sánh Độ Chính Xác (Macro F1-Score %)", fontsize=12, fontweight="bold", pad=12)
    ax1.set_ylabel("F1-Score (%)", fontsize=10, fontweight="bold")
    ax1.set_ylim(80, 100)
    ax1.grid(True, axis="y", linestyle="--", alpha=0.5)

    # Bar 2: Inference Latency (thấp hơn là tốt hơn)
    lat_colors = ["#10B981", "#EF4444", "#F59E0B", "#2563EB"]
    lat_colors = ["#10B981", "#EF4444", "#F59E0B", "#8B5CF6", "#2563EB"]
    bars2 = ax2.bar(short_names, latencies, color=lat_colors, width=0.55, edgecolor="#0F172A", alpha=0.9)
    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 0.1, f"{h:.2f} ms", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1E293B")
        ax2.text(bar.get_x() + bar.get_width()/2, h + 0.08, f"{h:.2f} ms", ha="center", va="bottom", fontsize=9.5, fontweight="bold", color="#1E293B")
    ax2.set_title("Độ Trễ Phân Loại Chuỗi (Inference Latency - ms)", fontsize=12, fontweight="bold", pad=12)
    ax2.set_ylabel("Thời gian xử lý (ms / chuỗi 30 frames)", fontsize=10, fontweight="bold")
    ax2.set_ylim(0, max(latencies) * 1.25)
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    out_dir = "/Users/khoi.nguyenhuu/enouvo/learning/computer-vision/driver-monitor/driver-monitoring-system/report_assets"
    out_path = os.path.join(out_dir, "chart_model_comparison.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\n✅ Đã lưu biểu đồ so sánh mô hình tại: {out_path}")

if __name__ == "__main__":
    run_experiment()

