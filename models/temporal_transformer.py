"""
[M7] Temporal Transformer for Sequence Modeling
Processes a sliding window of T fused frames (e.g. T=30 frames, ~1 second of video)
to capture temporal dependencies and output distraction class probabilities.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from config import (
    FUSED_FEAT_DIM,
    TEMPORAL_WINDOW_SIZE,
    NUM_CLASSES,
    DISTRACTION_CLASSES,
    DEVICE,
)


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for sequence tokens."""
    def __init__(self, d_model: int, max_len: int = 200):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, d_model)
        return x + self.pe[:, : x.size(1), :]


class TemporalTransformer(nn.Module):
    """
    Temporal Transformer Classifier.
    Input: (B, T, 256) where T is window size (e.g. 30 frames).
    Output:
      - logits: (B, 6)
      - probabilities: (B, 6)
      - predicted_class: list of class codes (e.g. ['C0'])
      - predicted_label: list of class names (e.g. ['Safe Driving'])
    """
    def __init__(
        self,
        feat_dim: int = FUSED_FEAT_DIM,
        num_classes: int = NUM_CLASSES,
        num_layers: int = 2,
        nhead: int = 4,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.pos_encoder = PositionalEncoding(d_model=feat_dim, max_len=120)

        # Learnable classification token
        self.cls_token = nn.Parameter(torch.zeros(1, 1, feat_dim))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=feat_dim,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.norm = nn.LayerNorm(feat_dim)

        self.classifier = nn.Sequential(
            nn.Linear(feat_dim, feat_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(feat_dim // 2, num_classes)
        )

    def forward(self, x: torch.Tensor) -> dict:
        """
        x: (B, T, 256)
        """
        B, T, D = x.shape
        cls_tokens = self.cls_token.expand(B, -1, -1)  # (B, 1, D)
        x = torch.cat([cls_tokens, x], dim=1)         # (B, T+1, D)
        x = self.pos_encoder(x)

        encoded = self.transformer_encoder(x)
        cls_out = self.norm(encoded[:, 0])             # (B, D)

        logits = self.classifier(cls_out)              # (B, NUM_CLASSES)
        probs = F.softmax(logits, dim=-1)

        class_keys = list(DISTRACTION_CLASSES.keys())
        pred_indices = torch.argmax(probs, dim=-1).cpu().numpy().tolist()
        pred_classes = [class_keys[idx] for idx in pred_indices]
        pred_labels = [DISTRACTION_CLASSES[k] for k in pred_classes]

        return {
            "logits": logits,
            "probabilities": probs,
            "predicted_class": pred_classes,
            "predicted_label": pred_labels,
        }
