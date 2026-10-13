from typing import Dict, Any, Tuple
import numpy as np
import torch

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

from config import POSE_INPUT_SIZE, DEVICE


class PoseDetector:
    """
    Detects 17 COCO skeletal keypoints for driver pose estimation using YOLO-Pose.
    """

    def __init__(
        self,
        model_name: str = "yolov8n-pose.pt",
        conf_thresh: float = 0.25,
        device: torch.device = DEVICE,
    ):
        self.device = device
        self.conf_thresh = conf_thresh
        self.model = None

        if ULTRALYTICS_AVAILABLE:
            try:
                self.model = YOLO(model_name)
            except Exception as e:
                print(f"[PoseDetector] Warning: Could not initialize YOLO({model_name}): {e}")
                self.model = None

    def detect(self, body_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Detects upper-body keypoints in body_bgr image.
        Returns:
          - keypoints: np.ndarray of shape (17, 3) normalized to [0, 1]
          - posture_state: str description
          - raw_pixels: np.ndarray of shape (17, 2) in image coordinate space
          - hand_to_ear: bool whether a hand is at the ear/head
        """
        if body_bgr is None or body_bgr.size == 0:
            return {
                "keypoints": np.zeros((17, 3), dtype=np.float32),
                "posture_state": "normal",
                "raw_pixels": np.zeros((17, 2), dtype=np.float32),
                "hand_to_ear": False,
            }

        h, w, _ = body_bgr.shape
        keypoints = np.zeros((17, 3), dtype=np.float32)
        raw_pixels = np.zeros((17, 2), dtype=np.float32)
        posture_state = "normal"
        hand_to_ear = False

        if self.model is not None:
            try:
                results = self.model(body_bgr, verbose=False, conf=self.conf_thresh)
                if len(results) > 0 and results[0].keypoints is not None:
                    kp_data = results[0].keypoints.data
                    boxes = results[0].boxes
                    if kp_data is not None and len(kp_data) > 0:
                        # Select person closest to image center (the driver)
                        best_person = 0
                        min_dist = float("inf")
                        if boxes is not None and len(boxes) > 0:
                            for i, b in enumerate(boxes):
                                xyxy = b.xyxy[0].cpu().numpy()
                                cx = (xyxy[0] + xyxy[2]) / 2.0
                                cy = (xyxy[1] + xyxy[3]) / 2.0
                                dist = np.hypot(cx - w / 2.0, cy - h / 2.0)
                                if dist < min_dist:
                                    min_dist = dist
                                    best_person = i
                        pts = kp_data[best_person].cpu().numpy()  # shape (17, 3)
                        raw_pixels = pts[:, :2]
                        # Normalize coordinates to [0, 1]
                        keypoints[:, 0] = pts[:, 0] / max(w, 1)
                        keypoints[:, 1] = pts[:, 1] / max(h, 1)
                        keypoints[:, 2] = pts[:, 2]  # confidence
            except Exception:
                pass

        # Heuristic posture evaluation based on keypoint positions
        posture_state, hand_to_ear = self._evaluate_posture(keypoints)

        return {
            "keypoints": keypoints,
            "posture_state": posture_state,
            "raw_pixels": raw_pixels,
            "hand_to_ear": hand_to_ear,
        }

    def _evaluate_posture(self, kp: np.ndarray) -> Tuple[str, bool]:
        """
        Evaluates driver posture and checks for hand-to-ear phone gesture.
        Returns (posture_state, hand_to_ear).
        """
        hand_to_ear = False
        posture_state = "normal"
        if kp[5, 2] > 0.20 and kp[6, 2] > 0.20:
            shoulder_y = (kp[5, 1] + kp[6, 1]) / 2.0
            sh_w = np.linalg.norm(kp[5, :2] - kp[6, :2]) + 1e-5

            # Distance from wrists to ears (normalized by shoulder width)
            lw, rw = kp[9, :2], kp[10, :2]
            lear, rear = kp[3, :2], kp[4, :2]
            d_lw_lear = np.linalg.norm(lw - lear) / sh_w
            d_rw_rear = np.linalg.norm(rw - rear) / sh_w
            d_lw_rear = np.linalg.norm(lw - rear) / sh_w
            d_rw_lear = np.linalg.norm(rw - lear) / sh_w
            min_ear_dist = min(d_lw_lear, d_rw_rear, d_lw_rear, d_rw_lear)

            # Hand raised near ear/head for phone call
            if min_ear_dist < 0.90 and (kp[9, 2] > 0.20 or kp[10, 2] > 0.20):
                hand_to_ear = True
                posture_state = "right_arm_raised_to_head" if (d_rw_rear < d_lw_lear) else "left_arm_raised_to_head"
            elif kp[10, 2] > 0.3 and kp[10, 1] < shoulder_y + 0.15 * sh_w:
                posture_state = "right_arm_raised_to_head"
            elif kp[9, 2] > 0.3 and kp[9, 1] < shoulder_y + 0.15 * sh_w:
                posture_state = "left_arm_raised_to_head"
            elif kp[0, 2] > 0.3 and abs(kp[0, 0] - 0.5) > 0.35:
                posture_state = "reaching_sideways_or_behind"

        return posture_state, hand_to_ear
