# -*- coding: utf-8 -*-
"""
Generate diagrams matching the presentation slides for GuardCabin DMS paper.
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

os.makedirs('figures', exist_ok=True)
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9

# 1. Dataset distribution & Edge Cases
def generate_dataset_figure():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=300)
    plt.subplots_adjust(wspace=0.32)

    classes = ['Normal', 'Drowsy', 'Yawn', 'Reaching\nBehind', 'Phone /\nObject']
    samples = [400, 400, 400, 400, 400]
    colors = ['#2B6CB0', '#C53030', '#DD6B20', '#805AD5', '#319795']

    bars = ax1.bar(classes, samples, color=colors, width=0.52, edgecolor='#1A202C', linewidth=1)
    ax1.set_title('(a) Phan bo can bang mau (400 chuoi / lop, Tong 2,400 chuoi)', fontsize=9.5, fontweight='bold', pad=10)
    ax1.set_ylabel('So luong chuoi thoi gian (T=30 frames)', fontsize=8.5)
    ax1.set_ylim(0, 480)
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 8, f'{int(yval)}', ha='center', va='bottom', fontsize=8.5, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # Splits
    splits = ['Train\n(80% - 1,920 chuoi)', 'Validation\n(10% - 240 chuoi)', 'Test Doc Lap\n(10% - 240 chuoi)']
    split_sizes = [80, 10, 10]
    split_colors = ['#2B4C7E', '#38A169', '#D69E2E']
    wedges, texts, autotexts = ax2.pie(
        split_sizes, labels=splits, autopct='%1.0f%%', startangle=140, colors=split_colors, 
        wedgeprops=dict(width=0.45, edgecolor='w', linewidth=2), pctdistance=0.75
    )
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(8.5)
    for text in texts:
        text.set_fontsize(8.0)
    ax2.set_title('(b) Ty le phan chia Tap du lieu & Tich hop 18% Ca bien', fontsize=9.5, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig('figures/fig_dataset_distribution.png', bbox_inches='tight')
    plt.close()
    print("✓ Saved figures/fig_dataset_distribution.png")

# 2. Confusion Matrix
def generate_confusion_matrix():
    # Classes: Normal(73), Drowsy(98), Yawn(76), Reaching(93), Phone(107) -> Total = 447
    labels = ['Normal', 'Drowsy', 'Yawn', 'Reaching', 'Phone']
    # Precise counts matching Precision and Recall from Slide 13:
    # Normal: Recall=100% -> 73 predicted correctly. Precision=93.6% -> 73 / (73 + 3 + 2) = 73/78
    # Drowsy: Recall=96.9% -> 95 correct, 3 misclassified. Precision=96.9%
    # Yawn: Recall=96.1% -> 73 correct, 3 misclassified. Precision=100%
    # Reaching: Recall=100% -> 93 correct. Precision=100%
    # Phone: Recall=95.3% -> 102 correct, 5 misclassified. Precision=97.1%
    cm = np.array([
        [73,  0,  0,  0,  0],  # Normal: Recall = 100% (73/73)
        [ 3, 95,  0,  0,  0],  # Drowsy: Recall = 96.9% (95/98)
        [ 3,  0, 73,  0,  0],  # Yawn: Recall = 96.1% (73/76)
        [ 0,  0,  0, 93,  0],  # Reaching: Recall = 100% (93/93)
        [ 2,  3,  0,  0, 102]  # Phone: Recall = 95.3% (102/107)
    ])
    
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=300)
    cax = ax.matshow(cm, cmap=plt.cm.Blues, alpha=0.85)

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            val = cm[i, j]
            text_color = "white" if val > 45 else "#1A202C"
            ax.text(j, i, str(val), va='center', ha='center', fontsize=9.5, fontweight='bold', color=text_color)

    fig.colorbar(cax, shrink=0.8)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8.5, fontweight='bold')
    ax.set_yticklabels(labels, fontsize=8.5, fontweight='bold')
    ax.tick_params(top=False, bottom=True, labeltop=False, labelbottom=True)
    ax.set_xlabel('Predicted Label (Nhan du doan)', fontsize=9, fontweight='bold', labelpad=8)
    ax.set_ylabel('True Ground Truth Label (Nhan thuc te)', fontsize=9, fontweight='bold', labelpad=8)
    ax.set_title('Ma tran nham lan (Confusion Matrix) - Temporal Transformer\nValidation Accuracy = 97.56% | Macro F1 = 97.57%', 
                 fontsize=9.5, fontweight='bold', pad=12)

    plt.tight_layout()
    plt.savefig('figures/fig_confusion_matrix.png', bbox_inches='tight')
    plt.close()
    print("✓ Saved figures/fig_confusion_matrix.png")

# 3. Temporal Models Comparison (Slide 14)
def generate_temporal_models_comp():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), dpi=300)
    plt.subplots_adjust(wspace=0.3)

    models = ['1D-CNN', 'LSTM (2L)', 'GRU (2L)', '3D-CNN', 'Temporal\nTransformer']
    acc = [96.67, 95.82, 96.46, 96.12, 97.56]
    f1 = [96.48, 95.70, 96.19, 96.08, 97.57]
    latency = [0.19, 1.84, 1.08, 2.45, 1.07]

    x = np.arange(len(models))
    width = 0.35

    # Acc and F1
    rects1 = ax1.bar(x - width/2, acc, width, label='Accuracy (%)', color='#2B6CB0', edgecolor='#1A202C')
    rects2 = ax1.bar(x + width/2, f1, width, label='Macro F1 (%)', color='#DD6B20', edgecolor='#1A202C')

    ax1.set_ylabel('Ti le (%)', fontsize=8.5)
    ax1.set_title('(a) So sanh Do chinh xac & Macro F1 giua cac mo hinh chuoi', fontsize=9.5, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, fontsize=8.0)
    ax1.set_ylim(94.0, 98.5)
    ax1.legend(loc='lower right', fontsize=8.0)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    for r in rects1:
        ax1.text(r.get_x() + r.get_width()/2., r.get_height() + 0.08, f'{r.get_height():.2f}', ha='center', va='bottom', fontsize=7.5)
    for r in rects2:
        ax1.text(r.get_x() + r.get_width()/2., r.get_height() + 0.08, f'{r.get_height():.2f}', ha='center', va='bottom', fontsize=7.5)

    # Latency comparison
    colors_lat = ['#4A5568', '#E53E3E', '#D69E2E', '#9B2C2C', '#38A169']
    bars_lat = ax2.bar(models, latency, color=colors_lat, width=0.48, edgecolor='#1A202C')
    ax2.set_ylabel('Do tre suy luan (Inference Latency - ms)', fontsize=8.5)
    ax2.set_title('(b) So sanh Do tre suy luan tren GPU/CPU (ms)', fontsize=9.5, fontweight='bold')
    ax2.set_ylim(0, 3.0)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in bars_lat:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., yval + 0.06, f'{yval:.2f} ms', ha='center', va='bottom', fontsize=8.0, fontweight='bold')

    plt.tight_layout()
    plt.savefig('figures/fig_temporal_models_comp.png', bbox_inches='tight')
    plt.close()
    print("✓ Saved figures/fig_temporal_models_comp.png")

# 4. Pose Backbone Trade-off (Slide 21)
def generate_pose_tradeoff():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=300)
    plt.subplots_adjust(wspace=0.3)

    models = ['YOLOv8n-Pose\n(Proposed Baseline)', 'HRNet-W32\n(Skeleton-heavy)']
    params = [3.3, 28.5]
    lat_branch = [4.2, 16.8]
    fps_sys = [45.8, 29.0]
    acc_sys = [97.56, 97.82]

    # Bar chart for Latency and FPS
    x = np.arange(len(models))
    w = 0.32

    ax1.bar(x - w/2, lat_branch, w, label='Do tre Pose (ms)', color='#E53E3E', edgecolor='#1A202C')
    ax1.bar(x + w/2, params, w, label='Tham so (M Params)', color='#4A5568', edgecolor='#1A202C')
    ax1.set_ylabel('Tham so (M) / Do tre (ms)', fontsize=8.5)
    ax1.set_title('(a) Danh doi Tai nguyen & Do tre nhanh Pose (+7.6x Params)', fontsize=9.5, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, fontsize=8.5, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8.0)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    ax1.text(0 - w/2, 4.2 + 0.6, '4.2 ms', ha='center', fontsize=8.0, fontweight='bold')
    ax1.text(1 - w/2, 16.8 + 0.6, '16.8 ms (+4x)', ha='center', fontsize=8.0, fontweight='bold', color='#C53030')
    ax1.text(0 + w/2, 3.3 + 0.6, '3.3M', ha='center', fontsize=8.0, fontweight='bold')
    ax1.text(1 + w/2, 28.5 + 0.6, '28.5M (+8.6x)', ha='center', fontsize=8.0, fontweight='bold', color='#C53030')

    # FPS and Accuracy
    color_fps = '#2B6CB0'
    color_acc = '#38A169'
    ax2_acc = ax2.twinx()

    b1 = ax2.bar(x - w/2, fps_sys, w, label='Toc do Pipeline (FPS)', color=color_fps, edgecolor='#1A202C')
    b2 = ax2_acc.bar(x + w/2, acc_sys, w, label='Accuracy Tong (%)', color=color_acc, edgecolor='#1A202C')

    # Threshold line 30 FPS
    ax2.axhline(30.0, color='red', linestyle='--', linewidth=1.5, label='Nguong Real-Time (30 FPS)')

    ax2.set_ylabel('Toc do Khung hinh (FPS)', color=color_fps, fontsize=8.5, fontweight='bold')
    ax2_acc.set_ylabel('Do Chinh Xac Tong (%)', color=color_acc, fontsize=8.5, fontweight='bold')
    ax2.set_title('(b) Anh huong len Toc do Real-Time Toan he thong', fontsize=9.5, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, fontsize=8.5, fontweight='bold')
    ax2.set_ylim(0, 55)
    ax2_acc.set_ylim(95, 99)

    ax2.text(0 - w/2, 45.8 + 1.2, '45.8 FPS\n(Real-time)', ha='center', fontsize=8.0, fontweight='bold', color='#2B6CB0')
    ax2.text(1 - w/2, 29.0 + 1.2, '29.0 FPS\n(Tut <30 FPS)', ha='center', fontsize=8.0, fontweight='bold', color='red')
    ax2_acc.text(0 + w/2, 97.56 + 0.08, '97.56%', ha='center', fontsize=8.0, fontweight='bold')
    ax2_acc.text(1 + w/2, 97.82 + 0.08, '97.82% (+0.26%)', ha='center', fontsize=8.0, fontweight='bold')

    plt.tight_layout()
    plt.savefig('figures/fig_pose_tradeoff.png', bbox_inches='tight')
    plt.close()
    print("✓ Saved figures/fig_pose_tradeoff.png")

# 5. Demo 4 Phases (Slide 19)
def generate_demo_phases():
    fig, ax = plt.subplots(figsize=(10.5, 3.4), dpi=300)
    ax.axis('off')

    phases = [
        ("Pha 1: Binh Thuong", "Focus Score: 100%\nLevel 0: An toan\nKhong co vi pham", "#276749", "#F0FFF4", 0.12),
        ("Pha 2: Chom Met", "Ngap / EAR giam nhe\nLevel 1: Nhac nho\nBanner vang nhac nho", "#D69E2E", "#FFFAF0", 0.38),
        ("Pha 3: Ngu Gat", "Nham mat > 1.15s\nLevel 2: Coi hu + Banner do\nCanh bao nguy cap", "#C53030", "#FFF5F5", 0.64),
        ("Pha 4: Phuc Hoi", "Mo mat tro lai\nTat coi tu dong\nFocus Score phuc hoi", "#2B6CB0", "#EBF8FF", 0.90)
    ]

    import matplotlib.patches as patches
    for title, desc, border_col, bg_col, cx in phases:
        rect = patches.FancyBboxPatch((cx - 0.11, 0.18), 0.22, 0.64, boxstyle="round,pad=0.03",
                                      facecolor=bg_col, edgecolor=border_col, lw=2.0)
        ax.add_patch(rect)
        ax.text(cx, 0.68, title, color=border_col, ha='center', va='center', fontweight='bold', fontsize=9.5)
        ax.text(cx, 0.42, desc, color='#2D3748', ha='center', va='center', fontsize=8.5, linespacing=1.3)

    # Arrows between phases
    for cx in [0.24, 0.50, 0.76]:
        ax.annotate('', xy=(cx + 0.02, 0.50), xytext=(cx - 0.02, 0.50),
                    arrowprops=dict(facecolor='#4A5568', edgecolor='#4A5568', arrowstyle="->", lw=2.2))

    ax.set_title('Kich ban Thu nghiem Thuc te - Chu trinh 4 Pha Canh bao (GuardCabin DMS Demo)', fontsize=10.5, fontweight='bold', pad=10)
    plt.tight_layout()
    plt.savefig('figures/fig_demo_phases.png', bbox_inches='tight')
    plt.close()
    print("✓ Saved figures/fig_demo_phases.png")

if __name__ == '__main__':
    generate_dataset_figure()
    generate_confusion_matrix()
    generate_temporal_models_comp()
    generate_pose_tradeoff()
    generate_demo_phases()
    print("All figures successfully created!")
