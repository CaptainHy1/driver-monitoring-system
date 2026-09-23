"""
[M3] Pose Detector Module (YOLO-Pose)
Extracts 17 COCO 2D skeletal keypoints (x, y, conf) from the upper body / driver frame.
"""

from typing import Dict, Any, Tuple
import numpy as np
import cv2
import torch

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

from config import POSE_INPUT_SIZE, DEVICE


class PoseDetector:
    """
    Wrapper for YOLO-Pose (v8n-pose / v11n-pose).
    Trích xuất 17 điểm khớp xương COCO:
      0: Nose, 1: L-Eye, 2: R-Eye, 3: L-Ear, 4: R-Ear,
      5: L-Shoulder, 6: R-Shoulder, 7: L-Elbow, 8: R-Elbow,
      9: L-Wrist, 10: R-Wrist, 11: L-Hip, 12: R-Hip,
      13: L-Knee, 14: R-Knee, 15: L-Ankle, 16: R-Ankle.
    """

    KEYPOINT_NAMES = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]

    def __init__(self, model_name: str = "yolov8n-pose.pt", conf_thresh: float = 0.3, device: torch.device = DEVICE):
        self.device = device
        self.conf_thresh = conf_thresh
        self.model = None

        if ULTRALYTICS_AVAILABLE:
            try:
                # Load ultralytics pose model (auto-downloads lightweight weights if not present)
                self.model = YOLO(model_name)
            except Exception as e:
                print(f"[PoseDetector] Warning: Could not initialize YOLO({model_name}): {e}")
                self.model = None

    def detect(self, body_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Detects upper-body keypoints in body_bgr image.
        Returns:
          - keypoints: np.ndarray of shape (17, 3) where each row is [x, y, conf] normalized to [0, 1]
          - posture_state: str description ('normal', 'reaching_behind', 'leaning_forward', 'arm_raised')
          - raw_pixels: np.ndarray of shape (17, 2) in image coordinate space
        """
        if body_bgr is None or body_bgr.size == 0:
            return {
                "keypoints": np.zeros((17, 3), dtype=np.float32),
                "posture_state": "unknown",
                "raw_pixels": np.zeros((17, 2), dtype=np.float32),
            }

        h, w, _ = body_bgr.shape
        keypoints = np.zeros((17, 3), dtype=np.float32)
        raw_pixels = np.zeros((17, 2), dtype=np.float32)
        posture_state = "normal"

        if self.model is not None:
            try:
                results = self.model(body_bgr, verbose=False, conf=self.conf_thresh)
                if len(results) > 0 and results[0].keypoints is not None:
                    # Get first detected person
                    kp_data = results[0].keypoints.data
                    if kp_data is not None and len(kp_data) > 0:
                        pts = kp_data[0].cpu().numpy()  # shape (17, 3)
                        raw_pixels = pts[:, :2]
                        # Normalize coordinates to [0, 1]
                        keypoints[:, 0] = pts[:, 0] / max(w, 1)
                        keypoints[:, 1] = pts[:, 1] / max(h, 1)
                        keypoints[:, 2] = pts[:, 2]  # confidence
            except Exception:
                pass

        # Heuristic posture evaluation based on keypoint positions
        posture_state = self._evaluate_posture(keypoints)

        return {
            "keypoints": keypoints,
            "posture_state": posture_state,
            "raw_pixels": raw_pixels,
        }

    def _evaluate_posture(self, kp: np.ndarray) -> str:
        """Heuristic check on arm height and torso angle."""
        # 5: L-Shoulder, 6: R-Shoulder, 9: L-Wrist, 10: R-Wrist, 0: Nose
        if kp[5, 2] > 0.3 and kp[6, 2] > 0.3:
            shoulder_y = (kp[5, 1] + kp[6, 1]) / 2.0
            # Right arm raised near head
            if kp[10, 2] > 0.3 and kp[10, 1] < shoulder_y:
                return "right_arm_raised_to_head"
            # Left arm raised near head
            if kp[9, 2] > 0.3 and kp[9, 1] < shoulder_y:
                return "left_arm_raised_to_head"
            # Severe head tilt or leaning
            if kp[0, 2] > 0.3 and abs(kp[0, 0] - 0.5) > 0.35:
                return "reaching_sideways_or_behind"
        return "normal"
