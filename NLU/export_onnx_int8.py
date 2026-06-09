import argparse
import os
import sys
import numpy as np

import torch
import onnx
import onnxruntime as ort
from onnxruntime.quantization import (
    quantize_dynamic,
    QuantType,
)

from nlp.model import MDeBERTaNLU
from config.labels import ENCODER_MODEL    

class SquireONNXWrapper(torch.nn.Module):
    def __init__(self, model: MDeBERTaNLU):
        super().__init__()
        self.model = model

    def forward(
        self,
        input_ids: torch.Tensor,      
        attention_mask: torch.Tensor,   
    ):
        out = self.model(input_ids, attention_mask)
        return (
            out["action_logits"],  
            out["object_logits"],  
            out["ner_emissions"],  
        )

def load_model(checkpoint_path: str) -> MDeBERTaNLU:
    print(f"[1/5] Loading checkpoint: {checkpoint_path}")
    model = MDeBERTaNLU()
    state = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    print(f"      Parameters: {sum(p.numel() for p in model.parameters()):,}")
    return model


def make_dummy_inputs(batch_size: int = 1, seq_len: int = 64):
    """Dummy tokenizer output for tracing (values don't matter for structure)."""
    input_ids      = torch.zeros((batch_size, seq_len), dtype=torch.long)
    attention_mask = torch.ones((batch_size, seq_len), dtype=torch.long)
    return input_ids, attention_mask


def export_fp32(wrapper: SquireONNXWrapper, fp32_path: str, opset: int):
    print(f"[2/5] Exporting FP32 ONNX → {fp32_path}")
    dummy = make_dummy_inputs()

    torch.onnx.export(
        wrapper,
        dummy,
        fp32_path,
        dynamo=False,
        opset_version=opset,
        input_names=["input_ids", "attention_mask"],
        output_names=["action_logits", "object_logits", "ner_emissions"],
        dynamic_axes={
            "input_ids":       {0: "batch", 1: "seq"},
            "attention_mask":  {0: "batch", 1: "seq"},
            "action_logits":   {0: "batch"},
            "object_logits":   {0: "batch"},
            "ner_emissions":   {0: "batch", 1: "seq"},
        },
        do_constant_folding=True,
        export_params=True,
    )
    size_mb = os.path.getsize(fp32_path) / 1_048_576
    print(f"      FP32 size: {size_mb:.1f} MB")


def quantize_int8(fp32_path: str, int8_path: str):
    print(f"[3/5] Quantizing to INT8 → {int8_path}")

    model_proto = onnx.load(fp32_path)
    nodes_to_exclude = []

    quantize_dynamic(
        model_input=fp32_path,
        model_output=int8_path,
        weight_type=QuantType.QInt8,
        nodes_to_exclude=nodes_to_exclude,
        per_channel=False,        
    )

    size_fp32 = os.path.getsize(fp32_path) / 1_048_576
    size_int8 = os.path.getsize(int8_path) / 1_048_576
    ratio     = size_fp32 / size_int8 if size_int8 else 0
    print(f"      FP32: {size_fp32:.1f} MB  →  INT8: {size_int8:.1f} MB  "
          f"(~{ratio:.1f}× smaller)")


def verify(int8_path: str):
    print(f"[4/5] Verifying INT8 model …")
    sess_opts = ort.SessionOptions()
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    sess = ort.InferenceSession(int8_path, sess_opts,
                                providers=["CPUExecutionProvider"])

    input_ids      = np.zeros((1, 64), dtype=np.int64)
    attention_mask = np.ones((1, 64),  dtype=np.int64)

    action_logits, object_logits, ner_emissions = sess.run(
        None,
        {"input_ids": input_ids, "attention_mask": attention_mask},
    )

    action_pred = int(np.argmax(action_logits[0]))
    object_pred = int(np.argmax(object_logits[0]))
    print(f"      action_logits shape : {action_logits.shape}")
    print(f"      object_logits shape : {object_logits.shape}")
    print(f"      ner_emissions shape : {ner_emissions.shape}")
    print(f"      Dummy prediction    : action={action_pred}  object={object_pred}")
    print("      ✓ Verification passed")


def print_summary(output_dir: str):
    print(f"\n[5/5] Export complete — files in {output_dir}/")
    for fname in ["squire_fp32.onnx", "squire_int8.onnx"]:
        fpath = os.path.join(output_dir, fname)
        if os.path.exists(fpath):
            size_mb = os.path.getsize(fpath) / 1_048_576
            print(f"      {fname:<25} {size_mb:>7.1f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Export Squire MDeBERTaNLU → ONNX INT8"
    )
    parser.add_argument(
        "--checkpoint", required=True,
        help="Path to trained .pt checkpoint (state_dict)"
    )
    parser.add_argument(
        "--output_dir", default="./onnx_export",
        help="Directory for output ONNX files (created if missing)"
    )
    parser.add_argument(
        "--opset", type=int, default=17,
        help="ONNX opset version (default 17; use 14 for older runtimes)"
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    fp32_path = os.path.join(args.output_dir, "squire_fp32.onnx")
    int8_path = os.path.join(args.output_dir, "squire_int8.onnx")

    model   = load_model(args.checkpoint)
    wrapper = SquireONNXWrapper(model)
    wrapper.eval()

    export_fp32(wrapper, fp32_path, args.opset)
    quantize_int8(fp32_path, int8_path)
    verify(int8_path)
    print_summary(args.output_dir)


if __name__ == "__main__":
    main()
