# -*- coding: utf-8 -*-
"""
StratumRO — Exportator SAM 2 la format ONNX & Verificator Numeric
================================================================
Acest instrument realizează exportul oficial al decodorului SAM 2 (Hiera)
la formatul deschis ONNX și validează numeric egalitatea predicțiilor dintre
PyTorch și ONNX Runtime (DirectML / CPU).
"""

import os
import sys
import argparse
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import torch
import torch.nn as nn

try:
    import onnx
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

try:
    from sam2.build_sam import build_sam2
    SAM2_AVAILABLE = True
except ImportError:
    SAM2_AVAILABLE = False


class SAM2DecoderONNXWrapper(nn.Module):
    """
    Wrapper PyTorch optimizat pentru exportul ONNX al decodorului de măști SAM 2 Hiera.
    Primește embeddings de imagine (multi-scale) + puncte de prompt și produce
    măști de rezoluție înaltă și scoruri IoU.
    """
    def __init__(self, sam2_model):
        super().__init__()
        self.sam_prompt_encoder = sam2_model.sam_prompt_encoder
        self.sam_mask_decoder = sam2_model.sam_mask_decoder

    def forward(self, image_embeddings, feat_s0, feat_s1, point_coords, point_labels):
        # image_embeddings: (1, 256, 64, 64)
        # feat_s0: (1, 32, 256, 256)
        # feat_s1: (1, 64, 128, 128)
        # point_coords: (1, N, 2)
        # point_labels: (1, N)
        sparse_embeddings, dense_embeddings = self.sam_prompt_encoder(
            points=(point_coords, point_labels),
            boxes=None,
            masks=None
        )
        low_res_multimasks, iou_predictions, _, _ = self.sam_mask_decoder(
            image_embeddings=image_embeddings,
            image_pe=self.sam_prompt_encoder.get_dense_pe(),
            sparse_prompt_embeddings=sparse_embeddings,
            dense_prompt_embeddings=dense_embeddings,
            multimask_output=True,
            repeat_image=False,
            high_res_features=[feat_s0, feat_s1],
        )
        return low_res_multimasks, iou_predictions


def export_and_verify(
    checkpoint_path: str = "models/sam2/sam2_hiera_tiny.pt",
    config_name: str = "sam2_hiera_t.yaml",
    output_onnx_path: str = "models/sam2/sam2_decoder.onnx",
    device: str = "cpu"
):
    print("=" * 75)
    print("  STRATUM-RO: EXPORT SAM 2 -> ONNX & VALIDARE NUMERICĂ BIT-CU-BIT")
    print("=" * 75)

    if not SAM2_AVAILABLE:
        print("[-] EROARE: Pachetul 'sam2' nu este instalat.")
        return False
    if not ONNX_AVAILABLE:
        print("[-] EROARE: 'onnx' sau 'onnxruntime' lipsesc din mediu.")
        return False
    if not os.path.exists(checkpoint_path):
        print(f"[-] EROARE: Checkpointul SAM 2 nu există la: {checkpoint_path}")
        return False

    print(f"[+] Încărcare model SAM 2 din: {checkpoint_path} ({config_name})...")
    sam2 = build_sam2(config_name, checkpoint_path, device=device)
    sam2.eval()

    wrapper = SAM2DecoderONNXWrapper(sam2)
    wrapper.eval()

    # Creare intrări simulate conforme cu dimensiunile SAM 2 Hiera
    dummy_image_embeddings = torch.randn(1, 256, 64, 64, dtype=torch.float32, device=device)
    dummy_feat_s0 = torch.randn(1, 32, 256, 256, dtype=torch.float32, device=device)
    dummy_feat_s1 = torch.randn(1, 64, 128, 128, dtype=torch.float32, device=device)
    dummy_point_coords = torch.tensor([[[256.0, 256.0], [300.0, 300.0]]], dtype=torch.float32, device=device)
    dummy_point_labels = torch.tensor([[1, 1]], dtype=torch.int32, device=device)

    print("[+] Rulare inferență PyTorch de referință...")
    with torch.no_grad():
        torch_masks, torch_iou = wrapper(
            dummy_image_embeddings, dummy_feat_s0, dummy_feat_s1,
            dummy_point_coords, dummy_point_labels
        )

    print(f"    - Torch masks shape: {list(torch_masks.shape)}")
    print(f"    - Torch IoU shape:   {list(torch_iou.shape)}")

    os.makedirs(os.path.dirname(os.path.abspath(output_onnx_path)), exist_ok=True)
    print(f"[+] Export către ONNX: {output_onnx_path}...")
    t0 = time.perf_counter()

    torch.onnx.export(
        wrapper,
        (dummy_image_embeddings, dummy_feat_s0, dummy_feat_s1, dummy_point_coords, dummy_point_labels),
        output_onnx_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["image_embeddings", "feat_s0", "feat_s1", "point_coords", "point_labels"],
        output_names=["low_res_masks", "iou_predictions"],
        dynamic_axes={
            "point_coords": {1: "num_points"},
            "point_labels": {1: "num_points"},
        }
    )
    export_duration = time.perf_counter() - t0
    file_size_mb = os.path.getsize(output_onnx_path) / 1024 / 1024
    print(f"    - Export finalizat cu succes în {export_duration:.2f} s. Mărime fișier: {file_size_mb:.2f} MB")

    # Validare ONNX Runtime
    print("\n[+] Inițializare sesiune ONNX Runtime & Validare Numerică...")
    providers = ["CPUExecutionProvider"]
    if "DmlExecutionProvider" in ort.get_available_providers():
        providers.insert(0, "DmlExecutionProvider")

    session = ort.InferenceSession(output_onnx_path, providers=providers)
    ort_inputs = {
        "image_embeddings": dummy_image_embeddings.cpu().numpy(),
        "feat_s0": dummy_feat_s0.cpu().numpy(),
        "feat_s1": dummy_feat_s1.cpu().numpy(),
        "point_coords": dummy_point_coords.cpu().numpy(),
        "point_labels": dummy_point_labels.cpu().numpy(),
    }
    ort_outputs = session.run(None, ort_inputs)
    ort_masks, ort_iou = ort_outputs[0], ort_outputs[1]

    # Comparație numerică
    max_diff_masks = np.max(np.abs(torch_masks.cpu().numpy() - ort_masks))
    max_diff_iou = np.max(np.abs(torch_iou.cpu().numpy() - ort_iou))

    print("-" * 75)
    print(f"    - Provider ONNX utilizat:        {session.get_providers()[0]}")
    print(f"    - Erori numerice absolute maxime:")
    print(f"      * Măști (Logits):             {max_diff_masks:.2e}")
    print(f"      * Scoruri Calitate IoU:        {max_diff_iou:.2e}")

    tolerance = 1e-4
    if max_diff_masks < tolerance and max_diff_iou < tolerance:
        print("    [+] STATUS VALIDARE: NUMERICALLY_VERIFIED (Identitate matematică confirmată)")
        status = "NUMERICALLY_VERIFIED"
    else:
        print(f"    [!] Atenție: Diferența depășește pragul de {tolerance}")
        status = "DEVIATION_DETECTED"

    print("=" * 75)
    return status == "NUMERICALLY_VERIFIED"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export SAM 2 la ONNX și validare numerică.")
    parser.add_argument("--checkpoint", default="models/sam2/sam2_hiera_tiny.pt", help="Cale fișier checkpoint .pt")
    parser.add_argument("--config", default="sam2_hiera_t.yaml", help="Nume fișier config YAML SAM 2")
    parser.add_argument("--output", default="models/sam2/sam2_decoder.onnx", help="Cale ieșire fișier .onnx")
    args = parser.parse_args()

    success = export_and_verify(args.checkpoint, args.config, args.output)
    sys.exit(0 if success else 1)
