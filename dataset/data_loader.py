"""
Module Data Loader cho PyTorch xử lý tập dữ liệu chuỗi thời gian.
Chuyển đổi dữ liệu sang định dạng Channel-First (B, Channels=12, Length=30).
"""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

class SequenceDataset(Dataset):
    def __init__(self, npz_path):
        data = np.load(npz_path)
        self.X = data["X"]  # Shape: (N, 30, 12)
        self.y = data["y"]  # Shape: (N,)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        # Chuyển đổi từ (Length=30, Channels=12) sang (Channels=12, Length=30) cho Conv1D
        x_seq = np.transpose(self.X[idx]).astype(np.float32)  # Shape (12, 30)
        y_label = int(self.y[idx])

        return torch.from_numpy(x_seq), torch.tensor(y_label, dtype=torch.long)

def get_dataloaders(train_path, val_path, batch_size=32):
    """Tạo DataLoader cho quá trình huấn luyện và đánh giá"""
    train_dataset = SequenceDataset(train_path)
    val_dataset = SequenceDataset(val_path)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader
