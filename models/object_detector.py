"""
[M5] Cockpit Object & Hand Interaction Detector
Detects cellphones, bottles, cups, cigarettes, food, and evaluates hand-on-wheel placement.
Produces feature vector f_hand in R^256.
"""

from typing import Dict, Any, List
import numpy as np
import cv2
import torch
import torch.nn as nn

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

from config import (
    COCKPIT_INPUT_SIZE,
    HAND_FEAT_DIM,
    OBJECT_CLASSES_OF_INTEREST,
    DEVICE,
)


class CockpitObjectDetector:
    """
    Detector for distracting items and steering wheel interactions.
    Extracts:
      - detected_objects: list of {name, confidence, bbox}
      - hands_on_wheel: 'both_hands', 'one_hand', 'hands_off'
      - f_hand: torch.Tensor of shape (1, 256)
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        conf_thresh: float = 0.35,
        device: torch.device = DEVICE,
    ):
        self.device = device
        self.conf_thresh = conf_thresh
        self.model = None

        if ULTRALYTICS_AVAILABLE:
            try:
                self.model = YOLO(model_name)
            except Exception as e:
                print(f"[CockpitObjectDetector] Warning: Could not initialize YOLO({model_name}): {e}")
                self.model = None

        # Feature projection layer to transform object detection features into f_hand in R^256
        self.feature_proj = nn.Sequential(
            nn.Linear(64, HAND_FEAT_DIM),
            nn.LayerNorm(HAND_FEAT_DIM),
            nn.ReLU(),
            nn.Linear(HAND_FEAT_DIM, HAND_FEAT_DIM),
        ).to(self.device)

    def detect(self, cockpit_bgr: np.ndarray, driver_keypoints: np.ndarray = None) -> Dict[str, Any]:
        """
        Runs object detection and checks hand positions.
        """
        if cockpit_bgr is None or cockpit_bgr.size == 0:
            return {
                "detected_objects": [],
                "hands_on_wheel": "hands_off",
                "phone_detected": False,
                "drink_detected": False,
                "f_hand": torch.zeros((1, HAND_FEAT_DIM), device=self.device),
            }

        h, w, _ = cockpit_bgr.shape
        detected_objects: List[Dict[str, Any]] = []
        phone_detected = False
        drink_detected = False
        hands_visible_count = 0

        # Raw feature descriptor (64-dim) summarizing detection presence and spatial bins
        raw_feat = np.zeros(64, dtype=np.float32)

        if self.model is not None:
            try:
                results = self.model(cockpit_bgr, verbose=False, conf=self.conf_thresh)
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = self.model.names.get(cls_id, "")
                        conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()

                        if cls_name in OBJECT_CLASSES_OF_INTEREST or "phone" in cls_name or "bottle" in cls_name or "cup" in cls_name:
                            detected_objects.append({
                                "name": cls_name,
                                "confidence": round(conf, 3),
                                "bbox": xyxy,
                            })

                            if "phone" in cls_name:
                                phone_detected = True
                                raw_feat[0] = max(raw_feat[0], conf)
                                # Normalized center coordinates
                                raw_feat[1] = (xyxy[0] + xyxy[2]) / (2.0 * w)
                                raw_feat[2] = (xyxy[1] + xyxy[3]) / (2.0 * h)

                            if "bottle" in cls_name or "cup" in cls_name:
                                drink_detected = True
                                raw_feat[3] = max(raw_feat[3], conf)
                                raw_feat[4] = (xyxy[0] + xyxy[2]) / (2.0 * w)
                                raw_feat[5] = (xyxy[1] + xyxy[3]) / (2.0 * h)
                            if "hand" in cls_name.lower():
                                hands_visible_count += 1
            except Exception:
                pass

        # -------------------------------------------------------------
        # Ước lượng vị trí bàn tay & tương tác vật thể (Hand Estimation)
        # (Không giả định vị trí vô-lăng vì mô hình không train cầm vô-lăng)
        # -------------------------------------------------------------
        hand_status = "normal"

        # Ước lượng bổ sung vị trí cổ tay/bàn tay từ keypoints
        if driver_keypoints is not None and len(driver_keypoints) >= 11:
            lw = driver_keypoints[9]   # left_wrist
            rw = driver_keypoints[10]  # right_wrist

            if lw[2] > 0.25 and hands_visible_count == 0:
                hands_visible_count += 1
            if rw[2] > 0.25 and hands_visible_count <= 1:
                hands_visible_count += 1

            # Kiểm tra tay giơ lên gần mặt/tai
            if (lw[2] > 0.3 and lw[1] < 0.4) or (rw[2] > 0.3 and rw[1] < 0.4):
                hand_status = "hand_raised"

        if phone_detected:
            hand_status = "holding_phone"
        elif drink_detected:
            hand_status = "holding_drink"
        elif hands_visible_count > 0 and hand_status != "hand_raised":
            hand_status = "hands_visible"

        # Encode hand status descriptor
        raw_feat[6] = 1.0 if hands_visible_count >= 2 else 0.0
        raw_feat[7] = 1.0 if "holding" in hand_status else 0.0
        raw_feat[8] = 1.0 if hand_status == "hand_raised" else 0.0

        # Project 64-dim raw feature descriptor to f_hand (1, 256)
        with torch.no_grad():
            feat_tensor = torch.from_numpy(raw_feat).unsqueeze(0).to(self.device)
            f_hand = self.feature_proj(feat_tensor)

        return {
            "detected_objects": detected_objects,
            "hand_status": hand_status,
            "hands_on_wheel": hand_status,  # Giữ alias tương thích
            "hands_visible_count": hands_visible_count,
            "phone_detected": phone_detected,
            "drink_detected": drink_detected,
            "f_hand": f_hand,
        }
