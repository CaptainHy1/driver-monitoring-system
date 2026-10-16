# -*- coding: utf-8 -*-
"""
Generate diagrams focused on the Multimodal Temporal Transformer DMS.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

os.makedirs('paper/figures', exist_ok=True)
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9

def generate_fig1_architecture():
    fig, ax = plt.subplots(figsize=(10, 5.0), dpi=250)
    ax.axis('off')
    
    c_navy = '#1A365D'
    c_blue = '#2B4C7E'
    c_light_blue = '#EBF4FF'
    c_green = '#276749'
    c_light_green = '#F0FFF4'
    c_orange = '#DD6B20'
    c_light_orange = '#FFFAF0'
    c_purple = '#6B46C1'
    c_light_purple = '#FAF5FF'
    c_gray = '#4A5568'

    # Camera
    rect_cam = patches.FancyBboxPatch((0.02, 0.40), 0.11, 0.20, boxstyle="round,pad=0.02",
                                      facecolor=c_navy, edgecolor='none')
    ax.add_patch(rect_cam)
    ax.text(0.075, 0.53, "CAMERA CABIN\n(RGB / NIR)", color='white', ha='center', va='center', weight='bold', fontsize=8)
    ax.text(0.075, 0.44, "30 FPS | Full HD", color='#CBD5E0', ha='center', va='center', fontsize=7)

    # Arrow to M1
    ax.annotate('', xy=(0.16, 0.50), xytext=(0.13, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.5))

    # [M1] Preprocessor
    rect_m1 = patches.FancyBboxPatch((0.16, 0.35), 0.12, 0.30, boxstyle="round,pad=0.02",
                                     facecolor=c_light_blue, edgecolor=c_blue, lw=1.5)
    ax.add_patch(rect_m1)
    ax.text(0.22, 0.59, "[M1] Multi-ROI\nPreprocessor", color=c_navy, ha='center', va='center', weight='bold', fontsize=7.8)
    ax.text(0.22, 0.47, "Face: 224x224\nBody: 256x256\nCockpit: 640x640\nImageNet Norm", color=c_gray, ha='center', va='center', fontsize=6.8)

    # 3 Parallel Streams
    streams = [
        ("Nhánh Mặt [M2]", "MediaPipe Face Mesh (468 3D)\n+ Face ViT-Tiny -> f_face (256D)", c_light_green, c_green, 0.72),
        ("Nhánh Thân [M3-M4]", "YOLO-Pose (17 Khớp COCO)\n+ ST-GCN Đồ thị -> f_pose (256D)", c_light_orange, c_orange, 0.50),
        ("Nhánh Vật thể [M5]", "YOLO Cockpit Detector (Vật thể)\n+ Hand MLP -> f_hand (256D)", c_light_purple, c_purple, 0.28)
    ]

    for name, desc, bg, border, y_pos in streams:
        ax.annotate('', xy=(0.31, y_pos), xytext=(0.28, 0.50),
                    arrowprops=dict(facecolor=border, edgecolor=border, arrowstyle="->", lw=1.2))
        
        rect_stream = patches.FancyBboxPatch((0.31, y_pos - 0.08), 0.20, 0.16, boxstyle="round,pad=0.015",
                                             facecolor=bg, edgecolor=border, lw=1.2)
        ax.add_patch(rect_stream)
        ax.text(0.41, y_pos + 0.04, name, color=border, ha='center', va='center', weight='bold', fontsize=7.5)
        ax.text(0.41, y_pos - 0.03, desc, color=c_gray, ha='center', va='center', fontsize=6.5)

        ax.annotate('', xy=(0.54, 0.50), xytext=(0.51, y_pos),
                    arrowprops=dict(facecolor=border, edgecolor=border, arrowstyle="->", lw=1.2))

    # [M6] Cross-Modal Fusion
    rect_m6 = patches.FancyBboxPatch((0.54, 0.35), 0.13, 0.30, boxstyle="round,pad=0.02",
                                     facecolor=c_light_blue, edgecolor=c_blue, lw=1.5)
    ax.add_patch(rect_m6)
    ax.text(0.605, 0.59, "[M6] Cross-Modal\nAttention Fusion", color=c_navy, ha='center', va='center', weight='bold', fontsize=7.8)
    ax.text(0.605, 0.47, "Tokens: 3x256D\nQuery-Key-Value\nMa trận A (3x3)\nNén MLP -> 256D", color=c_gray, ha='center', va='center', fontsize=6.8)

    # Arrow to M7
    ax.annotate('', xy=(0.70, 0.50), xytext=(0.67, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.5))

    # [M7] Temporal Transformer (THE CENTRAL MODEL)
    rect_m7 = patches.FancyBboxPatch((0.70, 0.32), 0.16, 0.36, boxstyle="round,pad=0.02",
                                     facecolor='#FEFCBF', edgecolor='#B7791F', lw=2.0)
    ax.add_patch(rect_m7)
    ax.text(0.78, 0.63, "[M7] TEMPORAL\nTRANSFORMER", color='#744210', ha='center', va='center', weight='bold', fontsize=8.2)
    ax.text(0.78, 0.47, "Mô hình Trung tâm Cốt lõi\n• Cửa sổ trượt T=30 frames\n• [CLS] Token + Sinusoidal PE\n• 2 tầng Pre-LN Transformer\n• Phân loại 5 lớp (C0 - C4)\n• Sensor Grounding Fallback", color='#744210', ha='center', va='center', fontsize=6.6)

    # Arrow to M8 & M9
    ax.annotate('', xy=(0.89, 0.58), xytext=(0.86, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.2))
    ax.annotate('', xy=(0.89, 0.42), xytext=(0.86, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.2))

    # [M8] Alert Engine
    rect_m8 = patches.FancyBboxPatch((0.89, 0.52), 0.09, 0.16, boxstyle="round,pad=0.015",
                                     facecolor='#FED7D7', edgecolor='#C53030', lw=1.2)
    ax.add_patch(rect_m8)
    ax.text(0.935, 0.63, "[M8] Alert", color='#9B2C2C', ha='center', va='center', weight='bold', fontsize=7.2)
    ax.text(0.935, 0.56, "Leaky Decay\nMức 0 - 3\nBuzzer + Clip", color='#9B2C2C', ha='center', va='center', fontsize=6.2)

    # [M9] HUD
    rect_m9 = patches.FancyBboxPatch((0.89, 0.32), 0.09, 0.16, boxstyle="round,pad=0.015",
                                     facecolor='#C6F6D5', edgecolor='#2F855A', lw=1.2)
    ax.add_patch(rect_m9)
    ax.text(0.935, 0.43, "[M9] HUD", color='#22543D', ha='center', va='center', weight='bold', fontsize=7.2)
    ax.text(0.935, 0.36, "Font Unicode\nRisk Gauge\nJSONL Log", color='#22543D', ha='center', va='center', fontsize=6.2)

    plt.tight_layout()
    out_path = 'paper/figures/fig1_system_architecture.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

def generate_fig2_detectors():
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), dpi=250)
    
    # (a) YOLO-Pose stream for Body
    ax0 = axes[0]
    ax0.set_title("(a) Nhánh Thân [M3-M4]: YOLO-Pose + ST-GCN", fontsize=8.5, weight='bold', color='#1A365D')
    ax0.axis('off')
    
    rect_pose = patches.FancyBboxPatch((0.05, 0.55), 0.40, 0.35, boxstyle="round,pad=0.02",
                                       facecolor='#FFFAF0', edgecolor='#DD6B20', lw=1.5)
    ax0.add_patch(rect_pose)
    ax0.text(0.25, 0.77, "YOLO-Pose Detector\n(yolov8n-pose / yolov11n-pose)", ha='center', va='center', weight='bold', color='#C05621', fontsize=7.8)
    ax0.text(0.25, 0.64, "Trích xuất 17 khớp xương COCO\nTọa độ chuẩn hóa: (x, y, conf)", ha='center', va='center', color='#4A5568', fontsize=6.8)

    ax0.annotate('', xy=(0.55, 0.72), xytext=(0.45, 0.72),
                arrowprops=dict(facecolor='#DD6B20', edgecolor='#DD6B20', arrowstyle="->", lw=1.5))

    rect_stgcn = patches.FancyBboxPatch((0.55, 0.55), 0.40, 0.35, boxstyle="round,pad=0.02",
                                        facecolor='#FFFAF0', edgecolor='#DD6B20', lw=1.5)
    ax0.add_patch(rect_stgcn)
    ax0.text(0.75, 0.77, "Spatial-Temporal GCN\n(ST-GCN)", ha='center', va='center', weight='bold', color='#C05621', fontsize=7.8)
    ax0.text(0.75, 0.64, "Đồ thị 17 khớp x 30 frames\nTích chập không gian + thời gian", ha='center', va='center', color='#4A5568', fontsize=6.8)

    rect_out1 = patches.FancyBboxPatch((0.25, 0.12), 0.50, 0.28, boxstyle="round,pad=0.02",
                                       facecolor='#ED8936', edgecolor='none')
    ax0.add_patch(rect_out1)
    ax0.text(0.50, 0.26, "Vector Đặc trưng Tư thế Động học", ha='center', va='center', weight='bold', color='white', fontsize=8)
    ax0.text(0.50, 0.18, "f_pose in R^256", ha='center', va='center', color='white', fontsize=7.5)

    ax0.annotate('', xy=(0.50, 0.40), xytext=(0.50, 0.55),
                arrowprops=dict(facecolor='#C05621', edgecolor='#C05621', arrowstyle="->", lw=1.2))

    # (b) YOLO Object detector stream for Cockpit Objects & Hand
    ax1 = axes[1]
    ax1.set_title("(b) Nhánh Cabin [M5]: YOLO Detector + Hand MLP", fontsize=8.5, weight='bold', color='#1A365D')
    ax1.axis('off')
    
    rect_obj = patches.FancyBboxPatch((0.05, 0.55), 0.40, 0.35, boxstyle="round,pad=0.02",
                                      facecolor='#FAF5FF', edgecolor='#805AD5', lw=1.5)
    ax1.add_patch(rect_obj)
    ax1.text(0.25, 0.77, "YOLO Object Detector\n(yolov8n / yolov11 / yolov26)", ha='center', va='center', weight='bold', color='#6B46C1', fontsize=7.8)
    ax1.text(0.25, 0.64, "Phát hiện: cell phone, cup, bottle\nHộp bao BBox + Confidence", ha='center', va='center', color='#4A5568', fontsize=6.8)

    ax1.annotate('', xy=(0.55, 0.72), xytext=(0.45, 0.72),
                arrowprops=dict(facecolor='#805AD5', edgecolor='#805AD5', arrowstyle="->", lw=1.5))

    rect_hand = patches.FancyBboxPatch((0.55, 0.55), 0.40, 0.35, boxstyle="round,pad=0.02",
                                       facecolor='#FAF5FF', edgecolor='#805AD5', lw=1.5)
    ax1.add_patch(rect_hand)
    ax1.text(0.75, 0.77, "Hand Status Estimator\n+ Linear Projection MLP", ha='center', va='center', weight='bold', color='#6B46C1', fontsize=7.8)
    ax1.text(0.75, 0.64, "Liên kết cổ tay với vật thể\nCầm điện thoại, ly nước (64D)", ha='center', va='center', color='#4A5568', fontsize=6.8)

    rect_out2 = patches.FancyBboxPatch((0.25, 0.12), 0.50, 0.28, boxstyle="round,pad=0.02",
                                       facecolor='#805AD5', edgecolor='none')
    ax1.add_patch(rect_out2)
    ax1.text(0.50, 0.26, "Vector Tương tác Bàn tay & Vật thể", ha='center', va='center', weight='bold', color='white', fontsize=8)
    ax1.text(0.50, 0.18, "f_hand in R^256", ha='center', va='center', color='white', fontsize=7.5)

    ax1.annotate('', xy=(0.50, 0.40), xytext=(0.50, 0.55),
                arrowprops=dict(facecolor='#6B46C1', edgecolor='#6B46C1', arrowstyle="->", lw=1.2))

    plt.tight_layout()
    out_path = 'paper/figures/fig2_detector_branches.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

def generate_fig5_temporal_core():
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=250)
    ax.axis('off')
    
    # Title
    ax.text(0.5, 0.95, "KIẾN TRÚC MÔ HÌNH HÓA CHUỖI THỜI GIAN TEMPORAL TRANSFORMER (MÔ HÌNH CỐT LÕI)",
            ha='center', va='center', weight='bold', color='#1A365D', fontsize=9)
    
    # 1. Input Sliding Window Tokens
    tokens = ['[CLS]', 'f^(t-29)', 'f^(t-28)', '...', 'f^(t-1)', 'f^(t)']
    x_positions = [0.08, 0.23, 0.38, 0.53, 0.68, 0.83]
    
    for x, tok in zip(x_positions, tokens):
        bg = '#CBD5E0' if tok == '[CLS]' else '#EBF4FF'
        border = '#2B6CB0' if tok == '[CLS]' else '#3182CE'
        rect = patches.FancyBboxPatch((x, 0.70), 0.10, 0.15, boxstyle="round,pad=0.01",
                                      facecolor=bg, edgecolor=border, lw=1.5)
        ax.add_patch(rect)
        ax.text(x + 0.05, 0.775, tok, ha='center', va='center', weight='bold', color='#1A365D', fontsize=7.8)
        
        # Positional Encoding arrow
        ax.annotate('', xy=(x + 0.05, 0.68), xytext=(x + 0.05, 0.58),
                    arrowprops=dict(facecolor='#805AD5', edgecolor='#805AD5', arrowstyle="->", lw=1))
        ax.text(x + 0.05, 0.54, "+ PE", ha='center', va='center', fontsize=6.8, color='#805AD5', weight='bold')

    # 2. Transformer Encoder Layers
    rect_enc = patches.FancyBboxPatch((0.08, 0.30), 0.85, 0.18, boxstyle="round,pad=0.02",
                                      facecolor='#FEFCBF', edgecolor='#B7791F', lw=2.0)
    ax.add_patch(rect_enc)
    ax.text(0.505, 0.42, "2 x Transformer Encoder Layers (Pre-LayerNorm)", ha='center', va='center', weight='bold', color='#744210', fontsize=8.5)
    ax.text(0.505, 0.34, "Multi-Head Self-Attention (4 Heads, d_head=64) + MLP Feed-Forward (d_ff=512, GELU, Dropout 0.1)",
            ha='center', va='center', color='#744210', fontsize=7.2)

    # 3. Output arrow from [CLS]
    ax.annotate('', xy=(0.13, 0.18), xytext=(0.13, 0.30),
                arrowprops=dict(facecolor='#2B6CB0', edgecolor='#2B6CB0', arrowstyle="->", lw=1.5))
    ax.text(0.13, 0.24, "z_cls (256D)", ha='right', va='center', color='#2B6CB0', fontsize=7.2, weight='bold')

    # 4. Classification Head
    rect_cls = patches.FancyBboxPatch((0.18, 0.06), 0.40, 0.18, boxstyle="round,pad=0.015",
                                      facecolor='#C6F6D5', edgecolor='#22543D', lw=1.5)
    ax.add_patch(rect_cls)
    ax.text(0.38, 0.18, "Linear Classification Head (256D -> 5D)", ha='center', va='center', weight='bold', color='#22543D', fontsize=8)
    ax.text(0.38, 0.10, "Softmax -> P(C0), P(C1), P(C2), P(C3), P(C4)", ha='center', va='center', color='#22543D', fontsize=7.2)

    # 5. Sensor Grounding Fallback
    rect_fb = patches.FancyBboxPatch((0.62, 0.06), 0.31, 0.18, boxstyle="round,pad=0.015",
                                     facecolor='#FED7D7', edgecolor='#9B2C2C', lw=1.5)
    ax.add_patch(rect_fb)
    ax.text(0.775, 0.18, "Sensor Grounding Fallback", ha='center', va='center', weight='bold', color='#9B2C2C', fontsize=8)
    ax.text(0.775, 0.10, "Nếu conf < 0.65 -> Neo theo\nMediaPipe / YOLO (Chống báo giả)", ha='center', va='center', color='#9B2C2C', fontsize=6.8)

    plt.tight_layout()
    out_path = 'paper/figures/fig5_temporal_core.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

if __name__ == '__main__':
    generate_fig1_architecture()
    generate_fig2_detectors()
    generate_fig5_temporal_core()
    print("Core diagrams generated successfully!")
