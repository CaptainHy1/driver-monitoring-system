"""
Script sinh biểu đồ trực quan hóa dữ liệu (Dataset Overview & Feature Profile)
phục vụ trực tiếp cho Slide Báo Cáo về Dataset.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 1.2,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
})

fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=300)
fig.patch.set_facecolor("#FFFFFF")

# -------------------------------------------------------------
# 1. Biểu đồ phân bổ mẫu theo 6 lớp & Tập Train/Val
# -------------------------------------------------------------
ax1 = axes[0]
classes = ["Normal\n(Bình thường)", "Drowsy\n(Buồn ngủ)", "Yawn\n(Ngáp)", 
           "Distracted\n(Lơ đãng)", "Phone\n(Điện thoại)", "Smoking\n(Hút/Uống)"]
x = np.arange(len(classes))
width = 0.38

# Mỗi lớp 400 mẫu: Train 320 (80%), Val 80 (20%)
train_counts = [320, 320, 320, 320, 320, 320]
val_counts = [80, 80, 80, 80, 80, 80]

bars1 = ax1.bar(x - width/2, train_counts, width, label="Tập Huấn Luyện (Train - 80%)", color="#2563EB", edgecolor="#1D4ED8", alpha=0.9, zorder=3)
bars2 = ax1.bar(x + width/2, val_counts, width, label="Tập Kiểm Thử (Val - 20%)", color="#10B981", edgecolor="#059669", alpha=0.9, zorder=3)

for bar in bars1:
    h = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, h + 6, f"{int(h)}", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1E3A8A")

for bar in bars2:
    h = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, h + 6, f"{int(h)}", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#065F46")

ax1.set_title("Phân Bổ Cân Bằng 6 Lớp Dữ Liệu (Tổng: 2,400 Chuỗi)", fontsize=13, fontweight="bold", pad=14, color="#0F172A")
ax1.set_ylabel("Số lượng chuỗi thời gian (Sequence Windows)", fontsize=11, fontweight="bold", color="#334155")
ax1.set_xticks(x)
ax1.set_xticklabels(classes, fontsize=10, fontweight="bold", color="#1E293B")
ax1.set_ylim(0, 390)
ax1.grid(True, axis="y")
ax1.legend(frameon=True, facecolor="#F8FAFC", edgecolor="#E2E8F0", loc="upper right", fontsize=10)

# -------------------------------------------------------------
# 2. Biểu đồ trực quan hóa đặc trưng sinh trắc học thời gian (EAR & MAR)
# -------------------------------------------------------------
ax2 = axes[1]
t = np.linspace(0, 1.0, 30) # 30 frames tương đương 1.0 giây (30 FPS)

# Dữ liệu minh họa 3 trạng thái
# 1. Normal: EAR ~ 0.32 với 1 cái chớp mắt tự nhiên 3 frames, MAR ổn định ~0.15
normal_ear = np.full(30, 0.31) + np.random.normal(0, 0.008, 30)
normal_ear[12:15] = [0.18, 0.10, 0.16] # chớp mắt
normal_mar = np.full(30, 0.15) + np.random.normal(0, 0.006, 30)

# 2. Drowsy: EAR sụp mí xuống dưới 0.18 kéo dài, MAR ~0.18
drowsy_ear = np.linspace(0.24, 0.10, 30) + np.random.normal(0, 0.008, 30)

# 3. Yawn: MAR đỉnh hình chuông vượt 0.65, EAR hơi híp ~0.22
gauss_t = np.linspace(-2, 2, 30)
yawn_mar = 0.16 + (0.68 - 0.16) * np.exp(-gauss_t**2)

ax2.plot(t, normal_ear, color="#2563EB", linewidth=2.2, label="Normal: Độ mở mắt EAR (Chớp mắt tự nhiên)", linestyle="-")
ax2.plot(t, drowsy_ear, color="#DC2626", linewidth=2.4, label="Drowsy: Mắt sụp mí liên tục (EAR < 0.20)", linestyle="-.")
ax2.plot(t, yawn_mar, color="#F59E0B", linewidth=2.4, label="Yawn: Độ mở miệng MAR (Đỉnh ngáp > 0.52)", linestyle="--")

# Ngưỡng kỹ thuật
ax2.axhline(0.20, color="#EF4444", linestyle=":", linewidth=1.5, alpha=0.8, label="Ngưỡng sụp mí (EAR Thresh = 0.20)")
ax2.axhline(0.52, color="#D97706", linestyle=":", linewidth=1.5, alpha=0.8, label="Ngưỡng chớm ngáp (MAR Thresh = 0.52)")

ax2.set_title("Trực Quan Hóa Chuỗi 12D: Biến Thiên Tín Hiệu Theo Thời Gian (30 Frames ~ 1s)", fontsize=13, fontweight="bold", pad=14, color="#0F172A")
ax2.set_xlabel("Thời gian quan sát (Giây - tương ứng 30 frames)", fontsize=11, fontweight="bold", color="#334155")
ax2.set_ylabel("Giá trị tỷ lệ chuẩn hóa (Ratio)", fontsize=11, fontweight="bold", color="#334155")
ax2.set_ylim(0.05, 0.75)
ax2.grid(True)
ax2.legend(frameon=True, facecolor="#F8FAFC", edgecolor="#E2E8F0", loc="upper right", fontsize=9.5)

plt.tight_layout(pad=2.5)

out_dir = "/Users/khoi.nguyenhuu/enouvo/learning/computer-vision/driver-monitor/driver-monitoring-system/report_assets"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "chart_dataset_overview.png")
plt.savefig(out_path, dpi=300, bbox_inches="tight")
plt.close()
print(f"✅ Đã xuất biểu đồ Dataset thành công: {out_path}")

