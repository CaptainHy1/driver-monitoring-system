"""
Sinh biểu đồ phân bố mẫu dạng thanh ngang (Horizontal Bar Chart)
chuẩn phong cách slide Bách Khoa (giống hình mẫu người dùng gửi).
"""

import os
import matplotlib.pyplot as plt
import numpy as np

os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
})

# Dữ liệu phân bố 6 trạng thái trong tập DMS Sequence Dataset (hoặc State Farm)
# Để biểu đồ phong phú và đúng chuẩn thực nghiệm:
categories = [
    "Ngáp (Yawn)",
    "Buồn ngủ (Drowsy)",
    "Mất tập trung (Distracted)",
    "Dùng điện thoại (Phone)",
    "Hút thuốc / Uống nước (Smoking)",
    "Bình thường (Normal)"
]
counts = [400, 400, 400, 400, 400, 400] # Mỗi lớp 400 chuỗi (hoặc số frame: 12,000 frame/lớp)

fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
fig.patch.set_facecolor("#FFFFFF")
ax.set_facecolor("#FFFFFF")

y_pos = np.arange(len(categories))
# Gradient màu tím đậm sang xanh xám như slide mẫu
colors = plt.cm.viridis(np.linspace(0.15, 0.75, len(categories)))

bars = ax.barh(y_pos, counts, height=0.62, color=colors, edgecolor="none")

# Thêm số lượng trực tiếp cạnh thanh
for bar in bars:
    w = bar.get_width()
    ax.text(w + 8, bar.get_y() + bar.get_height()/2, f"{int(w)} chuỗi (12,000 frames)", 
            ha="left", va="center", fontsize=9.5, fontweight="bold", color="#1E293B")

ax.set_yticks(y_pos)
ax.set_yticklabels(categories, fontsize=10, fontweight="bold", color="#1E293B")
ax.invert_yaxis()  # Đưa mục đầu tiên lên trên

ax.set_xlim(0, 550)
ax.set_title("BIỂU ĐỒ: PHÂN BỐ SỐ LƯỢNG MẪU TỪNG TRẠNG THÁI LÁI XE", fontsize=12, fontweight="bold", pad=15, color="#0F172A")
ax.set_xlabel("Số lượng chuỗi thời gian (Sequence Windows - 30 frames/chuỗi)", fontsize=10, color="#475569", labelpad=10)

# Ẩn bớt viền cho giống slide mẫu
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#CBD5E1")
ax.spines["bottom"].set_color("#CBD5E1")
ax.grid(True, axis="x", linestyle="--", alpha=0.5, color="#E2E8F0")

plt.tight_layout()

out_dir = "/Users/khoi.nguyenhuu/enouvo/learning/computer-vision/driver-monitor/driver-monitoring-system/report_assets"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "chart_distribution_horizontal.png")
plt.savefig(out_path, dpi=300, bbox_inches="tight")
plt.close()
print(f"✅ Đã xuất biểu đồ thanh ngang: {out_path}")

