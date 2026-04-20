#!/usr/bin/env python3
"""
Export standard torchvision CNNs to ONNX (PyTorch).

Install: pip install torch torchvision onnx
  (PyTorch 2.x ONNX export requires the ``onnx`` package.)

Usage:
  python3 compare/scripts/export_resnet_mobilenet_onnx.py
  OUT_DIR=/tmp/onnx python3 compare/scripts/export_resnet_mobilenet_onnx.py
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        import torch
        import torchvision.models as models
    except ImportError:
        print(
            "Need PyTorch: pip install torch torchvision\n"
            "See https://pytorch.org/get-started/locally/",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        import onnx  # noqa: F401 — required by torch.onnx.export on recent PyTorch
    except ImportError:
        print(
            "Need ONNX Python package: pip install onnx\n"
            "(torch.onnx.export raises OnnxExporterError without it.)",
            file=sys.stderr,
        )
        sys.exit(1)

    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = os.environ.get("OUT_DIR", os.path.join(repo, "compare", "models", "onnx"))
    os.makedirs(out_dir, exist_ok=True)

    # Same dummy input shape for both (NCHW)
    dummy = torch.randn(1, 3, 224, 224)
    opset = int(os.environ.get("ONNX_OPSET", "17"))

    specs = [
        ("resnet50", models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)),
        ("mobilenet_v2", models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)),
    ]

    for name, model in specs:
        model.eval()
        path = os.path.join(out_dir, f"{name}.onnx")
        torch.onnx.export(
            model,
            dummy,
            path,
            input_names=["input"],
            output_names=["logits"],
            dynamic_axes={
                "input": {0: "batch"},
                "logits": {0: "batch"},
            },
            opset_version=opset,
        )
        print(f"Wrote {path}")

    print(f"\nDone. OUT_DIR={out_dir}")


if __name__ == "__main__":
    main()
