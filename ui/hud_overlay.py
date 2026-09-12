"""
Module giao diện Cyber HUD (Heads-Up Display) hiển thị thông số thời gian thực.
Thiết kế thẩm mỹ cao (Cyberpunk / Glassmorphism):
- Panel bán trong suốt (Alpha Blended Panels)
- Đồ thị sóng cuộn thời gian thực (Real-time Rolling Waveform) cho EAR & MAR
- Trục tọa độ 3D Head Pose (Pitch, Yaw, Roll)
- Thẻ trạng thái cảnh báo động (Pulsating Alert Badges)
- Đồng hồ đo Attention Score và Telemetry (FPS, Latency, Blinks/min)
"""

import os
import cv2
import numpy as np
from collections import deque
from PIL import Image, ImageDraw, ImageFont

from config import (
    COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_CYAN,
    COLOR_DARK_BG, COLOR_WHITE,
    EAR_DROWSY_THRESH, MAR_YAWN_THRESH,
    CLASS_VIETNAMESE, CLASS_HUD_LABELS
)

class HUDOverlay:
    def __init__(self, history_len=60):
        self.history_len = history_len
        self.ear_history = deque([0.3] * history_len, maxlen=history_len)
        self.mar_history = deque([0.15] * history_len, maxlen=history_len)
        self.pulse_frame = 0

        # Khởi tạo font chữ TrueType hỗ trợ tiếng Việt có dấu chuẩn đẹp
        self.banner_font = None
        font_candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/tahoma.ttf"
        ]
        for fp in font_candidates:
            if os.path.exists(fp):
                try:
                    self.banner_font = ImageFont.truetype(fp, 22)
                    break
                except Exception:
                    pass

    def _draw_transparent_rect(self, img, pt1, pt2, color, alpha=0.65):
        """Vẽ hình chữ nhật trong suốt (Glassmorphism card)"""
        x1, y1 = pt1
        x2, y2 = pt2
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        cv2.rectangle(img, (x1, y1), (x2, y2), (80, 80, 90), 1)

    def _draw_head_pose_axes(self, img, rot_vec, trans_vec, camera_matrix, length=50):
        """Vẽ trục tọa độ 3D đại diện cho hướng nhìn của đầu"""
        if rot_vec is None or trans_vec is None:
            return

        axis_3d = np.float32([
            [0, 0, 0],
            [length, 0, 0],     # Trục X - Đỏ (Pitch)
            [0, length, 0],     # Trục Y - Xanh lá (Yaw)
            [0, 0, length]      # Trục Z - Xanh dương (Roll)
        ])

        dist_coeffs = np.zeros((4, 1))
        imgpts, _ = cv2.projectPoints(axis_3d, rot_vec, trans_vec, camera_matrix, dist_coeffs)
        imgpts = np.int32(imgpts).reshape(-1, 2)

        p_origin = tuple(imgpts[0])
        p_x = tuple(imgpts[1])
        p_y = tuple(imgpts[2])
        p_z = tuple(imgpts[3])

        # Vẽ các trục tọa độ
        cv2.line(img, p_origin, p_x, (0, 0, 255), 2)   # X: Đỏ
        cv2.line(img, p_origin, p_y, (0, 255, 0), 2)   # Y: Xanh lá
        cv2.line(img, p_origin, p_z, (255, 100, 0), 2) # Z: Xanh dương

    def _draw_strip_chart(self, img, x, y, w, h):
        """Vẽ biểu đồ sóng thời gian thực cho EAR và MAR"""
        self._draw_transparent_rect(img, (x, y), (x + w, y + h), COLOR_DARK_BG, 0.75)
        
        # Tiêu đề biểu đồ
        cv2.putText(img, "WAVEFORM: EAR (CYAN) / MAR (ORANGE)", (x + 10, y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)

        # Đường tham chiếu ngưỡng (Threshold lines)
        ear_thresh_y = int(y + h - (EAR_DROWSY_THRESH / 0.6) * (h - 25))
        mar_thresh_y = int(y + h - (MAR_YAWN_THRESH / 1.0) * (h - 25))
        
        # Ngưỡng EAR (màu đỏ mờ)
        if y < ear_thresh_y < y + h:
            cv2.line(img, (x + 5, ear_thresh_y), (x + w - 5, ear_thresh_y), (60, 60, 200), 1, cv2.LINE_AA)
            cv2.putText(img, "EAR 0.2", (x + w - 48, ear_thresh_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (80, 80, 220), 1)

        # Ngưỡng MAR (màu vàng mờ)
        if y < mar_thresh_y < y + h:
            cv2.line(img, (x + 5, mar_thresh_y), (x + w - 5, mar_thresh_y), (50, 180, 220), 1, cv2.LINE_AA)
            cv2.putText(img, "MAR 0.5", (x + w - 48, mar_thresh_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (50, 180, 220), 1)

        # Vẽ đường sóng EAR
        pts_ear = []
        for i, val in enumerate(self.ear_history):
            px = int(x + 5 + i * ((w - 10) / (self.history_len - 1)))
            norm_val = np.clip(val / 0.6, 0.0, 1.0)
            py = int(y + h - 5 - norm_val * (h - 25))
            pts_ear.append((px, py))

        for i in range(len(pts_ear) - 1):
            cv2.line(img, pts_ear[i], pts_ear[i + 1], COLOR_CYAN, 2, cv2.LINE_AA)

        # Vẽ đường sóng MAR
        pts_mar = []
        for i, val in enumerate(self.mar_history):
            px = int(x + 5 + i * ((w - 10) / (self.history_len - 1)))
            norm_val = np.clip(val / 1.0, 0.0, 1.0)
            py = int(y + h - 5 - norm_val * (h - 25))
            pts_mar.append((px, py))

        for i in range(len(pts_mar) - 1):
            cv2.line(img, pts_mar[i], pts_mar[i + 1], (0, 165, 255), 1, cv2.LINE_AA)

    def draw_hud(self, frame, face_info, yolo_info, evaluation_result, session_stats, fps=0.0, latency_ms=0.0):
        """
        Vẽ toàn bộ giao diện Cyber HUD lên frame video.
        """
        self.pulse_frame = (self.pulse_frame + 1) % 60
        h_img, w_img, _ = frame.shape

        # Cập nhật lịch sử sóng
        ear = face_info.get("ear_avg", 0.3) if face_info else 0.3
        mar = face_info.get("mar", 0.15) if face_info else 0.15
        self.ear_history.append(ear)
        self.mar_history.append(mar)

        # 1. Vẽ Face Bounding Box & Landmarks
        if face_info and face_info.get("detected", False):
            fx, fy, fw, fh = face_info.get("face_bbox", (0, 0, 0, 0))
            cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (0, 200, 120), 1)
            # 4 góc phong cách Corner Bracket
            bracket_len = min(20, fw // 4)
            cv2.line(frame, (fx, fy), (fx + bracket_len, fy), (0, 255, 180), 2)
            cv2.line(frame, (fx, fy), (fx, fy + bracket_len), (0, 255, 180), 2)
            cv2.line(frame, (fx + fw, fy), (fx + fw - bracket_len, fy), (0, 255, 180), 2)
            cv2.line(frame, (fx + fw, fy), (fx + fw, fy + bracket_len), (0, 255, 180), 2)
            cv2.line(frame, (fx, fy + fh), (fx + bracket_len, fy + fh), (0, 255, 180), 2)
            cv2.line(frame, (fx, fy + fh), (fx, fy + fh - bracket_len), (0, 255, 180), 2)
            cv2.line(frame, (fx + fw, fy + fh), (fx + fw - bracket_len, fy + fh), (0, 255, 180), 2)
            cv2.line(frame, (fx + fw, fy + fh), (fx + fw, fy + fh - bracket_len), (0, 255, 180), 2)

            # Vẽ trục 3D Head Pose
            camera_matrix = np.array([
                [w_img, 0, w_img / 2.0],
                [0, w_img, h_img / 2.0],
                [0, 0, 1]
            ], dtype=np.float64)
            self._draw_head_pose_axes(frame, face_info.get("rot_vec"), face_info.get("trans_vec"), camera_matrix)

        # 2. Vẽ Bounding Box phát hiện vật thể YOLO
        if yolo_info and yolo_info.get("raw_detections"):
            for det in yolo_info["raw_detections"]:
                bx, by, bw, bh = det["box"]
                cname = det["class"]
                conf = det["conf"]
                box_col = (0, 60, 255) if "phone" in cname else (0, 160, 255)
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), box_col, 2)
                cv2.putText(frame, f"{cname.upper()} {conf*100:.0f}%", (bx, by - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_col, 1, cv2.LINE_AA)

        # 3. Top Banner: Trạng thái & Mức độ Cảnh Báo
        alert_level = evaluation_result.get("alert_level", 0)
        class_name = evaluation_result.get("class_name", "Normal")
        alert_reason = evaluation_result.get("alert_reason", "")
        vn_label = CLASS_VIETNAMESE.get(class_name, class_name)
        hud_label_fallback = CLASS_HUD_LABELS.get(class_name, class_name)

        if alert_level == 2:
            # Nhấp nháy màu đỏ cho Level 2 (Báo động khẩn cấp)
            is_flash = (self.pulse_frame // 8) % 2 == 0
            banner_bg = COLOR_RED if is_flash else (20, 20, 140)
            prefix = "CRITICAL: "
            border_col = (50, 50, 255)
        elif alert_level == 1:
            banner_bg = (20, 140, 200)
            prefix = "WARNING: "
            border_col = COLOR_YELLOW
        else:
            banner_bg = (20, 100, 30)
            prefix = "NORMAL: "
            border_col = COLOR_GREEN

        status_text_vn = f"{prefix}{vn_label.upper()}"
        status_text_ascii = f"{prefix}{hud_label_fallback.upper()}"

        # Vẽ thanh cảnh báo đỉnh màn hình
        self._draw_transparent_rect(frame, (10, 10), (w_img - 10, 65), banner_bg, alpha=0.85)
        cv2.rectangle(frame, (10, 10), (w_img - 10, 65), border_col, 2)

        # Vẽ text: Ưu tiên PIL TrueType font để hiển thị Tiếng Việt có dấu chuẩn đẹp 100% không bị lỗi ????
        drawn_with_pil = False
        if self.banner_font is not None:
            try:
                roi_w = min(w_img - 200, 520)
                roi = frame[10:65, 10:10 + roi_w]
                pil_roi = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(pil_roi)
                draw.text((15, 14), status_text_vn, font=self.banner_font, fill=(255, 255, 255))
                frame[10:65, 10:10 + roi_w] = cv2.cvtColor(np.array(pil_roi), cv2.COLOR_RGB2BGR)
                drawn_with_pil = True
            except Exception:
                drawn_with_pil = False

        if not drawn_with_pil:
            cv2.putText(frame, status_text_ascii, (25, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_WHITE, 2, cv2.LINE_AA)
        
        # Hiển thị thông số FPS & Latency bên phải banner
        cv2.putText(frame, f"{fps:.1f} FPS | {latency_ms:.1f} ms", (w_img - 170, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_CYAN, 1, cv2.LINE_AA)

        # 4. Telemetry Card bên trái (Các chỉ số sinh học)
        card_w, card_h = 220, 150
        cx, cy = 10, 75
        self._draw_transparent_rect(frame, (cx, cy), (cx + card_w, cy + card_h), COLOR_DARK_BG, 0.75)
        cv2.putText(frame, "BIOMETRIC TELEMETRY", (cx + 12, cy + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_CYAN, 1, cv2.LINE_AA)

        ear_val = face_info.get("ear_avg", 0.0) if face_info else 0.0
        mar_val = face_info.get("mar", 0.0) if face_info else 0.0
        pitch_val = face_info.get("pitch", 0.0) if face_info else 0.0
        yaw_val = face_info.get("yaw", 0.0) if face_info else 0.0
        roll_val = face_info.get("roll", 0.0) if face_info else 0.0

        cv2.putText(frame, f"EAR (Eye Open): {ear_val:.3f}", (cx + 12, cy + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)
        cv2.putText(frame, f"MAR (Mouth Open): {mar_val:.3f}", (cx + 12, cy + 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)
        cv2.putText(frame, f"Head Pitch: {pitch_val:+.1f} deg", (cx + 12, cy + 91),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)
        cv2.putText(frame, f"Head Yaw:   {yaw_val:+.1f} deg", (cx + 12, cy + 114),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)
        cv2.putText(frame, f"Head Roll:  {roll_val:+.1f} deg", (cx + 12, cy + 137),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)

        # 5. Attention Score Bar (Thanh điểm tập trung góc trên phải)
        att_score = evaluation_result.get("attention_score", 100.0)
        bx, by, bw, bh = w_img - 190, 75, 180, 45
        self._draw_transparent_rect(frame, (bx, by), (bx + bw, by + bh), COLOR_DARK_BG, 0.75)
        cv2.putText(frame, f"FOCUS: {att_score:.0f}%", (bx + 10, by + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)

        # Vẽ progress bar điểm tập trung
        fill_w = int((bw - 20) * (np.clip(att_score, 0.0, 100.0) / 100.0))
        att_col = COLOR_GREEN if att_score > 70 else (COLOR_YELLOW if att_score > 40 else COLOR_RED)
        cv2.rectangle(frame, (bx + 10, by + 25), (bx + 10 + fill_w, by + 37), att_col, -1)
        cv2.rectangle(frame, (bx + 10, by + 25), (bx + bw - 10, by + 37), (100, 100, 100), 1)

        # 6. Biểu đồ sóng EAR / MAR góc dưới màn hình
        chart_w = w_img - 20
        chart_h = 80
        chart_x = 10
        chart_y = h_img - chart_h - 38
        self._draw_strip_chart(frame, chart_x, chart_y, chart_w, chart_h)

        # 7. Bottom Status Footer (Thống kê phiên lái xe)
        elapsed = session_stats.get("elapsed_formatted", "00:00:00")
        bpm = session_stats.get("blinks_per_min", 0.0)
        yawns = session_stats.get("yawn_count", 0)
        distracts = session_stats.get("distraction_count", 0)
        drowsy_evs = session_stats.get("drowsy_event_count", 0)

        footer_text = f"TIME: {elapsed} | BLINKS: {bpm:.1f}/m | YAWNS: {yawns} | DISTRACTS: {distracts} | DROWSY: {drowsy_evs}"
        self._draw_transparent_rect(frame, (10, h_img - 32), (w_img - 10, h_img - 8), COLOR_DARK_BG, 0.85)
        cv2.putText(frame, footer_text, (20, h_img - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (210, 210, 210), 1, cv2.LINE_AA)

        return frame
