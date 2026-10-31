"""
[M4] Spatial-Temporal Graph Convolutional Network (ST-GCN)
Analyzes spatial skeletal relationships and temporal movement dynamics,
producing feature vector f_pose in R^256.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from config import POSE_FEAT_DIM, TEMPORAL_WINDOW_SIZE, DEVICE


# 17 COCO Keypoints Graph Topology
COCO_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # Head
    (0, 5), (0, 6),                  # Neck/Head to Shoulders
    (5, 6),                          # Between Shoulders
    (5, 7), (7, 9),                  # Left arm: Shoulder -> Elbow -> Wrist
    (6, 8), (8, 10),                 # Right arm: Shoulder -> Elbow -> Wrist
    (5, 11), (6, 12),                # Shoulders to Hips
    (11, 12),                        # Between Hips
    (11, 13), (13, 15),              # Left Leg
    (12, 14), (14, 16)               # Right Leg
]


def build_normalized_adjacency(num_nodes: int = 17, edges = COCO_EDGES) -> torch.Tensor:
    """Builds symmetrically normalized adjacency matrix with self-loops: D^(-1/2) A D^(-1/2)"""
    A = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    # Self-connections
    for i in range(num_nodes):
        A[i, i] = 1.0
    # Symmetric edges
    for u, v in edges:
        A[u, v] = 1.0
        A[v, u] = 1.0

    # Degree matrix
    degree = np.sum(A, axis=1)
    d_inv_sqrt = np.power(degree, -0.5)
    d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.0
    D_inv = np.diag(d_inv_sqrt)
    A_norm = D_inv.dot(A).dot(D_inv)
    return torch.from_numpy(A_norm).float()


class SpatialGraphConv(nn.Module):
    """Spatial Graph Convolution across 17 skeletal joints."""
    def __init__(self, in_channels: int, out_channels: int, A: torch.Tensor):
        super().__init__()
        self.register_buffer("A", A)
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        self.bn = nn.BatchNorm2d(out_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, T, V)
        # multiply adjacency matrix A (V, V) on the joint dimension
        # x_A = einsum('bctv, vw -> bctw')
        x_A = torch.einsum("bctv, vw -> bctw", x, self.A)
        out = self.conv(x_A)
        out = self.bn(out)
        return out


class STGCNBlock(nn.Module):
    """Single Spatial-Temporal Graph Convolutional Unit."""
    def __init__(self, in_channels: int, out_channels: int, A: torch.Tensor, stride: int = 1):
        super().__init__()
        self.sgcn = SpatialGraphConv(in_channels, out_channels, A)
        # Temporal Convolution across T frames (kernel_size=9 along time, 1 along joints)
        self.tgcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=(9, 1),
                padding=((9 - 1) // 2, 0),
                stride=(stride, 1)
            ),
            nn.BatchNorm2d(out_channels),
        )

        if in_channels != out_channels or stride != 1:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.residual = nn.Identity()

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.residual(x)
        x = self.sgcn(x)
        x = self.tgcn(x)
        x = self.relu(x + res)
        return x


class STGCN(nn.Module):
    """
    ST-GCN for Driver Action and Posture Dynamics.
    Input: (B, 3, T, 17) -> (Batch, (x, y, conf), Time Window, 17 Joints)
    Output: f_pose in R^256
    """
    def __init__(
        self,
        in_channels: int = 3,
        num_joints: int = 17,
        out_dim: int = POSE_FEAT_DIM,
        device: torch.device = DEVICE
    ):
        super().__init__()
        self.device = device
        self.num_joints = num_joints
        A = build_normalized_adjacency(num_joints, COCO_EDGES).to(device)

        # ST-GCN Network layers
        self.data_bn = nn.BatchNorm1d(in_channels * num_joints)

        self.stgcn1 = STGCNBlock(in_channels, 64, A, stride=1)
        self.stgcn2 = STGCNBlock(64, 128, A, stride=2)
        self.stgcn3 = STGCNBlock(128, 256, A, stride=2)

        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.proj_head = nn.Sequential(
            nn.Linear(256, out_dim),
            nn.LayerNorm(out_dim),
            nn.GELU()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, C, T, V) = (Batch, 3, 30, 17)
        returns f_pose: (B, out_dim) = (B, 256)
        """
        B, C, T, V = x.shape
        # Flatten spatial joints for initial batch norm
        x_perm = x.permute(0, 1, 3, 2).contiguous().view(B, C * V, T)
        x_bn = self.data_bn(x_perm)
        x = x_bn.view(B, C, V, T).permute(0, 1, 3, 2).contiguous()  # (B, C, T, V)

        x = self.stgcn1(x)
        x = self.stgcn2(x)
        x = self.stgcn3(x)  # (B, 256, T', 17)

        # Global average pooling across time and joint nodes
        pooled = self.pool(x).view(B, -1)  # (B, 256)
        f_pose = self.proj_head(pooled)     # (B, 256)
        return f_pose
