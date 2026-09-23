"""
[M9] Visualizer & HUD Overlay Module
Renders bounding boxes, skeletal keypoints, gaze indicator, distraction gauge,
and alert banners onto the video frame with full UTF-8 Vietnamese font support via PIL,
plus JSON metadata export.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import AlertLevel
from modules.alert_engine import AlertDecision
from models.st_gcn import COCO_EDGES


class DMSVisualizer:
    """
    Renders professional Head-Up Display (HUD) overlays on live frames
    with full Vietnamese UTF-8 font support (Pillow + Arial/Segoe UI)
    and serializes event logs to JSON according to srs.md.
    """

    # Alert level colors (BGR format)
    COLOR_MAP = {
        AlertLevel.LEVEL_0: (40, 180, 40),    # Green (An toàn)
        AlertLevel.LEVEL_1: (0, 215, 255),    # Yellow (Nhắc nhở)
        AlertLevel.LEVEL_2: (0, 120, 255),    # Orange (Nguy hiểm)
        AlertLevel.LEVEL_3: (30, 30, 220),    # Red (Nguy cấp)
    }

    # Vietnamese translation map for status fields
    GAZE_VN_MAP = {
        "forward": "Nhìn thẳng phía trước",
        "looking_down": "Cúi nhìn xuống (Điện thoại/Taplo)",
        "looking_left": "Nhìn gương trái",
        "looking_right": "Nhìn gương phải",
        "eyes_closed": "Đang nhắm mắt",
    }

    HAND_STATUS_VN_MAP = {
        "normal": "Bình thường",
        "hands_visible": "Quan sát thấy tay",
        "hand_raised": "Tay giơ cao (gần mặt/tai)",
        "holding_phone": "Cầm điện thoại",
        "holding_drink": "Cầm chai / cốc nước",
    }

    POSTURE_VN_MAP = {
        "normal": "Tư thế bình thường",
        "right_arm_raised_to_head": "Tay phải đưa lên đầu/tai",
        "left_arm_raised_to_head": "Tay trái đưa lên đầu/tai",
        "reaching_sideways_or_behind": "Rướn người / Ngoái sau",
    }

    OBJECT_VN_MAP = {
        "cell phone": "Điện thoại",
        "cellphone": "Điện thoại",
        "bottle": "Chai nước",
        "cup": "Cốc nước",
        "sandwich": "Đồ ăn",
        "food": "Đồ ăn",
        "cigarette": "Thuốc lá",
    }

    def __init__(self):
        # Locate system TTF font with Vietnamese support (Arial / Segoe UI on Windows)
        font_candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        self.font_path = None
        for p in font_candidates:
            if os.path.exists(p):
                self.font_path = p
                break

        # Cache font instances by size
        self._font_cache = {}
        for sz in [14, 16, 18, 20, 22, 24, 28]:
            self._font_cache[sz] = self._load_font(sz)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        if self.font_path:
            try:
                return ImageFont.truetype(self.font_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def render_hud(
        self,
        frame: np.ndarray,
        decision: AlertDecision,
        face_info: Dict[str, Any],
        pose_info: Dict[str, Any],
        object_info: Dict[str, Any],
        fps: float = 30.0,
        frame_id: int = 0,
    ) -> np.ndarray:
        """Draws HUD overlay with crisp Vietnamese fonts directly on a copy of frame."""
        vis = frame.copy()
        h, w, _ = vis.shape
        color = self.COLOR_MAP.get(decision.level, (40, 180, 40))

        # -------------------------------------------------------------
        # 1. Draw Geometric primitives via OpenCV (Fast)
        # -------------------------------------------------------------

        # 1.1 Object Bounding Boxes
        text_queue = []  # List of tuples: (text, (x, y), font_size, rgb_color)
        for obj in object_info.get("detected_objects", []):
            x1, y1, x2, y2 = obj["bbox"]
            vn_name = self.OBJECT_VN_MAP.get(obj["name"].lower(), obj["name"])
            label = f"{vn_name} ({obj['confidence']:.2f})"
            box_color = (0, 0, 255) if "phone" in obj["name"] else (255, 200, 0)
            cv2.rectangle(vis, (x1, y1), (x2, y2), box_color, 2)
            # Queue label text
            text_queue.append((label, (x1, max(15, y1 - 22)), 16, (255, 255, 255)))

        # 1.2 Skeleton Keypoints & Limbs
        raw_kps = pose_info.get("raw_pixels")
        if raw_kps is not None and len(raw_kps) == 17:
            for u, v in COCO_EDGES:
                if u < len(raw_kps) and v < len(raw_kps):
                    pt1 = (int(raw_kps[u, 0]), int(raw_kps[u, 1]))
                    pt2 = (int(raw_kps[v, 0]), int(raw_kps[v, 1]))
                    if pt1 != (0, 0) and pt2 != (0, 0):
                        cv2.line(vis, pt1, pt2, (0, 255, 200), 2)
            for pt in raw_kps:
                x, y = int(pt[0]), int(pt[1])
                if x > 0 and y > 0:
                    cv2.circle(vis, (x, y), 4, (0, 100, 255), -1)

        # 1.3 Top Banner Background
        banner_h = 55
        overlay = vis.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), color, -1)
        cv2.addWeighted(overlay, 0.85, vis, 0.15, 0, vis)

        # Queue Banner Text
        banner_text = decision.message
        text_queue.append((banner_text, (20, 14), 22, (255, 255, 255)))

        # 1.4 Right Side Status Panel
        panel_w = 340
        panel_h = 210
        p_x1 = w - panel_w - 15
        p_y1 = banner_h + 15
        cv2.rectangle(overlay, (p_x1, p_y1), (w - 15, p_y1 + panel_h), (25, 25, 25), -1)
        cv2.addWeighted(overlay, 0.75, vis, 0.25, 0, vis)

        # Prepare panel Vietnamese info lines
        raw_gaze = face_info.get("gaze_direction", "forward")
        vn_gaze = self.GAZE_VN_MAP.get(raw_gaze, raw_gaze)

        raw_hand = object_info.get("hand_status", "normal")
        vn_hand = self.HAND_STATUS_VN_MAP.get(raw_hand, "Bình thường")

        raw_posture = pose_info.get("posture_state", "normal")
        vn_posture = self.POSTURE_VN_MAP.get(raw_posture, raw_posture)

        eye_closed_str = "Đang nhắm" if face_info.get("eye_closed", False) else "Bình thường"
        yawn_str = "Có ngáp" if face_info.get("yawning", False) else "Không"

        hp = face_info.get("head_pose", {})
        pitch_val = hp.get("pitch", 0.0)
        gaze_display = f"{vn_gaze} (Pitch: {pitch_val:+.0f}°)" if raw_gaze == "looking_down" else f"{vn_gaze}"

        lines = [
            f"Tốc độ khung hình (FPS): {fps:.1f}",
            f"Hướng nhìn: {gaze_display}",
            f"Trạng thái mắt: {eye_closed_str} (EAR: {face_info.get('ear', 0.0):.2f})",
            f"Tỷ lệ nhắm mắt (PERCLOS): {face_info.get('perclos', 0.0)*100:.1f}%",
            f"Dấu hiệu ngáp: {yawn_str} (MAR: {face_info.get('mar', 0.0):.2f})",
            f"Bàn tay: {vn_hand}",
            f"Tư thế: {vn_posture}",
        ]

        for idx, line in enumerate(lines):
            text_queue.append((line, (p_x1 + 12, p_y1 + 12 + idx * 26), 15, (230, 230, 230)))

        # 1.5 Distraction Meter (Gauge Bar at Bottom)
        meter_y = h - 40
        meter_w = 300
        meter_h = 22
        pct = min(1.0, decision.violation_duration / 2.5) if decision.level > 0 else 0.0
        cv2.rectangle(vis, (20, meter_y), (20 + meter_w, meter_y + meter_h), (50, 50, 50), -1)
        cv2.rectangle(vis, (20, meter_y), (20 + int(meter_w * pct), meter_y + meter_h), color, -1)
        cv2.rectangle(vis, (20, meter_y), (20 + meter_w, meter_y + meter_h), (220, 220, 220), 1)

        gauge_text = f"Mức độ rủi ro phân tâm: {int(pct * 100)}%"
        text_queue.append((gauge_text, (35 + meter_w, meter_y + 2), 16, (255, 255, 255)))

        # -------------------------------------------------------------
        # 2. Render all queued Vietnamese text using PIL (Single Pass)
        # -------------------------------------------------------------
        pil_img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        for text, (tx, ty), font_size, rgb_color in text_queue:
            font = self._font_cache.get(font_size)
            if font is None:
                font = self._load_font(font_size)
                self._font_cache[font_size] = font
            draw.text((tx, ty), text, font=font, fill=rgb_color)

        vis = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return vis

    def build_json_event(
        self,
        frame_id: int,
        fps: float,
        decision: AlertDecision,
        face_info: Dict[str, Any],
        pose_info: Dict[str, Any],
        object_info: Dict[str, Any],
        confidence: float = 0.95,
    ) -> Dict[str, Any]:
        """Creates metadata dictionary matching Section 8.1 in srs.md."""
        return {
            "timestamp": datetime.now().isoformat(),
            "frame_id": frame_id,
            "inference_fps": round(fps, 1),
            "system_state": {
                "predicted_class": decision.active_class_name,
                "class_id": decision.active_class,
                "confidence": round(confidence, 3),
                "alert_level": decision.level,
                "violation_duration_sec": decision.violation_duration,
            },
            "model_assignments": {
                "M2_face_vit": {
                    "gaze": face_info.get("gaze_direction", "forward"),
                    "eye_closed": face_info.get("eye_closed", False),
                    "ear": face_info.get("ear", 0.3),
                    "perclos": face_info.get("perclos", 0.0),
                    "yawning": face_info.get("yawning", False),
                },
                "M3_M4_pose_stgcn": {
                    "posture": pose_info.get("posture_state", "normal"),
                    "head_pose": face_info.get("head_pose", {}),
                },
                "M5_yolo_objects": {
                    "hand_status": object_info.get("hand_status", "normal"),
                    "detected_items": object_info.get("detected_objects", []),
                },
            },
            "action_commands": {
                "buzzer_active": decision.trigger_buzzer,
                "ui_banner_text": decision.message,
                "save_video_evidence": decision.save_evidence,
            },
        }
