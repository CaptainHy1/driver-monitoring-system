"""
[M8] Alert & Decision Engine
Evaluates temporal violation durations and triggers multi-level safety alerts (Level 0 to Level 3).
"""

import time
from dataclasses import dataclass
from typing import Dict, Any

from config import (
    AlertLevel,
    GAZE_AWAY_TIME_THRESHOLD,
    EYE_CLOSURE_TIME_THRESHOLD,
    PHONE_USAGE_TIME_THRESHOLD,
    REACHING_TIME_THRESHOLD,
    EATING_TIME_THRESHOLD,
    PERCLOS_DROWSY_THRESHOLD,
)


@dataclass
class AlertDecision:
    level: int                   # 0: Safe, 1: Warning, 2: Danger, 3: Emergency
    active_class: str            # 'C0', 'C1', etc.
    active_class_name: str       # 'Phone Usage', etc.
    message: str                 # User-facing alert message
    trigger_buzzer: bool         # Whether buzzer is activated
    violation_duration: float    # How long violation has persisted (seconds)
    save_evidence: bool          # Flag to save video clip


class AlertEngine:
    """
    Maintains continuous violation counters for temporal actions to eliminate false alarms.
    """

    def __init__(self):
        self.last_timestamp = time.time()

        # Timers tracking consecutive violation durations
        self.timers: Dict[str, float] = {
            "gaze_away": 0.0,
            "looking_down": 0.0,
            "eyes_closed": 0.0,
            "phone_usage": 0.0,
            "reaching": 0.0,
            "eating": 0.0,
            "yawning": 0.0,
        }

    def update(
        self,
        predicted_class: str,
        predicted_label: str,
        confidence: float,
        face_info: Dict[str, Any],
        object_info: Dict[str, Any],
        pose_info: Dict[str, Any],
    ) -> AlertDecision:
        """
        Updates state and evaluates safety thresholds.
        """
        now = time.time()
        dt = max(0.0, min(0.5, now - self.last_timestamp))  # clamp dt
        self.last_timestamp = now

        # 1. Update violation timers
        gaze_dir = face_info.get("gaze_direction", "forward")
        is_looking_down = (gaze_dir == "looking_down")

        # Phone is active only when sensor detects it (YOLO phone or hand holding phone),
        # or when temporal classifier is highly confident (>= 0.75)
        phone_detected = object_info.get("phone_detected", False)
        hand_holding_phone = (object_info.get("hand_status") == "holding_phone")
        classifier_says_phone = (predicted_class == "C1" and confidence >= 0.75)
        phone_active = phone_detected or hand_holding_phone or classifier_says_phone

        # Gaze away
        if gaze_dir != "forward":
            self.timers["gaze_away"] += dt
        else:
            self.timers["gaze_away"] = max(0.0, self.timers["gaze_away"] - dt * 1.5)

        # Looking down & Phone usage
        if is_looking_down:
            self.timers["looking_down"] += dt
            if phone_active:
                # Driver is looking down while handling phone -> accelerate alert
                self.timers["phone_usage"] += dt * 1.5
        else:
            self.timers["looking_down"] = max(0.0, self.timers["looking_down"] - dt * 2.5)

        if phone_active and not is_looking_down:
            self.timers["phone_usage"] += dt
        elif not phone_active and not is_looking_down:
            self.timers["phone_usage"] = max(0.0, self.timers["phone_usage"] - dt * 2.5)

        # Eyes closed
        if face_info.get("eye_closed", False):
            self.timers["eyes_closed"] += dt
        else:
            self.timers["eyes_closed"] = max(0.0, self.timers["eyes_closed"] - dt * 2.0)

        # Yawning
        if face_info.get("yawning", False):
            self.timers["yawning"] += dt
        else:
            self.timers["yawning"] = max(0.0, self.timers["yawning"] - dt * 1.5)

        # Reaching / Turning
        if "reaching" in pose_info.get("posture_state", "") or (predicted_class == "C3" and confidence >= 0.75):
            self.timers["reaching"] += dt
        else:
            self.timers["reaching"] = max(0.0, self.timers["reaching"] - dt * 2.0)

        # Eating / Drinking
        if object_info.get("drink_detected", False) or (predicted_class == "C4" and confidence >= 0.75):
            self.timers["eating"] += dt
        else:
            self.timers["eating"] = max(0.0, self.timers["eating"] - dt * 2.0)

        # 2. Evaluate Alert Rules (Priority from Level 3 to Level 0)

        # LEVEL 3: Critical Emergency (Drowsiness / Falling Asleep)
        if self.timers["eyes_closed"] >= EYE_CLOSURE_TIME_THRESHOLD or face_info.get("perclos", 0.0) >= PERCLOS_DROWSY_THRESHOLD:
            return AlertDecision(
                level=AlertLevel.LEVEL_3,
                active_class="C2",
                active_class_name="Drowsiness / Falling Asleep",
                message="NGUY CẤP: TÀI XẾ CÓ DẤU HIỆU NGỦ GẬT!",
                trigger_buzzer=True,
                violation_duration=round(self.timers["eyes_closed"], 2),
                save_evidence=True,
            )

        # LEVEL 2: Phone Usage
        if self.timers["phone_usage"] >= PHONE_USAGE_TIME_THRESHOLD:
            return AlertDecision(
                level=AlertLevel.LEVEL_2,
                active_class="C1",
                active_class_name="Phone Usage",
                message="CẢNH BÁO: KHÔNG SỬ DỤNG ĐIỆN THOẠI KHI LÁI XE!",
                trigger_buzzer=True,
                violation_duration=round(self.timers["phone_usage"], 2),
                save_evidence=True,
            )

        # LEVEL 2: Looking Down (Phone in lap / Taplo distraction)
        if self.timers["looking_down"] >= 2.0:
            return AlertDecision(
                level=AlertLevel.LEVEL_2,
                active_class="C0_VIOLATION",
                active_class_name="Looking Down",
                message="CẢNH BÁO: TÀI XẾ ĐANG CÚI ĐẦU NHÌN XUỐNG, MẤT TẬP TRUNG!",
                trigger_buzzer=True,
                violation_duration=round(self.timers["looking_down"], 2),
                save_evidence=True,
            )

        # LEVEL 2: Prolonged Eyes Off Road
        if self.timers["gaze_away"] >= GAZE_AWAY_TIME_THRESHOLD:
            return AlertDecision(
                level=AlertLevel.LEVEL_2,
                active_class="C0_VIOLATION",
                active_class_name="Distracted Gaze",
                message="CẢNH BÁO: CHÚ Ý QUAN SÁT ĐƯỜNG PHÍA TRƯỚC!",
                trigger_buzzer=True,
                violation_duration=round(self.timers["gaze_away"], 2),
                save_evidence=False,
            )

        # LEVEL 1: Yawning
        if self.timers["yawning"] >= 0.5:
            return AlertDecision(
                level=AlertLevel.LEVEL_1,
                active_class="C2",
                active_class_name="Yawning / Fatigue",
                message="Nhắc nhở: Phát hiện tài xế ngáp ngủ / có dấu hiệu mệt mỏi!",
                trigger_buzzer=False,
                violation_duration=round(self.timers["yawning"], 2),
                save_evidence=False,
            )

        # LEVEL 1: Reaching Behind / Side
        if self.timers["reaching"] >= REACHING_TIME_THRESHOLD:
            return AlertDecision(
                level=AlertLevel.LEVEL_1,
                active_class="C3",
                active_class_name="Reaching Behind / Side",
                message="Nhắc nhở: Tránh vươn người / ngoái đầu khi xe đang chạy!",
                trigger_buzzer=False,
                violation_duration=round(self.timers["reaching"], 2),
                save_evidence=False,
            )

        # LEVEL 1: Eating / Drinking
        if self.timers["eating"] >= EATING_TIME_THRESHOLD:
            return AlertDecision(
                level=AlertLevel.LEVEL_1,
                active_class="C4",
                active_class_name="Eating / Drinking",
                message="Nhắc nhở: Hạn chế ăn uống gây mất tập trung!",
                trigger_buzzer=False,
                violation_duration=round(self.timers["eating"], 2),
                save_evidence=False,
            )

        # LEVEL 0: Safe Driving
        # If classifier is untrained/low-confidence, ensure clean default to C0 Safe Driving
        safe_class = predicted_class if confidence >= 0.65 else "C0"
        safe_label = predicted_label if confidence >= 0.65 else "Safe Driving"

        return AlertDecision(
            level=AlertLevel.LEVEL_0,
            active_class=safe_class,
            active_class_name=safe_label,
            message="Lái xe an toàn (Normal)",
            trigger_buzzer=False,
            violation_duration=0.0,
            save_evidence=False,
        )
