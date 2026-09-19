"""
Generates a complete, cryptographic machine-readable manifest (SHA-256 hashes, sizes, CRS)
for all Cluj Phase 2 source files, intermediate products, and final deliverables.
"""

import os
import hashlib
import json
from datetime import datetime

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest()

def get_file_info(rel_path, crs, category, description):
    abs_path = os.path.abspath(rel_path)
    if not os.path.exists(abs_path):
        return None
    stat = os.stat(abs_path)
    return {
        "relative_path": rel_path.replace("\\", "/"),
        "category": category,
        "description": description,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "crs": crs,
        "sha256": sha256_file(abs_path)
    }

def main():
    items = [
        # Source Data (Immutable Raw Assets on Desktop)
        ("C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif", "EPSG:3844", "SOURCE_RASTER", "Bare-Earth Digital Terrain Model (3m resolution)"),
        ("C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz", "EPSG:3844", "SOURCE_POINTCLOUD", "Classified Airborne LiDAR Point Cloud (4,624,905 points)"),
        
        # Intermediate & Derived Rasters
        ("workspace/e2e/04_orthophoto/active_ortho_crop.tif", "EPSG:3844", "INPUT_RASTER", "Active Cluj Orthophoto Crop (20cm GSD, 2500x2000)"),
        ("workspace/derived/cluj_ndsm_1m.tif", "EPSG:3844", "DERIVED_RASTER", "Reconstructed Normalized Digital Surface Model (1m resolution)"),
        
        # Reference Data
        ("data/derived_reference/tier1_primary_29.geojson", "EPSG:3844", "REFERENCE_GT", "Deduplicated Primary Cadastral Reference (29 buildings)"),
        ("data/derived_reference/tier2_additional_121.geojson", "EPSG:3844", "REFERENCE_GT", "Deduplicated Complementary Reference (121 buildings)"),
        ("data/derived_reference/cluj_combined_unique_150.geojson", "EPSG:3844", "REFERENCE_GT", "Clean Deduplicated Cadastral Reference (150 unique buildings)"),
        
        # Predictions
        ("workspace/predictions/cluj_raw_sam2_predictions.geojson", "EPSG:3844", "MODEL_PREDICTION", "Raw Organic Footprints from Meta SAM 2 Inference"),
        ("workspace/predictions/cluj_regularized_predictions.geojson", "EPSG:3844", "REGULARIZED_CAD", "90-degree Orthogonal Cadastral Regularized Footprints"),
        
        # Quality Control & QGIS
        ("reports/cluj/coregistration_points.geojson", "EPSG:3844", "QC_VALIDATION", "Roof-to-Reference Centroid Divergence Points (26 buildings, EPSG:3844)"),
        ("reports/cluj/sam2_cluj_benchmark_metrics.json", "N/A", "METRICS", "Authentic Benchmark Performance & Evaluation Metrics"),
        ("reports/cluj/toolchain_versions.json", "N/A", "TOOLCHAIN_SPEC", "Windows CLI Verified Toolchain Versions (QGIS, GDAL, PDAL, SNAP, PyTorch, CUDA)"),
        ("reports/cluj/KILO_INDEPENDENT_PHASE2_AUDIT.md", "N/A", "AUDIT_HISTORICAL", "Historical Independent Pre-Correction Audit Report (Superseded)"),
        ("reports/cluj/KILO_PHASE2_REAUDIT.md", "N/A", "AUDIT_VALIDATION", "Post-Correction Independent Re-Audit Validation Report"),
        ("StratumRO_Cluj_Phase2_Spectator.qgs", "EPSG:3844", "QGIS_PROJECT", "Phase 2 Live Inspection QGIS Project File"),
    ]

    manifest = {
        "manifest_version": "1.0.0",
        "benchmark_aoi": "Cluj-Napoca (USAMV / Someșul Mic)",
        "project_identity": "StratumRO — AI Geospatial Platform for QGIS",
        "benchmark_role": "High-Precision Pre-Cadastral Assistance Validation Laboratory",
        "generated_date": datetime.now().isoformat(),
        "crs_primary": "Stereo 70 (EPSG:3844)",
        "hardware": "NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM, CUDA sm_89)",
        "software_versions": {
            "qgis": "3.40.0-Bratislava",
            "gdal": "3.9.3",
            "pdal": "2.8.1",
            "pytorch": "2.6.0+cu124",
            "python": "3.10.10"
        },
        "artifacts": []
    }

    for path, crs, cat, desc in items:
        info = get_file_info(path, crs, cat, desc)
        if info:
            manifest["artifacts"].append(info)
            print(f"[+] Hashed: {path}")
        else:
            print(f"[!] Warning: File not found: {path}")

    out_file = "reports/cluj/data_manifest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[+] Saved manifest to: {out_file}")

if __name__ == "__main__":
    main()
