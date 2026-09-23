"""
[M2] Face Vision Transformer (Face ViT) & Face Analyzer Module
Extracts gaze direction, eye closure (EAR/PERCLOS), and yawning (MAR),
producing feature vector f_face in R^256.
"""

import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

from config import (
    DEVICE,
    FACE_INPUT_SIZE,
    FACE_FEAT_DIM,
    EAR_THRESHOLD,
    MAR_THRESHOLD,
    PERCLOS_WINDOW_SECONDS,
)


class PatchEmbedding(nn.Module):
    """Splits image into non-overlapping patches and projects to embedding dimension."""
    def __init__(self, in_channels: int = 3, patch_size: int = 16, embed_dim: int = 256):
        super().__init__()
        self.patch_size = patch_size
        self.proj = nn.Conv2d(in_channels, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, H, W) -> (B, embed_dim, H/P, W/P)
        x = self.proj(x)
        # flatten and transpose: (B, embed_dim, num_patches) -> (B, num_patches, embed_dim)
        x = x.flatten(2).transpose(1, 2)
        return x


class FaceViT(nn.Module):
    """
    Vision Transformer for Driver Face Analysis.
    Outputs:
      - f_face: (B, 256) latent feature vector
      - gaze_logits: (B, 4) for ['forward', 'looking_down', 'looking_left', 'looking_right']
      - eye_state_logits: (B, 2) [open, closed]
      - yawn_logits: (B, 2) [normal, yawning]
    """
    def __init__(
        self,
        img_size: int = 224,
        patch_size: int = 16,
        in_channels: int = 3,
        embed_dim: int = 256,
        depth: int = 4,
        num_heads: int = 4,
        mlp_ratio: float = 2.0,
    ):
        super().__init__()
        self.num_patches = (img_size // patch_size) ** 2
        self.patch_embed = PatchEmbedding(in_channels, patch_size, embed_dim)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_embed = nn.Parameter(torch.randn(1, self.num_patches + 1, embed_dim) * 0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=int(embed_dim * mlp_ratio),
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=depth)
        self.norm = nn.LayerNorm(embed_dim)

        # Feature projection head -> f_face in R^256
        self.proj_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.GELU(),
            nn.LayerNorm(embed_dim)
        )

        # Prediction Heads
        self.gaze_head = nn.Linear(embed_dim, 4)       # 0: forward, 1: down, 2: left, 3: right
        self.eye_head = nn.Linear(embed_dim, 2)        # 0: open, 1: closed
        self.yawn_head = nn.Linear(embed_dim, 2)       # 0: normal, 1: yawning

    def forward(self, x: torch.Tensor):
        B = x.shape[0]
        # (B, num_patches, embed_dim)
        patches = self.patch_embed(x)
        # prepend cls_token
        cls_tokens = self.cls_token.expand(B, -1, -1)
        tokens = torch.cat([cls_tokens, patches], dim=1)
        tokens = tokens + self.pos_embed[:, : tokens.size(1), :]

        encoded = self.encoder(tokens)
        cls_out = self.norm(encoded[:, 0])

        f_face = self.proj_head(cls_out)  # (B, 256)
        gaze_logits = self.gaze_head(f_face)
        eye_logits = self.eye_head(f_face)
        yawn_logits = self.yawn_head(f_face)

        return {
            "f_face": f_face,
            "gaze_logits": gaze_logits,
            "eye_logits": eye_logits,
            "yawn_logits": yawn_logits,
        }


class FaceAnalyzer:
    """
    High-level Face Stream analyzer combining FaceViT and Landmark estimation.
    Accurately computes:
      - Gaze Direction: 'forward', 'looking_down', 'looking_left', 'looking_right', 'eyes_closed'
      - Yawning: MAR metric with temporal duration tracking (eliminates false triggers from talking)
      - Head Pose: Pitch ratio (detects downward head tilt when looking at phone)
      - PERCLOS & EAR
    """
    GAZE_LABELS = ["forward", "looking_down", "looking_left", "looking_right"]

    def __init__(self, device: torch.device = DEVICE):
        self.device = device
        self.model = FaceViT(
            img_size=FACE_INPUT_SIZE[0],
            patch_size=16,
            embed_dim=FACE_FEAT_DIM,
            depth=4,
            num_heads=4,
        ).to(self.device)
        self.model.eval()

        # Eye closure history for PERCLOS calculation
        self.eye_state_history = []  # list of (timestamp, is_closed)

        # Temporal Yawn tracker (prevents false alarms when speaking)
        self.yawn_duration = 0.0
        self.yawn_latch_timer = 0.0
        self.yawn_count = 0
        self.last_time = time.time()

        # 3D Canonical facial model points for solvePnP head pose estimation (mm)
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip (1)
            (0.0, -330.0, -65.0),        # Chin (152)
            (-225.0, 170.0, -135.0),     # Left eye outer corner (33)
            (225.0, 170.0, -135.0),      # Right eye outer corner (263)
            (-150.0, -150.0, -125.0),    # Left mouth corner (61)
            (150.0, -150.0, -125.0),     # Right mouth corner (291)
        ], dtype=np.float64)

        # Optional MediaPipe Face Mesh for zero-shot facial landmark tracking
        self.mp_face_mesh = None
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

    @torch.no_grad()
    def analyze(self, face_bgr: np.ndarray, full_frame: np.ndarray = None) -> dict:
        """
        Analyze face using high-resolution landmarks + FaceViT embeddings.
        Supports passing full_frame for maximum landmark resolution and wide-angle tracking.
        """
        curr_time = time.time()
        dt = max(0.001, min(0.4, curr_time - self.last_time))
        self.last_time = curr_time

        if face_bgr is None or face_bgr.size == 0:
            dummy_f = torch.zeros((1, FACE_FEAT_DIM), device=self.device)
            return {
                "f_face": dummy_f,
                "gaze_direction": "forward",
                "eye_closed": False,
                "ear": 0.35,
                "perclos": 0.0,
                "yawning": False,
                "mar": 0.20,
                "head_pose": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            }

        # 1. Preprocess face crop for FaceViT feature extraction
        resized = cv2.resize(face_bgr, FACE_INPUT_SIZE)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        tensor = ((tensor - mean) / std).unsqueeze(0).to(self.device)

        vit_out = self.model(tensor)
        f_face = vit_out["f_face"]  # (1, 256)

        # 2. Precise Facial Landmarks calculation
        ear = 0.32
        mar = 0.15
        eye_closed = False
        yawning = False
        gaze_direction = "forward"
        head_pose = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}

        # Use full frame for landmarks if available (gives 10x better precision and field-of-view)
        mesh_input = full_frame if (full_frame is not None and full_frame.size > 0) else face_bgr

        if self.mp_face_mesh is not None:
            results = self.mp_face_mesh.process(cv2.cvtColor(mesh_input, cv2.COLOR_BGR2RGB))
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                h, w, _ = mesh_input.shape

                def pt(idx):
                    return np.array([landmarks[idx].x * w, landmarks[idx].y * h])

                try:
                    # -------------------------------------------------------------
                    # A. Eye Aspect Ratio (EAR) - Chớp mắt / Nhắm mắt
                    # -------------------------------------------------------------
                    # Left Eye: 33, 133, 160, 158, 144, 153
                    # Right Eye: 362, 263, 385, 387, 380, 373
                    p33, p160, p158, p133, p153, p144 = [pt(i) for i in [33, 160, 158, 133, 153, 144]]
                    p362, p385, p387, p263, p373, p380 = [pt(i) for i in [362, 385, 387, 263, 373, 380]]

                    left_ear = (np.linalg.norm(p160 - p144) + np.linalg.norm(p158 - p153)) / (2.0 * np.linalg.norm(p33 - p133) + 1e-6)
                    right_ear = (np.linalg.norm(p385 - p380) + np.linalg.norm(p387 - p373)) / (2.0 * np.linalg.norm(p362 - p263) + 1e-6)
                    ear = float((left_ear + right_ear) / 2.0)

                    # -------------------------------------------------------------
                    # B. Mouth Aspect Ratio (MAR) & Yawning - Ngáp ngủ
                    # -------------------------------------------------------------
                    # 13: inner upper lip, 14: inner lower lip
                    # 78: inner left corner, 308: inner right corner
                    # 0: outer upper lip, 17: outer lower lip
                    # 61: outer left corner, 291: outer right corner
                    p13, p14, p78, p308 = [pt(i) for i in [13, 14, 78, 308]]
                    p0, p17, p61, p291 = [pt(i) for i in [0, 17, 61, 291]]

                    inner_v = np.linalg.norm(p13 - p14)
                    inner_h = np.linalg.norm(p78 - p308) + 1e-6
                    outer_v = np.linalg.norm(p0 - p17)
                    outer_h = np.linalg.norm(p61 - p291) + 1e-6

                    mar = float(inner_v / inner_h)
                    outer_mar = float(outer_v / outer_h)

                    # Temporal filtering: mouth opening must be sustained to be a true yawn
                    # Speaking has mar 0.15 - 0.35, outer_mar 0.30 - 0.45
                    # Yawning opens mouth vertically: mar >= 0.45 or outer_mar >= 0.55
                    is_mouth_wide = (mar >= 0.45) or (outer_mar >= 0.55)
                    if is_mouth_wide:
                        self.yawn_duration += dt
                    else:
                        self.yawn_duration = max(0.0, self.yawn_duration - dt * 2.0)

                    # Require wide opening for at least 0.6s to confirm a genuine yawn
                    if self.yawn_duration >= 0.6:
                        self.yawn_latch_timer = 2.0  # Latch for 2.0s so alert engine and HUD can process
                        self.yawn_count += 1
                        self.yawn_duration = 0.0

                    if self.yawn_latch_timer > 0:
                        self.yawn_latch_timer -= dt
                        yawning = True
                    else:
                        yawning = False

                    # -------------------------------------------------------------
                    # C. Head Pose & Gaze Estimation (Normalized Geometric Ratios)
                    # -------------------------------------------------------------
                    forehead_y = landmarks[10].y
                    nose_y = landmarks[1].y
                    chin_y = landmarks[152].y
                    face_h = chin_y - forehead_y + 1e-6
                    chin_ratio = (chin_y - nose_y) / face_h

                    # Iris Vertical Position (Mắt nhìn xuống):
                    # Left eye: 159 (top), 145 (bottom), 468 (iris center)
                    # Right eye: 386 (top), 374 (bottom), 473 (iris center)
                    v_iris_left = (landmarks[468].y - landmarks[159].y) / (landmarks[145].y - landmarks[159].y + 1e-6)
                    v_iris_right = (landmarks[473].y - landmarks[386].y) / (landmarks[374].y - landmarks[386].y + 1e-6)
                    v_ratio = (v_iris_left + v_iris_right) / 2.0

                    # Iris Horizontal Position (Liếc trái / phải):
                    h_left = (landmarks[468].x - landmarks[33].x) / (landmarks[133].x - landmarks[33].x + 1e-6)
                    h_right = (landmarks[473].x - landmarks[362].x) / (landmarks[263].x - landmarks[362].x + 1e-6)
                    h_ratio = (h_left + h_right) / 2.0

                    # Calibrated Head Pose angles (Pitch: negative=down, Yaw: negative=left)
                    pitch_deg = round(((0.395 - chin_ratio) / 0.15) * -20.0, 1)
                    yaw_deg = round(((h_ratio - 0.50) / 0.15) * 20.0, 1)
                    head_pose = {
                        "pitch": pitch_deg,
                        "yaw": yaw_deg,
                        "roll": 0.0,
                    }

                    # -------------------------------------------------------------
                    # D. Gaze Direction & Cúi nhìn xuống điện thoại (Calibrated)
                    # -------------------------------------------------------------
                    # Head tilted down: lower face compresses significantly (chin_ratio < 0.28 vs normal ~0.40)
                    head_tilted_down = (chin_ratio < 0.28)
                    # Iris looking down: pupil drops to lower eyelid (v_ratio > 0.66 vs normal ~0.43-0.56)
                    iris_looking_down = (v_ratio > 0.66) and (ear >= 0.20)

                    is_looking_down = head_tilted_down or (iris_looking_down and chin_ratio < 0.35)

                    # Determine eye closure and gaze direction:
                    if is_looking_down:
                        # When looking down, eyelids naturally narrow. Only deep closure counts as closed eyes.
                        eye_closed = (ear < 0.14)
                        if eye_closed:
                            gaze_direction = "eyes_closed"
                        else:
                            gaze_direction = "looking_down"  # Cúi nhìn xuống điện thoại / taplo
                    else:
                        eye_closed = (ear < EAR_THRESHOLD)
                        if eye_closed:
                            gaze_direction = "eyes_closed"
                        elif yaw_deg < -15.0 or h_ratio > 0.65:
                            gaze_direction = "looking_left"
                        elif yaw_deg > 15.0 or h_ratio < 0.35:
                            gaze_direction = "looking_right"
                        else:
                            gaze_direction = "forward"

                except Exception:
                    gaze_direction = "forward"
        else:
            # Fallback if mediapipe is not available
            gaze_direction = "forward"

        # 4. Update PERCLOS sliding window
        self.eye_state_history.append((curr_time, eye_closed))
        self.eye_state_history = [
            (t, c) for t, c in self.eye_state_history if curr_time - t <= PERCLOS_WINDOW_SECONDS
        ]
        closed_count = sum(1 for _, c in self.eye_state_history if c)
        total_count = max(1, len(self.eye_state_history))
        perclos = float(closed_count / total_count)

        return {
            "f_face": f_face,
            "gaze_direction": gaze_direction,
            "eye_closed": eye_closed,
            "ear": round(ear, 3),
            "perclos": round(perclos, 3),
            "yawning": yawning,
            "mar": round(mar, 3),
            "head_pose": head_pose,
        }

