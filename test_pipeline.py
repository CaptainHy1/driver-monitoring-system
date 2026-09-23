"""
Comprehensive Unit & Integration Tests for Multimodal DMS Pipeline
Validates all modules M1 through M9.
"""

import unittest
import numpy as np
import torch

from config import (
    FACE_INPUT_SIZE,
    POSE_INPUT_SIZE,
    COCKPIT_INPUT_SIZE,
    FACE_FEAT_DIM,
    POSE_FEAT_DIM,
    HAND_FEAT_DIM,
    FUSED_FEAT_DIM,
    TEMPORAL_WINDOW_SIZE,
    NUM_CLASSES,
    AlertLevel,
)
from modules.preprocessor import MultiROICropper
from models.face_vit import FaceViT, FaceAnalyzer
from models.pose_detector import PoseDetector
from models.st_gcn import STGCN
from models.object_detector import CockpitObjectDetector
from models.multimodal_fusion import MultimodalFusionLayer
from models.temporal_transformer import TemporalTransformer
from modules.alert_engine import AlertEngine
from modules.visualizer import DMSVisualizer
from pipeline import DMSPipeline


class TestDMSModules(unittest.TestCase):

    def setUp(self):
        self.dummy_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

    def test_m1_preprocessor(self):
        cropper = MultiROICropper()
        rois = cropper.crop_rois(self.dummy_frame)
        self.assertEqual(rois["face_roi"].shape, (FACE_INPUT_SIZE[1], FACE_INPUT_SIZE[0], 3))
        self.assertEqual(rois["body_roi"].shape, (POSE_INPUT_SIZE[1], POSE_INPUT_SIZE[0], 3))
        self.assertEqual(rois["cockpit_roi"].shape, (COCKPIT_INPUT_SIZE[1], COCKPIT_INPUT_SIZE[0], 3))
        print("[TEST PASS] M1: MultiROICropper returns expected tensor resolutions.")

    def test_m2_face_vit(self):
        model = FaceViT(img_size=224, embed_dim=FACE_FEAT_DIM)
        x = torch.randn(2, 3, 224, 224)
        out = model(x)
        self.assertEqual(out["f_face"].shape, (2, FACE_FEAT_DIM))
        self.assertEqual(out["gaze_logits"].shape, (2, 4))
        self.assertEqual(out["eye_logits"].shape, (2, 2))
        self.assertEqual(out["yawn_logits"].shape, (2, 2))

        # Test high-level analyzer
        analyzer = FaceAnalyzer()
        crop = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        res = analyzer.analyze(crop)
        self.assertIn("f_face", res)
        self.assertIn("gaze_direction", res)
        self.assertEqual(res["f_face"].shape, (1, FACE_FEAT_DIM))
        print("[TEST PASS] M2: FaceViT & FaceAnalyzer produce valid embeddings and facial states.")

    def test_m3_pose_detector(self):
        detector = PoseDetector()
        crop = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
        res = detector.detect(crop)
        self.assertEqual(res["keypoints"].shape, (17, 3))
        self.assertIn("posture_state", res)
        print("[TEST PASS] M3: PoseDetector outputs 17 COCO keypoints.")

    def test_m4_st_gcn(self):
        model = STGCN(num_joints=17, out_dim=POSE_FEAT_DIM)
        # Input shape: (B, C, T, V)
        x = torch.randn(2, 3, TEMPORAL_WINDOW_SIZE, 17)
        out = model(x)
        self.assertEqual(out.shape, (2, POSE_FEAT_DIM))
        print("[TEST PASS] M4: ST-GCN forward pass produces f_pose in R^256.")

    def test_m5_object_detector(self):
        detector = CockpitObjectDetector()
        crop = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        res = detector.detect(crop)
        self.assertEqual(res["f_hand"].shape, (1, HAND_FEAT_DIM))
        self.assertIn("hands_on_wheel", res)
        self.assertIn("detected_objects", res)
        print("[TEST PASS] M5: CockpitObjectDetector produces f_hand in R^256.")

    def test_m6_multimodal_fusion(self):
        fusion = MultimodalFusionLayer()
        f_face = torch.randn(2, FACE_FEAT_DIM)
        f_pose = torch.randn(2, POSE_FEAT_DIM)
        f_hand = torch.randn(2, HAND_FEAT_DIM)
        f_fused = fusion(f_face, f_pose, f_hand)
        self.assertEqual(f_fused.shape, (2, FUSED_FEAT_DIM))
        print("[TEST PASS] M6: MultimodalFusionLayer produces f_fused in R^256.")

    def test_m7_temporal_transformer(self):
        model = TemporalTransformer(feat_dim=FUSED_FEAT_DIM, num_classes=NUM_CLASSES)
        x = torch.randn(2, TEMPORAL_WINDOW_SIZE, FUSED_FEAT_DIM)
        out = model(x)
        self.assertEqual(out["logits"].shape, (2, NUM_CLASSES))
        self.assertEqual(out["probabilities"].shape, (2, NUM_CLASSES))
        self.assertEqual(len(out["predicted_class"]), 2)
        print("[TEST PASS] M7: TemporalTransformer predicts distraction classes.")

    def test_m8_alert_engine(self):
        engine = AlertEngine()
        face_info = {"gaze_direction": "forward", "eye_closed": False, "perclos": 0.0}
        object_info = {"hands_on_wheel": "both_hands", "phone_detected": False}
        pose_info = {"posture_state": "normal"}

        # Normal test -> LEVEL_0
        dec = engine.update("C0", "Safe Driving", 0.95, face_info, object_info, pose_info)
        self.assertEqual(dec.level, AlertLevel.LEVEL_0)

        # Simulate prolonged eyes closed -> Escalation to LEVEL_3
        engine.timers["eyes_closed"] = 2.0
        dec_drowsy = engine.update("C2", "Drowsiness", 0.90, face_info, object_info, pose_info)
        self.assertEqual(dec_drowsy.level, AlertLevel.LEVEL_3)
        self.assertTrue(dec_drowsy.trigger_buzzer)
        print("[TEST PASS] M8: AlertEngine escalates to LEVEL_3 upon violation threshold.")

    def test_m9_visualizer_and_json(self):
        visualizer = DMSVisualizer()
        engine = AlertEngine()
        dec = engine.update("C0", "Safe Driving", 0.99, {}, {}, {})
        vis_frame = visualizer.render_hud(self.dummy_frame, dec, {}, {}, {})
        self.assertEqual(vis_frame.shape, self.dummy_frame.shape)

        event = visualizer.build_json_event(1, 30.0, dec, {}, {}, {})
        self.assertIn("timestamp", event)
        self.assertIn("system_state", event)
        self.assertIn("model_assignments", event)
        self.assertIn("action_commands", event)
        print("[TEST PASS] M9: Visualizer and JSON metadata log adhere to srs.md.")

    def test_end_to_end_pipeline(self):
        pipeline = DMSPipeline()
        for i in range(5):
            vis, dec, event = pipeline.process_frame(self.dummy_frame)
            self.assertEqual(vis.shape, self.dummy_frame.shape)
            self.assertIsNotNone(dec)
            self.assertIsNotNone(event)
        print("[TEST PASS] DMSPipeline runs end-to-end without errors.")


if __name__ == "__main__":
    unittest.main()
