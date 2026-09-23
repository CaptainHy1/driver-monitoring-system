"""
[M6] Multimodal Fusion Layer
Fuses heterogeneous feature vectors from Face (M2), Pose (M4), and Hand/Object (M5) streams
into a unified representation f_fused in R^256.
"""

import torch
import torch.nn as nn
from config import (
    FACE_FEAT_DIM,
    POSE_FEAT_DIM,
    HAND_FEAT_DIM,
    FUSED_FEAT_DIM,
    DEVICE,
)


class CrossModalAttention(nn.Module):
    """Computes cross-modal attention weights between streams."""
    def __init__(self, feat_dim: int = 256):
        super().__init__()
        self.query = nn.Linear(feat_dim, feat_dim)
        self.key = nn.Linear(feat_dim, feat_dim)
        self.value = nn.Linear(feat_dim, feat_dim)
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, face_feat: torch.Tensor, pose_feat: torch.Tensor, hand_feat: torch.Tensor) -> torch.Tensor:
        # Stack streams: (B, 3, feat_dim)
        tokens = torch.stack([face_feat, pose_feat, hand_feat], dim=1)
        Q = self.query(tokens)
        K = self.key(tokens)
        V = self.value(tokens)

        scores = torch.bmm(Q, K.transpose(1, 2)) / (face_feat.size(-1) ** 0.5)
        attn = self.softmax(scores)
        out = torch.bmm(attn, V)  # (B, 3, feat_dim)
        return out.flatten(start_dim=1)  # (B, 3 * feat_dim)


class MultimodalFusionLayer(nn.Module):
    """
    Fuses f_face, f_pose, and f_hand.
    Output: f_fused in R^256.
    """
    def __init__(
        self,
        face_dim: int = FACE_FEAT_DIM,
        pose_dim: int = POSE_FEAT_DIM,
        hand_dim: int = HAND_FEAT_DIM,
        out_dim: int = FUSED_FEAT_DIM,
        use_attention: bool = True,
    ):
        super().__init__()
        self.use_attention = use_attention
        concat_dim = face_dim + pose_dim + hand_dim

        if self.use_attention:
            self.attn = CrossModalAttention(feat_dim=out_dim)

        self.projection = nn.Sequential(
            nn.Linear(concat_dim, out_dim * 2),
            nn.LayerNorm(out_dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(out_dim * 2, out_dim),
            nn.LayerNorm(out_dim),
        )

    def forward(
        self,
        f_face: torch.Tensor,
        f_pose: torch.Tensor,
        f_hand: torch.Tensor,
    ) -> torch.Tensor:
        """
        f_face: (B, 256)
        f_pose: (B, 256)
        f_hand: (B, 256)
        returns f_fused: (B, 256)
        """
        if self.use_attention:
            # (B, 3 * 256)
            fused_input = self.attn(f_face, f_pose, f_hand)
        else:
            fused_input = torch.cat([f_face, f_pose, f_hand], dim=-1)

        f_fused = self.projection(fused_input)
        return f_fused
