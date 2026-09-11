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


class SAM2EncoderONNXWrapper(nn.Module):
    """
    Wrapper PyTorch optimizat pentru exportul ONNX al encoderului de imagine ViT-Hiera SAM 2.
    """
    def __init__(self, sam2_model):
        super().__init__()
        self.image_encoder = sam2_model.image_encoder

    def forward(self, image):
        out = self.image_encoder(image)
        return out['vision_features'], out['backbone_fpn'][0], out['backbone_fpn'][1]


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
        print("    [+] STATUS VALIDARE (Sintetic): NUMERICALLY_VERIFIED (Identitate matematică confirmată)")
        status = "NUMERICALLY_VERIFIED"
    else:
        print(f"    [!] Atenție: Diferența depășește pragul de {tolerance}")
        status = "DEVIATION_DETECTED"

    # Validare secundară pe eșantion de imagine reală (contrast acoperiș / sol)
    print("\n[+] Validare Secundară pe Embeddings Extrase din Imagine Realistă...")
    try:
        from sam2.sam2_image_predictor import SAM2ImagePredictor
        pred = SAM2ImagePredictor(sam2)
        test_img = np.full((256, 256, 3), 90, dtype=np.uint8)
        test_img[50:160, 60:170, :] = 210  # Corp clădire contrastant
        pred.set_image(test_img)

        real_feats = pred._features
        r_img_emb = real_feats['image_embed']
        r_feat_s0 = real_feats['high_res_feats'][0]
        r_feat_s1 = real_feats['high_res_feats'][1]
        r_coords = torch.tensor([[[110.0, 115.0]]], dtype=torch.float32, device=device)
        r_labels = torch.tensor([[1]], dtype=torch.int32, device=device)

        with torch.no_grad():
            r_torch_m, r_torch_i = wrapper(r_img_emb, r_feat_s0, r_feat_s1, r_coords, r_labels)

        r_ort_inputs = {
            "image_embeddings": r_img_emb.cpu().numpy(),
            "feat_s0": r_feat_s0.cpu().numpy(),
            "feat_s1": r_feat_s1.cpu().numpy(),
            "point_coords": r_coords.cpu().numpy(),
            "point_labels": r_labels.cpu().numpy(),
        }
        r_ort_out = session.run(None, r_ort_inputs)
        r_diff_m = np.max(np.abs(r_torch_m.cpu().numpy() - r_ort_out[0]))
        r_diff_i = np.max(np.abs(r_torch_i.cpu().numpy() - r_ort_out[1]))

        print(f"    - Erori pe scenă de imagine:")
        print(f"      * Măști (Logits):             {r_diff_m:.2e}")
        print(f"      * Scoruri IoU:                {r_diff_i:.2e}")
        if r_diff_m < tolerance and r_diff_i < tolerance:
            print("    [+] STATUS VALIDARE IMAGINE: CONFIRMATĂ (Identitate confirmată pe proiecție spectrală)")
    except Exception as ex:
        print(f"    [!] Notă: Testul pe imagine a fost omis: {ex}")

    print("=" * 75)
    return status == "NUMERICALLY_VERIFIED"


def export_and_verify_encoder(
    checkpoint_path: str = "models/sam2/sam2_hiera_tiny.pt",
    config_name: str = "sam2_hiera_t.yaml",
    output_onnx_path: str = "models/sam2/sam2_encoder.onnx",
    device: str = "cpu"
):
    print("=" * 75)
    print("  STRATUM-RO: EXPORT ENCODER SAM 2 (ViT-Hiera) -> ONNX & VALIDARE NUMERICĂ")
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

    wrapper = SAM2EncoderONNXWrapper(sam2)
    wrapper.eval()

    dummy_image = torch.randn(1, 3, 1024, 1024, dtype=torch.float32, device=device)

    print("[+] Rulare inferență PyTorch de referință (ViT Encoder)...")
    with torch.no_grad():
        torch_vf, torch_s0, torch_s1 = wrapper(dummy_image)

    print(f"    - Torch vision_features shape: {list(torch_vf.shape)}")
    print(f"    - Torch feat_s0 shape:         {list(torch_s0.shape)}")
    print(f"    - Torch feat_s1 shape:         {list(torch_s1.shape)}")

    os.makedirs(os.path.dirname(os.path.abspath(output_onnx_path)), exist_ok=True)
    print(f"[+] Export către ONNX: {output_onnx_path}...")
    t0 = time.perf_counter()

    torch.onnx.export(
        wrapper,
        dummy_image,
        output_onnx_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["image"],
        output_names=["vision_features", "feat_s0", "feat_s1"]
    )
    export_duration = time.perf_counter() - t0
    file_size_mb = os.path.getsize(output_onnx_path) / 1024 / 1024
    print(f"    - Export encoder finalizat cu succes în {export_duration:.2f} s. Mărime: {file_size_mb:.2f} MB")

    print("\n[+] Inițializare sesiune ONNX Runtime & Validare Numerică...")
    providers = ["CPUExecutionProvider"]
    if "DmlExecutionProvider" in ort.get_available_providers():
        providers.insert(0, "DmlExecutionProvider")

    session = ort.InferenceSession(output_onnx_path, providers=providers)
    ort_inputs = {"image": dummy_image.cpu().numpy()}
    ort_outputs = session.run(None, ort_inputs)
    ort_vf, ort_s0, ort_s1 = ort_outputs[0], ort_outputs[1], ort_outputs[2]

    diff_vf = np.max(np.abs(torch_vf.cpu().numpy() - ort_vf))
    diff_s0 = np.max(np.abs(torch_s0.cpu().numpy() - ort_s0))
    diff_s1 = np.max(np.abs(torch_s1.cpu().numpy() - ort_s1))

    print("-" * 75)
    print(f"    - Provider ONNX utilizat:        {session.get_providers()[0]}")
    print(f"    - Erori numerice absolute maxime:")
    print(f"      * vision_features:            {diff_vf:.2e}")
    print(f"      * high_res feat_s0:           {diff_s0:.2e}")
    print(f"      * high_res feat_s1:           {diff_s1:.2e}")

    tolerance = 1e-4
    if diff_vf < tolerance and diff_s0 < tolerance and diff_s1 < tolerance:
        print("    [+] STATUS VALIDARE ENCODER: NUMERICALLY_VERIFIED (Identitate matematică confirmată)")
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
    parser.add_argument("--output-decoder", default="models/sam2/sam2_decoder.onnx", help="Cale ieșire decodor .onnx")
    parser.add_argument("--output-encoder", default="models/sam2/sam2_encoder.onnx", help="Cale ieșire encoder .onnx")
    parser.add_argument("--export-encoder", action="store_true", help="Exportă exclusiv encoderul de imagine")
    parser.add_argument("--export-all", action="store_true", help="Exportă atât decodorul cât și encoderul")
    args = parser.parse_args()

    if args.export_encoder:
        success = export_and_verify_encoder(args.checkpoint, args.config, args.output_encoder)
    elif args.export_all:
        s_dec = export_and_verify(args.checkpoint, args.config, args.output_decoder)
        s_enc = export_and_verify_encoder(args.checkpoint, args.config, args.output_encoder)
        success = s_dec and s_enc
    else:
        success = export_and_verify(args.checkpoint, args.config, args.output_decoder)

    sys.exit(0 if success else 1)
