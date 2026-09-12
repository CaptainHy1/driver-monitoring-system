"""
Script xuất mô hình TCN đã huấn luyện sang định dạng ONNX.
Sử dụng trọng số đã lưu tại weights/tcn_dms.pth.
"""

import os
import sys
import torch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from config import TCN_CONFIG, TCN_WEIGHTS_PATH, TCN_ONNX_PATH
from models.tcn import TCNModel

def export():
    print("=" * 60)
    print("📦 ĐANG XUẤT MÔ HÌNH TCN SANG ONNX...")
    print("=" * 60)

    if not os.path.exists(TCN_WEIGHTS_PATH):
        print(f"❌ Không tìm thấy file trọng số: {TCN_WEIGHTS_PATH}")
        return

    device = torch.device("cpu")
    model = TCNModel(
        input_size=TCN_CONFIG["input_channels"],
        num_classes=TCN_CONFIG["num_classes"],
        num_channels=TCN_CONFIG["num_channels"],
        kernel_size=TCN_CONFIG["kernel_size"],
        dropout=0.0
    ).to(device)

    model.load_state_dict(torch.load(TCN_WEIGHTS_PATH, map_location=device))
    model.eval()

    dummy_input = torch.randn(1, TCN_CONFIG["input_channels"], 30, device=device)

    os.makedirs(os.path.dirname(TCN_ONNX_PATH), exist_ok=True)
    torch.onnx.export(
        model,
        dummy_input,
        TCN_ONNX_PATH,
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["feature_sequence"],
        output_names=["class_logits"]
    )
    print(f"✅ Đã xuất thành công sang file ONNX: {TCN_ONNX_PATH}")

    # Kiểm thử lại bằng ONNX Runtime
    import onnxruntime as ort
    session = ort.InferenceSession(TCN_ONNX_PATH, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    outs = session.run(None, {input_name: dummy_input.numpy()})
    print(f"✅ Kiểm thử ONNX Runtime thành công! Output shape: {outs[0].shape}")
    print("=" * 60)

if __name__ == "__main__":
    export()
