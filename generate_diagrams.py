# -*- coding: utf-8 -*-
"""
Generate professional academic figures for the Multimodal DMS research paper.
Outputs high-res PNG files into paper/figures/
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
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=250)
    ax.axis('off')
    
    # Colors
    c_blue = '#2B4C7E'
    c_light_blue = '#EBF4FF'
    c_navy = '#1A365D'
    c_green = '#276749'
    c_light_green = '#F0FFF4'
    c_orange = '#DD6B20'
    c_light_orange = '#FFFAF0'
    c_purple = '#6B46C1'
    c_light_purple = '#FAF5FF'
    c_gray = '#4A5568'
    c_light_gray = '#F7FAFC'

    # 1. Camera Input
    rect_cam = patches.FancyBboxPatch((0.02, 0.40), 0.12, 0.20, boxstyle="round,pad=0.02",
                                      facecolor=c_navy, edgecolor='none')
    ax.add_patch(rect_cam)
    ax.text(0.08, 0.53, "CAMERA CABIN\n(RGB / NIR)", color='white', ha='center', va='center', weight='bold', fontsize=8.5)
    ax.text(0.08, 0.44, "30 FPS | Full HD", color='#CBD5E0', ha='center', va='center', fontsize=7.5)

    # Arrow to M1
    ax.annotate('', xy=(0.18, 0.50), xytext=(0.14, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.5))

    # 2. [M1] Preprocessor
    rect_m1 = patches.FancyBboxPatch((0.18, 0.35), 0.13, 0.30, boxstyle="round,pad=0.02",
                                     facecolor=c_light_blue, edgecolor=c_blue, lw=1.5)
    ax.add_patch(rect_m1)
    ax.text(0.245, 0.59, "[M1] Multi-ROI\nPreprocessor", color=c_navy, ha='center', va='center', weight='bold', fontsize=8)
    ax.text(0.245, 0.48, "• Face: 224x224\n• Body: 256x256\n• Cockpit: 640x640\nImageNet Norm", color=c_gray, ha='center', va='center', fontsize=7)

    # 3 Parallel Streams
    streams = [
        ("Face Stream [M2]", "MediaPipe Face Mesh (468 3D)\n+ Face ViT-Tiny (4 Layers)\nBiometrics: EAR, MAR, Gaze", c_light_green, c_green, 0.72),
        ("Body Stream [M3-M4]", "YOLO-Pose (17 Keypoints)\n+ ST-GCN (Spatial-Temporal)\nSkeletal Dynamics over T=30", c_light_orange, c_orange, 0.50),
        ("Cockpit Stream [M5]", "Cockpit Detector (YOLO/DETR)\n+ Hand Interaction MLP\nPhone, Cup, Bottle, Food", c_light_purple, c_purple, 0.28)
    ]

    for name, desc, bg, border, y_pos in streams:
        # Arrow from M1 to Stream
        ax.annotate('', xy=(0.35, y_pos), xytext=(0.31, 0.50),
                    arrowprops=dict(facecolor=border, edgecolor=border, arrowstyle="->", lw=1.2))
        
        rect_stream = patches.FancyBboxPatch((0.35, y_pos - 0.08), 0.19, 0.16, boxstyle="round,pad=0.015",
                                             facecolor=bg, edgecolor=border, lw=1.2)
        ax.add_patch(rect_stream)
        ax.text(0.445, y_pos + 0.04, name, color=border, ha='center', va='center', weight='bold', fontsize=7.8)
        ax.text(0.445, y_pos - 0.03, desc, color=c_gray, ha='center', va='center', fontsize=6.8)

        # Arrow from Stream to Fusion
        ax.annotate('', xy=(0.58, 0.50), xytext=(0.54, y_pos),
                    arrowprops=dict(facecolor=border, edgecolor=border, arrowstyle="->", lw=1.2))

    # 4. [M6] Cross-Modal Fusion
    rect_m6 = patches.FancyBboxPatch((0.58, 0.35), 0.13, 0.30, boxstyle="round,pad=0.02",
                                     facecolor=c_light_blue, edgecolor=c_blue, lw=1.5)
    ax.add_patch(rect_m6)
    ax.text(0.645, 0.59, "[M6] Cross-Modal\nAttention Fusion", color=c_navy, ha='center', va='center', weight='bold', fontsize=8)
    ax.text(0.645, 0.47, "Tokens: 3 x 256D\nQuery-Key-Value\nAffinity A in R^(3x3)\nMLP Nén -> 256D", color=c_gray, ha='center', va='center', fontsize=7)

    # Arrow from Fusion to Temporal
    ax.annotate('', xy=(0.75, 0.50), xytext=(0.71, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.5))

    # 5. [M7] Temporal Transformer
    rect_m7 = patches.FancyBboxPatch((0.75, 0.35), 0.12, 0.30, boxstyle="round,pad=0.02",
                                     facecolor='#FEFCBF', edgecolor='#B7791F', lw=1.5)
    ax.add_patch(rect_m7)
    ax.text(0.81, 0.59, "[M7] Temporal\nTransformer", color='#744210', ha='center', va='center', weight='bold', fontsize=8)
    ax.text(0.81, 0.47, "Window T=30 frames\n[CLS] Token + PE\nPre-LN 2 Layers\nSensor Grounding\nFallback C0-C4", color='#744210', ha='center', va='center', fontsize=6.8)

    # Arrow to Alert & HUD
    ax.annotate('', xy=(0.90, 0.58), xytext=(0.87, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.2))
    ax.annotate('', xy=(0.90, 0.42), xytext=(0.87, 0.50),
                arrowprops=dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=1.2))

    # 6. [M8] Alert Engine
    rect_m8 = patches.FancyBboxPatch((0.90, 0.52), 0.09, 0.16, boxstyle="round,pad=0.015",
                                     facecolor='#FED7D7', edgecolor='#C53030', lw=1.2)
    ax.add_patch(rect_m8)
    ax.text(0.945, 0.63, "[M8] Alert", color='#9B2C2C', ha='center', va='center', weight='bold', fontsize=7.5)
    ax.text(0.945, 0.56, "Leaky Decay\nMức 0 - 3\nBuzzer + Clip", color='#9B2C2C', ha='center', va='center', fontsize=6.5)

    # 7. [M9] HUD & Log
    rect_m9 = patches.FancyBboxPatch((0.90, 0.32), 0.09, 0.16, boxstyle="round,pad=0.015",
                                     facecolor='#C6F6D5', edgecolor='#2F855A', lw=1.2)
    ax.add_patch(rect_m9)
    ax.text(0.945, 0.43, "[M9] HUD", color='#22543D', ha='center', va='center', weight='bold', fontsize=7.5)
    ax.text(0.945, 0.36, "Font Unicode\nRisk Gauge\nJSONL Log", color='#22543D', ha='center', va='center', fontsize=6.5)

    plt.tight_layout()
    out_path = 'paper/figures/fig1_system_architecture.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

def generate_fig5_biometrics():
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), dpi=250)
    
    # 1. EAR (Eye Aspect Ratio)
    ax0 = axes[0]
    ax0.set_title("(a) Chỉ số Mở Mắt EAR & PERCLOS", fontsize=8.5, weight='bold', color='#1A365D')
    t = np.linspace(0, 5, 200)
    # Simulated EAR with blinks and prolonged closure
    ear = 0.32 + 0.02 * np.sin(2 * np.pi * 0.5 * t)
    # normal blink at t=1.2s
    ear[(t >= 1.1) & (t <= 1.3)] = 0.08
    # drowsy closure at t >= 3.0s
    ear[t >= 3.0] = 0.07 + 0.02 * np.random.normal(0, 0.05, np.sum(t >= 3.0))
    ear = np.clip(ear, 0.05, 0.40)
    ax0.plot(t, ear, color='#2B6CB0', lw=1.8, label='EAR(t)')
    ax0.axhline(0.20, color='#E53E3E', ls='--', lw=1.2, label='Ngưỡng EAR=0.20')
    ax0.axvspan(3.0, 5.0, color='#FED7D7', alpha=0.5, label='Ngủ gật (Δt >= 1.5s)')
    ax0.set_xlabel("Thời gian (giây)", fontsize=7.5)
    ax0.set_ylabel("Giá trị EAR", fontsize=7.5)
    ax0.set_ylim(0, 0.45)
    ax0.legend(loc='lower left', fontsize=6.5)
    ax0.grid(True, ls=':', alpha=0.6)

    # 2. MAR (Mouth Aspect Ratio)
    ax1 = axes[1]
    ax1.set_title("(b) Độ Mở Miệng MAR & Latch Filter", fontsize=8.5, weight='bold', color='#1A365D')
    mar = 0.22 + 0.04 * np.sin(2 * np.pi * 1.5 * t)  # talking
    # yawning event from t=2.0 to 3.5s
    yawn_mask = (t >= 2.0) & (t <= 3.5)
    mar[yawn_mask] = 0.22 + 0.45 * np.sin(np.pi * (t[yawn_mask] - 2.0) / 1.5)
    ax1.plot(t, mar, color='#DD6B20', lw=1.8, label='MAR(t)')
    ax1.axhline(0.45, color='#E53E3E', ls='--', lw=1.2, label='Ngưỡng ngáp MAR=0.45')
    ax1.axvspan(2.6, 4.6, color='#FEEBC8', alpha=0.5, label='Latch Timer (2.0s)')
    ax1.set_xlabel("Thời gian (giây)", fontsize=7.5)
    ax1.set_ylabel("Giá trị MAR", fontsize=7.5)
    ax1.set_ylim(0.1, 0.75)
    ax1.legend(loc='upper right', fontsize=6.5)
    ax1.grid(True, ls=':', alpha=0.6)

    # 3. Gaze & Head Pitch
    ax2 = axes[2]
    ax2.set_title("(c) Hướng nhìn Gaze & Cúi đầu (Pitch)", fontsize=8.5, weight='bold', color='#1A365D')
    pitch = np.zeros_like(t) - 2.0  # looking straight
    # Looking down at phone from t=2.0 to 4.5s
    pitch[(t >= 2.0) & (t <= 4.5)] = -18.0 + 1.5 * np.sin(2 * np.pi * t[(t >= 2.0) & (t <= 4.5)])
    ax2.plot(t, pitch, color='#6B46C1', lw=1.8, label='Head Pitch (°)')
    ax2.axhline(-15.0, color='#E53E3E', ls='--', lw=1.2, label='Ngưỡng cúi Pitch=-15°')
    ax2.axvspan(2.0, 4.5, color='#E9D8FD', alpha=0.5, label='Cúi đầu nhìn máy')
    ax2.set_xlabel("Thời gian (giây)", fontsize=7.5)
    ax2.set_ylabel("Góc Pitch (độ)", fontsize=7.5)
    ax2.set_ylim(-25, 5)
    ax2.legend(loc='lower left', fontsize=6.5)
    ax2.grid(True, ls=':', alpha=0.6)

    plt.tight_layout()
    out_path = 'paper/figures/fig5_facial_biometrics.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

def generate_fig6_fusion():
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), dpi=250)
    
    # 1. Affinity Matrix Heatmap
    ax0 = axes[0]
    ax0.set_title("(a) Ma trận Tương tác Cross-Modal Attention", fontsize=8.5, weight='bold', color='#1A365D')
    # When phone is detected in hand and driver looks down
    A = np.array([
        [0.35, 0.25, 0.40],  # Face attends strongly to Hand
        [0.20, 0.30, 0.50],  # Pose attends strongly to Hand
        [0.45, 0.35, 0.20],  # Hand attends to Face & Pose
    ])
    cax = ax0.matshow(A, cmap='Blues', vmin=0, vmax=0.6)
    fig.colorbar(cax, ax=ax0, fraction=0.046, pad=0.04)
    labels = ['Face (Mặt)', 'Pose (Thân)', 'Hand (Tay/Vật)']
    ax0.set_xticks(range(3))
    ax0.set_yticks(range(3))
    ax0.set_xticklabels(labels, fontsize=7.5)
    ax0.set_yticklabels(labels, fontsize=7.5)
    for i in range(3):
        for j in range(3):
            ax0.text(j, i, f"{A[i, j]:.2f}", ha='center', va='center', color='black' if A[i, j] < 0.38 else 'white', weight='bold', fontsize=8)

    # 2. Temporal Sequence Sliding Window
    ax1 = axes[1]
    ax1.set_title("(b) Cửa sổ Trượt Temporal Transformer (T=30)", fontsize=8.5, weight='bold', color='#1A365D')
    ax1.axis('off')
    
    # Draw sliding window boxes
    ax1.text(0.5, 0.88, "Chuỗi thời gian: T = 30 frames (~1.0s tại 30 FPS)", ha='center', va='center', weight='bold', color='#2B4C7E', fontsize=8)
    
    colors = ['#BEE3F8', '#C6F6D5', '#FED7D7', '#FEFCBF']
    tokens = ['[CLS]', 'f^(t-29)', 'f^(t-28)', '...', 'f^(t-1)', 'f^(t)']
    positions = [0.06, 0.22, 0.38, 0.54, 0.70, 0.86]
    
    for pos, tok in zip(positions, tokens):
        bg = '#CBD5E0' if tok == '[CLS]' else '#E2E8F0'
        bc = '#2B6CB0' if tok == '[CLS]' else '#4A5568'
        rect = patches.FancyBboxPatch((pos, 0.56), 0.11, 0.18, boxstyle="round,pad=0.01",
                                      facecolor=bg, edgecolor=bc, lw=1.2)
        ax1.add_patch(rect)
        ax1.text(pos + 0.055, 0.65, tok, ha='center', va='center', fontsize=7.5, weight='bold', color=bc)
        # Positional Encoding arrow
        ax1.annotate('', xy=(pos + 0.055, 0.54), xytext=(pos + 0.055, 0.44),
                    arrowprops=dict(facecolor='#805AD5', edgecolor='#805AD5', arrowstyle="->", lw=1))
        ax1.text(pos + 0.055, 0.38, "PE", ha='center', va='center', fontsize=7, color='#805AD5')
        
    rect_enc = patches.FancyBboxPatch((0.06, 0.12), 0.88, 0.18, boxstyle="round,pad=0.015",
                                      facecolor='#FEFCBF', edgecolor='#B7791F', lw=1.5)
    ax1.add_patch(rect_enc)
    ax1.text(0.50, 0.21, "2 x Transformer Encoder Layers (Multi-Head Self-Attention + FFN)", ha='center', va='center', weight='bold', fontsize=7.8, color='#744210')

    plt.tight_layout()
    out_path = 'paper/figures/fig6_fusion_temporal.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

def generate_fig7_alert_leaky():
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.3), dpi=250)
    
    # 1. Leaky Decay Dynamics
    ax0 = axes[0]
    ax0.set_title("(a) Cơ chế Tích lũy Vi phạm & Leaky Decay", fontsize=8.5, weight='bold', color='#1A365D')
    t = np.linspace(0, 6, 300)
    # Binary timer vs Leaky Decay timer
    # Driver cheats: uses phone from 0 to 1.3s, looks up 1.3-1.6s, uses phone 1.6-2.9s...
    t_binary = np.zeros_like(t)
    t_leaky = np.zeros_like(t)
    
    dt = t[1] - t[0]
    cur_bin = 0.0
    cur_leak = 0.0
    
    for i in range(len(t)):
        ti = t[i]
        # Distraction active: [0, 1.3] and [1.6, 3.2] and [3.6, 5.0]
        active = (0 <= ti <= 1.3) or (1.6 <= ti <= 3.2) or (3.6 <= ti <= 5.0)
        if active:
            cur_bin += dt
            cur_leak += dt
        else:
            cur_bin = 0.0  # binary resets immediately
            cur_leak = max(0.0, cur_leak - 1.8 * dt)  # leaky decay
        t_binary[i] = cur_bin
        t_leaky[i] = cur_leak
        
    ax0.plot(t, t_binary, color='#A0AEC0', ls=':', lw=1.5, label='Bộ đếm nhị phân (Bị qua mặt)')
    ax0.plot(t, t_leaky, color='#E53E3E', lw=2.0, label='Đề xuất: Leaky Decay (Chống lách)')
    ax0.axhline(1.5, color='#DD6B20', ls='--', lw=1.2, label='Ngưỡng cảnh báo Mức 2 (1.5s)')
    ax0.set_xlabel("Thời gian (giây)", fontsize=7.5)
    ax0.set_ylabel("Thời gian vi phạm tích lũy (s)", fontsize=7.5)
    ax0.set_ylim(0, 3.0)
    ax0.legend(loc='upper left', fontsize=6.8)
    ax0.grid(True, ls=':', alpha=0.6)

    # 2. Risk Gauge & Alert Matrix Levels
    ax1 = axes[1]
    ax1.set_title("(b) Phân cấp 4 Mức Cảnh báo & Risk Gauge", fontsize=8.5, weight='bold', color='#1A365D')
    levels = ['Mức 0\n(Safe)', 'Mức 1\n(Reminder)', 'Mức 2\n(Warning)', 'Mức 3\n(Critical)']
    colors = ['#38A169', '#D69E2E', '#DD6B20', '#E53E3E']
    scores = [20, 55, 80, 98]
    bars = ax1.bar(levels, scores, color=colors, width=0.55, edgecolor='#2D3748', lw=1)
    ax1.set_ylabel("Thanh đo Nguy cơ Distraction Risk (%)", fontsize=7.5)
    ax1.set_ylim(0, 115)
    for bar, score in zip(bars, scores):
        y = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, y + 2, f"{score}%", ha='center', va='bottom', weight='bold', fontsize=8)
    ax1.grid(axis='y', ls=':', alpha=0.6)

    plt.tight_layout()
    out_path = 'paper/figures/fig7_hud_alert_engine.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

def generate_fig8_latency():
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=250)
    models = ['YOLOv8n', 'YOLOv11n', 'YOLO26n', 'RT-DETRv2-S']
    fps_orin = [52.3, 64.1, 78.4, 42.5]
    lat_gpu = [5.8, 4.6, 3.9, 8.2]
    
    x = np.arange(len(models))
    width = 0.35
    
    rects1 = ax.bar(x - width/2, fps_orin, width, label='FPS (Jetson Orin Nano)', color='#2B6CB0', edgecolor='#1A365D')
    ax2 = ax.twinx()
    rects2 = ax2.bar(x + width/2, lat_gpu, width, label='Độ trễ GPU TensorRT (ms)', color='#DD6B20', edgecolor='#7B341E')
    
    ax.set_ylabel('Tốc độ khung hình (FPS)', color='#2B6CB0', fontsize=8, weight='bold')
    ax2.set_ylabel('Độ trễ suy luận (ms)', color='#DD6B20', fontsize=8, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=8, weight='bold')
    ax.set_ylim(0, 100)
    ax2.set_ylim(0, 12)
    
    for r in rects1:
        h = r.get_height()
        ax.text(r.get_x() + r.get_width()/2, h + 1.5, f"{h:.1f}", ha='center', va='bottom', fontsize=7.5, weight='bold', color='#1A365D')
    for r in rects2:
        h = r.get_height()
        ax2.text(r.get_x() + r.get_width()/2, h + 0.2, f"{h:.1f}ms", ha='center', va='bottom', fontsize=7.5, weight='bold', color='#7B341E')
        
    ax.set_title("So sánh Tốc độ Khung hình (FPS) và Độ trễ Suy luận Trên Nền tảng Nhúng Ô tô", fontsize=8.5, weight='bold', color='#1A365D')
    ax.grid(axis='y', ls=':', alpha=0.5)
    plt.tight_layout()
    out_path = 'paper/figures/fig8_latency_fps_comparison.png'
    plt.savefig(out_path, dpi=250, bbox_inches='tight')
    plt.close()
    print(f"Generated: {out_path}")

if __name__ == '__main__':
    generate_fig1_architecture()
    generate_fig5_biometrics()
    generate_fig6_fusion()
    generate_fig7_alert_leaky()
    generate_fig8_latency()
    print("All diagrams generated successfully!")
