import os
import time
from collections import deque
from typing import Dict, Any, Tuple
import numpy as np
import torch

from config import (
    DEVICE,
    TEMPORAL_WINDOW_SIZE,
    FUSED_FEAT_DIM,
    FACE_VIT_WEIGHTS_PATH,
    YOLO_POSE_WEIGHTS_PATH,
    ST_GCN_WEIGHTS_PATH,
    YOLO_OBJECT_WEIGHTS_PATH,
    FUSION_WEIGHTS_PATH,
    TEMPORAL_TRANSFORMER_WEIGHTS_PATH,
)
from modules.preprocessor import MultiROICropper
from models.face_vit import FaceAnalyzer
from models.pose_detector import PoseDetector
from models.st_gcn import STGCN
from models.object_detector import CockpitObjectDetector
from models.multimodal_fusion import MultimodalFusionLayer
from models.temporal_transformer import TemporalTransformer
from modules.alert_engine import AlertEngine, AlertDecision
from modules.visualizer import DMSVisualizer


class DMSPipeline:
    """
    Main Pipeline Coordinator executing the 3 streams + fusion + temporal sequence analysis.
    """

    def __init__(self, device: torch.device = DEVICE):
        self.device = device
        print(f"[DMSPipeline] Đang khởi tạo hệ thống trên thiết bị: {self.device}")

        # [M1] Preprocessor
        self.cropper = MultiROICropper()

        # [M2] Face Stream
        self.face_analyzer = FaceAnalyzer(device=self.device)
        if os.path.exists(FACE_VIT_WEIGHTS_PATH):
            try:
                self.face_analyzer.model.load_state_dict(torch.load(FACE_VIT_WEIGHTS_PATH, map_location=self.device, weights_only=True))
                print(f"[DMSPipeline] ✓ Đã nạp checkpoint FaceViT: {FACE_VIT_WEIGHTS_PATH}")
            except Exception as e:
                print(f"[DMSPipeline] ⚠ Cảnh báo nạp FaceViT: {e}")
        else:
            print(f"[DMSPipeline] ℹ FaceViT: Chưa có checkpoint tại {FACE_VIT_WEIGHTS_PATH}, chạy chế độ zero-shot fallback.")

        # [M3] Pose Keypoints Stream
        pose_weights = YOLO_POSE_WEIGHTS_PATH if os.path.exists(YOLO_POSE_WEIGHTS_PATH) else "yolov8n-pose.pt"
        self.pose_detector = PoseDetector(model_name=pose_weights, device=self.device)
        print(f"[DMSPipeline] ✓ Đã nạp mô hình YOLO-Pose: {pose_weights}")

        # [M4] Skeletal Dynamics Stream (ST-GCN)
        self.st_gcn = STGCN(device=self.device).to(self.device)
        if os.path.exists(ST_GCN_WEIGHTS_PATH):
            try:
                self.st_gcn.load_state_dict(torch.load(ST_GCN_WEIGHTS_PATH, map_location=self.device, weights_only=True))
                print(f"[DMSPipeline] ✓ Đã nạp checkpoint ST-GCN: {ST_GCN_WEIGHTS_PATH}")
            except Exception as e:
                print(f"[DMSPipeline] ⚠ Cảnh báo nạp ST-GCN: {e}")
        else:
            print(f"[DMSPipeline] ℹ ST-GCN: Chưa có checkpoint tại {ST_GCN_WEIGHTS_PATH}, dùng cấu trúc đồ thị chuẩn.")
        self.st_gcn.eval()

        # [M5] Object & Hand Interaction Stream (YOLO)
        obj_weights = YOLO_OBJECT_WEIGHTS_PATH if os.path.exists(YOLO_OBJECT_WEIGHTS_PATH) else "yolov8n.pt"
        self.object_detector = CockpitObjectDetector(model_name=obj_weights, device=self.device)
        print(f"[DMSPipeline] ✓ Đã nạp mô hình YOLO-Object: {obj_weights}")

        # [M6] Multimodal Fusion Layer
        self.fusion_layer = MultimodalFusionLayer().to(self.device)
        if os.path.exists(FUSION_WEIGHTS_PATH):
            try:
                self.fusion_layer.load_state_dict(torch.load(FUSION_WEIGHTS_PATH, map_location=self.device, weights_only=True))
                print(f"[DMSPipeline] ✓ Đã nạp checkpoint Fusion Layer: {FUSION_WEIGHTS_PATH}")
            except Exception as e:
                print(f"[DMSPipeline] ⚠ Cảnh báo nạp Fusion Layer: {e}")
        self.fusion_layer.eval()

        # [M7] Temporal Transformer
        self.temporal_transformer = TemporalTransformer().to(self.device)
        if os.path.exists(TEMPORAL_TRANSFORMER_WEIGHTS_PATH):
            try:
                self.temporal_transformer.load_state_dict(torch.load(TEMPORAL_TRANSFORMER_WEIGHTS_PATH, map_location=self.device, weights_only=True))
                print(f"[DMSPipeline] ✓ Đã nạp checkpoint Temporal Transformer: {TEMPORAL_TRANSFORMER_WEIGHTS_PATH}")
            except Exception as e:
                print(f"[DMSPipeline] ⚠ Cảnh báo nạp Temporal Transformer: {e}")
        self.temporal_transformer.eval()

        # [M8] Alert Engine
        self.alert_engine = AlertEngine()

        # [M9] Visualizer & Logger
        self.visualizer = DMSVisualizer()

        # Sliding Window Buffers
        self.pose_buffer = deque(maxlen=TEMPORAL_WINDOW_SIZE)       # stores (17, 3) arrays
        self.fused_buffer = deque(maxlen=TEMPORAL_WINDOW_SIZE)      # stores (1, 256) tensors

        self.frame_count = 0
        self.fps_timer = time.time()
        self.current_fps = 30.0

    @torch.no_grad()
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, AlertDecision, Dict[str, Any]]:
        """
        Executes end-to-end processing on a single video frame.
        Returns:
          - vis_frame: Frame with HUD overlay
          - decision: AlertDecision
          - json_event: Serialized metadata dictionary
        """
        self.frame_count += 1
        now = time.time()
        elapsed = now - self.fps_timer
        if elapsed > 0.5:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_timer = now

        # -------------------------------------------------------------
        # Step 1 [M1]: Crop Multi-ROIs
        # -------------------------------------------------------------
        rois = self.cropper.crop_rois(frame)
        face_roi = rois["face_roi"]
        body_roi = rois["body_roi"]
        cockpit_roi = rois["cockpit_roi"]

        # -------------------------------------------------------------
        # Step 2 [M2]: Face Stream (Face ViT)
        # -------------------------------------------------------------
        face_info = self.face_analyzer.analyze(face_roi, full_frame=frame)
        f_face = face_info["f_face"]  # (1, 256)

        # -------------------------------------------------------------
        # Step 3 [M3 & M4]: Body/Pose Stream (YOLO-Pose & ST-GCN)
        # -------------------------------------------------------------
        pose_info = self.pose_detector.detect(body_roi)
        kps = pose_info["keypoints"]  # (17, 3)
        self.pose_buffer.append(kps)

        # Build tensor for ST-GCN: shape (1, 3, T, 17)
        while len(self.pose_buffer) < TEMPORAL_WINDOW_SIZE:
            self.pose_buffer.append(kps)

        pose_seq = np.array(list(self.pose_buffer))  # (T, 17, 3)
        # Transpose to (3, T, 17)
        pose_seq = np.transpose(pose_seq, (2, 0, 1))
        pose_tensor = torch.from_numpy(pose_seq).unsqueeze(0).float().to(self.device)  # (1, 3, T, 17)
        f_pose = self.st_gcn(pose_tensor)  # (1, 256)

        # -------------------------------------------------------------
        # Step 4 [M5]: Hands & Object Stream (Fine-tuned YOLO)
        # -------------------------------------------------------------
        # Pass full frame so objects (phone, bottle) anywhere in cabin/hand are detected
        object_info = self.object_detector.detect(cockpit_bgr=frame, driver_keypoints=kps)
        f_hand = object_info["f_hand"]  # (1, 256)

        # -------------------------------------------------------------
        # Step 5 [M6]: Multimodal Fusion
        # -------------------------------------------------------------
        f_fused = self.fusion_layer(f_face, f_pose, f_hand)  # (1, 256)
        self.fused_buffer.append(f_fused)

        # Fill window if starting up
        while len(self.fused_buffer) < TEMPORAL_WINDOW_SIZE:
            self.fused_buffer.append(f_fused)

        # -------------------------------------------------------------
        # Step 6 [M7]: Temporal Transformer Sequence Modeling
        # -------------------------------------------------------------
        fused_window = torch.stack(list(self.fused_buffer), dim=1)  # (1, T, 256)
        temporal_out = self.temporal_transformer(fused_window)
        pred_class = temporal_out["predicted_class"][0]
        pred_label = temporal_out["predicted_label"][0]
        probs = temporal_out["probabilities"][0].cpu().numpy()
        confidence = float(np.max(probs))

        # Grounding fallback for untrained / low-confidence temporal transformer:
        # Prevent random neural logits from triggering false alarms
        if confidence < 0.65:
            if object_info.get("phone_detected", False) or object_info.get("hand_status") == "holding_phone":
                pred_class = "C1"
                pred_label = "Phone Usage"
                confidence = 0.90
            elif face_info.get("eye_closed", False) or face_info.get("yawning", False):
                pred_class = "C2"
                pred_label = "Drowsiness / Yawning"
                confidence = 0.90
            elif "reaching" in pose_info.get("posture_state", ""):
                pred_class = "C3"
                pred_label = "Reaching / Turning"
                confidence = 0.85
            elif object_info.get("drink_detected", False) or object_info.get("hand_status") == "holding_drink":
                pred_class = "C4"
                pred_label = "Eating / Drinking"
                confidence = 0.85
            else:
                pred_class = "C0"
                pred_label = "Safe Driving"
                confidence = 0.95

        # -------------------------------------------------------------
        # Step 7 [M8]: Alert Decision Engine
        # -------------------------------------------------------------
        decision = self.alert_engine.update(
            predicted_class=pred_class,
            predicted_label=pred_label,
            confidence=confidence,
            face_info=face_info,
            object_info=object_info,
            pose_info=pose_info,
        )

        # -------------------------------------------------------------
        # Step 8 [M9]: Visualizer & JSON Event Log
        # -------------------------------------------------------------
        vis_frame = self.visualizer.render_hud(
            frame=frame,
            decision=decision,
            face_info=face_info,
            pose_info=pose_info,
            object_info=object_info,
            fps=self.current_fps,
            frame_id=self.frame_count,
        )

        json_event = self.visualizer.build_json_event(
            frame_id=self.frame_count,
            fps=self.current_fps,
            decision=decision,
            face_info=face_info,
            pose_info=pose_info,
            object_info=object_info,
            confidence=confidence,
        )

        return vis_frame, decision, json_event
