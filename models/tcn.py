"""
Kiến trúc mô hình Temporal Convolutional Network (TCN) bằng PyTorch.
Sử dụng Dilated Causal 1D Convolutions và Residual Blocks.
Không nhìn trước tương lai (Causality) và mở rộng trường nhìn quá khứ (Dilated receptive field).
"""

import torch
import torch.nn as nn
from torch.nn.utils import weight_norm

class Chomp1d(nn.Module):
    """
    Cắt bỏ phần đệm ở tương lai (right padding) để đảm bảo tính nhân quả thời gian (Causality).
    Tín hiệu tại thời điểm t chỉ phụ thuộc vào thời điểm <= t.
    """
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        if self.chomp_size == 0:
            return x
        return x[:, :, :-self.chomp_size].contiguous()

class TemporalBlock(nn.Module):
    """
    Khối Temporal Residual Block gồm:
    - 2 lớp Dilated Causal Conv1D
    - Chomp1D cắt padding tương lai
    - BatchNorm1D + ReLU + Dropout
    - Kết nối phần dư (Residual Connection)
    """
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(TemporalBlock, self).__init__()

        self.conv1 = nn.Conv1d(
            n_inputs, n_outputs, kernel_size,
            stride=stride, padding=padding, dilation=dilation
        )
        self.chomp1 = Chomp1d(padding)
        self.bn1 = nn.BatchNorm1d(n_outputs)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(
            n_outputs, n_outputs, kernel_size,
            stride=stride, padding=padding, dilation=dilation
        )
        self.chomp2 = Chomp1d(padding)
        self.bn2 = nn.BatchNorm1d(n_outputs)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(
            self.conv1, self.chomp1, self.bn1, self.relu1, self.dropout1,
            self.conv2, self.chomp2, self.bn2, self.relu2, self.dropout2
        )

        # 1x1 Convolution nếu số channel vào và ra khác nhau để cộng residual
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()
        self.init_weights()

    def init_weights(self):
        nn.init.kaiming_normal_(self.conv1.weight, mode='fan_out', nonlinearity='relu')
        nn.init.kaiming_normal_(self.conv2.weight, mode='fan_out', nonlinearity='relu')
        if self.downsample is not None:
            nn.init.kaiming_normal_(self.downsample.weight, mode='fan_out', nonlinearity='relu')

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TemporalConvNet(nn.Module):
    """
    Mạng xếp chồng nhiều TemporalBlock với dilation tăng dần theo cấp số nhân 2:
    dilation = [1, 2, 4, 8,...]
    """
    def __init__(self, num_inputs, num_channels, kernel_size=3, dropout=0.2):
        super(TemporalConvNet, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = num_inputs if i == 0 else num_channels[i - 1]
            out_channels = num_channels[i]
            padding = (kernel_size - 1) * dilation_size
            layers.append(
                TemporalBlock(
                    in_channels, out_channels, kernel_size,
                    stride=1, dilation=dilation_size, padding=padding,
                    dropout=dropout
                )
            )
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

class TCNModel(nn.Module):
    """
    Mô hình phân loại chuỗi thời gian hoàn chỉnh cho Driver Monitoring System:
    Đầu vào: Tensor (Batch, Features=12, Seq_Len=30)
    Đầu ra: Logits (Batch, Num_Classes=6)
    """
    def __init__(self, input_size=12, num_classes=6, num_channels=None, kernel_size=3, dropout=0.2):
        super(TCNModel, self).__init__()
        if num_channels is None:
            num_channels = [32, 64, 64, 128]

        self.tcn = TemporalConvNet(input_size, num_channels, kernel_size=kernel_size, dropout=dropout)
        
        # Lớp phân loại: lấy vector tại bước thời gian cuối cùng + Global Pooling kết hợp
        last_channel = num_channels[-1]
        self.classifier = nn.Sequential(
            nn.Linear(last_channel, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        # x: [B, C, L]
        features = self.tcn(x)  # [B, last_channel, L]
        
        # Sử dụng đặc trưng bước thời gian cuối cùng (thời điểm hiện tại t)
        last_step = features[:, :, -1]  # [B, last_channel]
        
        logits = self.classifier(last_step)  # [B, num_classes]
        return logits
