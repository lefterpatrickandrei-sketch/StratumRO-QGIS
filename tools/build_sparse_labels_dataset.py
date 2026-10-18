# -*- coding: utf-8 -*-
"""
Generate Sparse Labels Dataset for Cluj USAMV and independent holdout for Bucharest FIFIM.
"""
from pathlib import Path
import sys
import json
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratum_ro.sparse_dataset_builder import (
    SparseDatasetBuilder, IGNORE_INDEX, ROOF_LABEL, NEGATIVE_LABEL
)

OUT_DIR = ROOT / "workspace/reviews/sparse_labels"
REVIEW18_GPKG = ROOT / "workspace/reviews/review18_20261013/review18.gpkg"
RETRY_SIX_GPKG = ROOT / "workspace/reviews/retry_six_release_20261013/retry_six.gpkg"
LOT3_OLD_GPKG = ROOT / "workspace/reviews/lot3_20261013/lot3_results.gpkg"
BUCHAREST_ORTO = Path(r"C:\Users\lefpa\Desktop\date\georeferentiere\ORTO\ORTO.tif")
BUCHAREST_PLAN = Path(r"C:\Users\lefpa\Desktop\date\georeferentiere\PLAN_GEOREF\1_500.jpg")
CLUJ_VRT = ROOT / "workspace/output/ortofoto_cluj_usamv_rgb.vrt"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    builder = SparseDatasetBuilder(crs="EPSG:3844")

    print("[SPARSE] 1. Loading Cluj USAMV verified positive and explicit negative annotations...")
    pos_gdf, neg_gdf = builder.load_cluj_annotations(
        review18_gpkg=REVIEW18_GPKG,
        retry_six_gpkg=RETRY_SIX_GPKG,
        lot3_old_gpkg=LOT3_OLD_GPKG
    )
    print(f"Loaded {len(pos_gdf)} positive building instances (Lot 1 + Lot 2 accepted cadastre candidates).")
    print(f"Loaded {len(neg_gdf)} explicit negative instances (paved courtyards, rejected surfaces).")

    print("[SPARSE] 2. Partitioning into spatially disjoint Train and Val sets (with 20m buffer corridor)...")
    split_info = builder.create_spatial_split(pos_gdf, neg_gdf, split_axis="y", buffer_m=20.0)
    print(f"  Split Axis: {split_info['split_axis'].upper()} at {split_info['split_coord']:.2f}")
    print(f"  Train: {len(split_info['train_pos'])} positives, {len(split_info['train_neg'])} negatives")
    print(f"  Val:   {len(split_info['val_pos'])} positives, {len(split_info['val_neg'])} negatives")
    print(f"  Excluded in buffer corridor: {split_info['excluded_pos_count']} positives, {split_info['excluded_neg_count']} negatives")
    print(f"  Zero spatial leakage verified: {split_info['zero_leakage_verified']} (min separation: {split_info['measured_min_distance_m']} m)")

    # Save to GeoPackage
    gpkg_out = OUT_DIR / "cluj_usamv_sparse_annotations.gpkg"
    print(f"[SPARSE] 3. Writing annotations GeoPackage: {gpkg_out.name}...")
    split_info["train_pos"].to_file(gpkg_out, layer="CLUJ_TRAIN_POSITIVES", driver="GPKG")
    split_info["train_neg"].to_file(gpkg_out, layer="CLUJ_TRAIN_NEGATIVES", driver="GPKG")
    split_info["val_pos"].to_file(gpkg_out, layer="CLUJ_VAL_POSITIVES", driver="GPKG")
    if len(split_info["val_neg"]) > 0:
        split_info["val_neg"].to_file(gpkg_out, layer="CLUJ_VAL_NEGATIVES", driver="GPKG")

    corridor_gdf = gpd.GeoDataFrame([{"id": "BUFFER_CORRIDOR_20M", "geometry": split_info["corridor_envelope"]}], crs="EPSG:3844")
    corridor_gdf.to_file(gpkg_out, layer="BUFFER_CORRIDOR", driver="GPKG")

    # Generate Cluj summary catalog JSON
    cluj_catalog = {
        "dataset_name": "CLUJ_USAMV_SPARSE_LABELS",
        "crs": "EPSG:3844",
        "labels_schema": {
            "ignore_index": IGNORE_INDEX,
            "positive_roof": ROOF_LABEL,
            "explicit_negative": NEGATIVE_LABEL
        },
        "spatial_split": {
            "split_axis": split_info["split_axis"],
            "split_coord": split_info["split_coord"],
            "buffer_corridor_m": split_info["buffer_m"],
            "zero_leakage_verified": split_info["zero_leakage_verified"],
            "measured_min_distance_m": split_info["measured_min_distance_m"],
        },
        "statistics": {
            "total_positives": len(pos_gdf),
            "total_negatives": len(neg_gdf),
            "train_positives": len(split_info["train_pos"]),
            "train_negatives": len(split_info["train_neg"]),
            "val_positives": len(split_info["val_pos"]),
            "val_negatives": len(split_info["val_neg"]),
            "train_positive_area_m2": round(float(split_info["train_pos"].area.sum()), 2),
            "val_positive_area_m2": round(float(split_info["val_pos"].area.sum()), 2),
            "negative_area_m2": round(float(neg_gdf.area.sum()), 2),
        },
        "train_instances": split_info["train_pos"]["id"].tolist(),
        "val_instances": split_info["val_pos"]["id"].tolist(),
        "negative_instances": neg_gdf["id"].tolist(),
    }
    cluj_catalog_path = OUT_DIR / "cluj_usamv_sparse_catalog.json"
    cluj_catalog_path.write_text(json.dumps(cluj_catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SPARSE] Saved Cluj catalog: {cluj_catalog_path.name}")

    print("[SPARSE] 4. Building independent holdout catalog for Bucharest FIFIM...")
    fifim_catalog = builder.build_bucharest_holdout_catalog(
        orto_path=BUCHAREST_ORTO,
        visual_plan_path=BUCHAREST_PLAN,
        patch_size=512
    )
    fifim_catalog_path = OUT_DIR / "bucharest_fifim_holdout_catalog.json"
    fifim_catalog_path.write_text(json.dumps(fifim_catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SPARSE] Saved Bucharest FIFIM holdout catalog: {fifim_catalog_path.name} ({fifim_catalog['total_evaluation_patches']} test patches)")

    print("[SPARSE] 5. Generating sample sparse label raster patches for visual inspection...")
    # Sample 4 patches centered on key objects: T05, T10, T12, B00005
    sample_targets = [
        {"name": "T10 (Accepted Rect)", "center": [390932.0, 585670.0], "size_m": 45.0},
        {"name": "T05 (Accepted L + Annex)", "center": [390868.0, 585660.0], "size_m": 55.0},
        {"name": "T12 (Roof + Paved Neg)", "center": [391285.0, 585605.0], "size_m": 60.0},
        {"name": "B00005 (Split Bodies)", "center": [390865.0, 585720.0], "size_m": 50.0},
    ]

    fig, axes = plt.subplots(4, 3, figsize=(15, 18), layout="constrained")

    with rasterio.open(CLUJ_VRT) as src:
        all_pos_geoms = list(pos_gdf.geometry)
        all_neg_geoms = list(neg_gdf.geometry)

        for row_idx, target in enumerate(sample_targets):
            cx, cy = target["center"]
            half_s = target["size_m"] / 2.0
            p_box = [cx - half_s, cy - half_s, cx + half_s, cy + half_s]
            win = from_bounds(*p_box, transform=src.transform)
            win = win.round_offsets().round_lengths()
            rgb = np.moveaxis(src.read([1, 2, 3], window=win), 0, -1)
            win_tr = rasterio.windows.transform(win, src.transform)
            h, w = rgb.shape[:2]

            # Rasterize sparse mask
            mask = builder.rasterize_sparse_patch(
                patch_bounds=p_box,
                transform=win_tr,
                out_shape=(h, w),
                positive_geoms=all_pos_geoms,
                negative_geoms=all_neg_geoms,
                ignore_index=IGNORE_INDEX
            )

            # Mask color overlay: ignore = gray transparent, 1 = neon green, 0 = bright red
            mask_rgb = np.zeros((h, w, 3), dtype=np.uint8)
            mask_rgb[mask == IGNORE_INDEX] = [180, 180, 180]  # unannotated (ignore_index=255)
            mask_rgb[mask == ROOF_LABEL] = [57, 255, 20]      # verified roof (label=1)
            mask_rgb[mask == NEGATIVE_LABEL] = [255, 23, 68]  # explicit negative (label=0)

            # Blended overlay
            alpha = 0.5
            blended = (rgb * (1 - alpha) + mask_rgb * alpha).astype(np.uint8)

            ext = [win_tr.c, win_tr.c + w * win_tr.a, win_tr.f + h * win_tr.e, win_tr.f]

            ax0, ax1, ax2 = axes[row_idx]
            ax0.imshow(rgb, extent=ext)
            ax0.set_title(f"{target['name']} — RGB Orto", fontsize=11, fontweight="bold")
            ax0.axis("off")

            ax1.imshow(mask_rgb, extent=ext)
            ax1.set_title("Sparse Mask (Green=1, Red=0, Gray=255)", fontsize=11, fontweight="bold")
            ax1.axis("off")

            ax2.imshow(blended, extent=ext)
            ax2.set_title("Ortho + Sparse Label Overlay", fontsize=11, fontweight="bold")
            ax2.axis("off")

    sample_img_path = OUT_DIR / "sparse_labels_sample_patches.png"
    fig.suptitle("StratumRO — Eșantioane Sparse Labels (ignore_index=255, Pozitiv=1, Negativ Explicit=0)",
                 fontsize=15, fontweight="bold")
    fig.savefig(sample_img_path, dpi=160)
    plt.close(fig)
    print(f"[SPARSE] Saved sample visual sheet: {sample_img_path.name}")
    print("[SPARSE] Dataset build completed successfully!")


if __name__ == "__main__":
    main()
