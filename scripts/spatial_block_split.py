# -*- coding: utf-8 -*-
"""
Performs spatial block split along X-axis (West-East in Stereo 70 EPSG:3844)
with a 30m buffer between splits to prevent spatial data leakage.
"""

import json
from pathlib import Path


def spatial_block_split(
    input_geojson: str,
    output_dir: str = "data/splits",
    train_ratio: float = 0.65,
    val_ratio: float = 0.15,
    buffer_m: float = 30.0
):
    inp_path = Path(input_geojson)
    with open(inp_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"Total features to split: {len(features)}")

    # Sort features by centroid_x
    features_sorted = sorted(features, key=lambda f: f["properties"]["centroid_x"])

    total = len(features_sorted)
    idx_train_end = int(total * train_ratio)
    idx_val_end = int(total * (train_ratio + val_ratio))

    train_cands = features_sorted[:idx_train_end]
    val_cands_raw = features_sorted[idx_train_end:idx_val_end]
    test_cands_raw = features_sorted[idx_val_end:]

    # Get max X of train
    max_x_train = max(f["properties"]["centroid_x"] for f in train_cands)
    val_x_threshold = max_x_train + buffer_m
    val_cands = [f for f in val_cands_raw if f["properties"]["centroid_x"] >= val_x_threshold]

    if val_cands:
        max_x_val = max(f["properties"]["centroid_x"] for f in val_cands)
        test_x_threshold = max_x_val + buffer_m
    else:
        test_x_threshold = val_x_threshold + buffer_m

    test_cands = [f for f in test_cands_raw if f["properties"]["centroid_x"] >= test_x_threshold]

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    splits = {
        "usamv_train.geojson": train_cands,
        "usamv_val.geojson": val_cands,
        "usamv_test.geojson": test_cands
    }

    for fname, feats in splits.items():
        s_data = {
            "type": "FeatureCollection",
            "name": Path(fname).stem,
            "crs": data.get("crs"),
            "features": feats
        }
        target_f = out_path / fname
        target_f.write_text(json.dumps(s_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] Saved {len(feats)} features to {target_f}")

    print("\nSplit Summary (with 30m spatial buffer):")
    print(f"  Train: {len(train_cands)} buildings (West)")
    print(f"  Val:   {len(val_cands)} buildings (Center)")
    print(f"  Test:  {len(test_cands)} buildings (East)")
    excluded = total - (len(train_cands) + len(val_cands) + len(test_cands))
    print(f"  Excluded by 30m buffer zones: {excluded} buildings (prevents leakage)")


if __name__ == "__main__":
    spatial_block_split("data/ground_truth/tier2_cladiri_usamv.geojson")
