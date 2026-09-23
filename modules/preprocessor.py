"""
[M1] Multi-ROI Preprocessor Module
Crops and normalizes 3 distinct Regions of Interest (Face, Body, Cockpit) from the raw driver camera feed.
"""

from typing import Dict, Tuple
import cv2
import numpy as np

from config import (
    FACE_INPUT_SIZE,
    POSE_INPUT_SIZE,
    COCKPIT_INPUT_SIZE,
)


class MultiROICropper:
    """
    Extracts Face ROI, Body/Pose ROI, and Cockpit ROI from raw driver camera video.
    Can utilize detected facial/person coordinates, or standard cabin partition layout.
    """

    def __init__(self):
        # Default cabin partition ratios for dash/cabin mounted camera:
        # Face is typically in the upper-center quadrant [0.05:0.55 Y, 0.20:0.80 X]
        # Body is upper-to-mid section [0.10:0.90 Y, 0.10:0.90 X]
        # Cockpit is lower-to-mid section [0.35:1.00 Y, 0.05:0.95 X]
        self.default_face_ratio = (0.05, 0.55, 0.25, 0.75)     # ymin, ymax, xmin, xmax
        self.default_body_ratio = (0.10, 0.90, 0.15, 0.85)
        self.default_cockpit_ratio = (0.35, 1.00, 0.05, 0.95)

    def crop_rois(
        self,
        frame: np.ndarray,
        face_bbox: Tuple[int, int, int, int] = None,
        person_bbox: Tuple[int, int, int, int] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Crops 3 ROIs:
          - 'face_roi': (224, 224, 3)
          - 'body_roi': (256, 256, 3)
          - 'cockpit_roi': (640, 640, 3)
          - 'original_frame': reference
        """
        h, w, _ = frame.shape

        # 1. Face ROI Crop
        if face_bbox is not None:
            fx1, fy1, fx2, fy2 = face_bbox
            # Add 15% margin
            pad_w = int((fx2 - fx1) * 0.15)
            pad_h = int((fy2 - fy1) * 0.15)
            fx1 = max(0, fx1 - pad_w)
            fy1 = max(0, fy1 - pad_h)
            fx2 = min(w, fx2 + pad_w)
            fy2 = min(h, fy2 + pad_h)
            face_crop = frame[fy1:fy2, fx1:fx2]
        else:
            ymin, ymax, xmin, xmax = self.default_face_ratio
            face_crop = frame[int(ymin * h):int(ymax * h), int(xmin * w):int(xmax * w)]

        if face_crop.size == 0:
            face_crop = frame

        # 2. Body ROI Crop
        if person_bbox is not None:
            bx1, by1, bx2, by2 = person_bbox
            body_crop = frame[by1:by2, bx1:bx2]
        else:
            ymin, ymax, xmin, xmax = self.default_body_ratio
            body_crop = frame[int(ymin * h):int(ymax * h), int(xmin * w):int(xmax * w)]

        if body_crop.size == 0:
            body_crop = frame

        # 3. Cockpit ROI Crop (Steering wheel and hands)
        c_ymin, c_ymax, c_xmin, c_xmax = self.default_cockpit_ratio
        cockpit_crop = frame[int(c_ymin * h):int(c_ymax * h), int(c_xmin * w):int(c_xmax * w)]
        if cockpit_crop.size == 0:
            cockpit_crop = frame

        # Normalize resolutions
        face_roi = cv2.resize(face_crop, FACE_INPUT_SIZE)
        body_roi = cv2.resize(body_crop, POSE_INPUT_SIZE)
        cockpit_roi = cv2.resize(cockpit_crop, COCKPIT_INPUT_SIZE)

        return {
            "face_roi": face_roi,
            "body_roi": body_roi,
            "cockpit_roi": cockpit_roi,
        }
