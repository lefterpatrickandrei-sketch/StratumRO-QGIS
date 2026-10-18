# -*- coding: utf-8 -*-
"""
StratumRO Sparse Labels Dataset Builder (Cluj USAMV + Bucharest FIFIM Holdout).

Constructs sparse training and validation sets:
- ignore_index = 255 (unannotated background)
- 1 = verified roof polygon (Lot 1 + Lot 2 accepted cadastre candidates)
- 0 = verified explicit negative surface (T12:C1 paved courtyard, T08/T09 rejected ground/veg)

Enforces strict spatial disjoint partition with buffer to guarantee zero spatial leakage,
and prepares geographic holdout evaluation catalog for Bucharest FIFIM (RGB-only).
"""
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json
import numpy as np
import geopandas as gpd
from shapely.geometry import box, Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import rasterio
from rasterio.features import rasterize
from rasterio.windows import from_bounds, Window

IGNORE_INDEX = 255
ROOF_LABEL = 1
NEGATIVE_LABEL = 0


class SparseDatasetBuilder:
    def __init__(self, crs: str = "EPSG:3844"):
        self.crs = crs

    def load_cluj_annotations(
        self,
        review18_gpkg: Path,
        retry_six_gpkg: Path,
        lot3_old_gpkg: Path
    ) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Loads verified positive building annotations (Lot 1 & Lot 2) and explicit negative
        annotations (paved courtyards, rejected ground/vegetation) from audited GeoPackages.
        """
        pos_records = []
        neg_records = []

        # 1. Lot 1: B00005 split (2 bodies)
        b5_gdf = gpd.read_file(review18_gpkg, layer="B5_DOUA_CORPURI")
        for _, row in b5_gdf.iterrows():
            pos_records.append({
                "id": str(row["id"]),
                "source": "review18_B5_DOUA_CORPURI",
                "lot": 1,
                "label": ROOF_LABEL,
                "owner_verdict": "ACCEPTED_BY_OWNER",
                "geometry": row["geometry"]
            })

        # 2. Lot 1: Accepted bodies from CONTURURI_PASTRATE
        pastrate_gdf = gpd.read_file(review18_gpkg, layer="CONTURURI_PASTRATE")
        for _, row in pastrate_gdf.iterrows():
            pos_records.append({
                "id": str(row["id"]),
                "source": "review18_CONTURURI_PASTRATE",
                "lot": 1,
                "label": ROOF_LABEL,
                "owner_verdict": "ACCEPTED_BY_OWNER",
                "geometry": row["geometry"]
            })

        # 3. Lot 2: Accepted T01-T04 from TESTE_10_REZULTATE
        t10_gdf = gpd.read_file(review18_gpkg, layer="TESTE_10_REZULTATE")
        accepted_t10 = t10_gdf[t10_gdf["id"].isin(["T01:C1", "T02:C1", "T03:C1", "T04:C1"])]
        for _, row in accepted_t10.iterrows():
            pos_records.append({
                "id": str(row["id"]),
                "source": "review18_TESTE_10_REZULTATE",
                "lot": 2,
                "label": ROOF_LABEL,
                "owner_verdict": "ACCEPTED_BY_OWNER",
                "geometry": row["geometry"]
            })

        # 4. Lot 2: Accepted rectified retries (T05:A1, T05:A3, T06:A1, T07:A1, T10:A1)
        r6_gdf = gpd.read_file(retry_six_gpkg, layer="CORPURI_RECTIFICATE")
        for _, row in r6_gdf.iterrows():
            pos_records.append({
                "id": str(row["id"]),
                "source": "retry_six_CORPURI_RECTIFICATE",
                "lot": 2,
                "label": ROOF_LABEL,
                "owner_verdict": "ACCEPTED_BY_OWNER",
                "geometry": row["geometry"]
            })

        # 5. Negatives: Paved courtyard false-positive T12:C1 from lot3_20261013
        lot3_old_gdf = gpd.read_file(lot3_old_gpkg, layer="CORPURI_EXTRASE_LOT3")
        t12_courtyard = lot3_old_gdf[lot3_old_gdf["id"] == "T12:C1"]
        for _, row in t12_courtyard.iterrows():
            neg_records.append({
                "id": "NEG_T12_C1_PAVED_COURTYARD",
                "source": "lot3_20261013_T12_C1",
                "lot": 3,
                "label": NEGATIVE_LABEL,
                "category": "PAVED_COURTYARD",
                "geometry": row["geometry"]
            })

        # 6. Negatives: Rejected non-building ground/vegetation masks T08 and T09
        resp_gdf = gpd.read_file(retry_six_gpkg, layer="RESPINSE_ANTERIOR")
        t08_t09 = resp_gdf[resp_gdf["id"].isin(["T08", "T09"])]
        for _, row in t08_t09.iterrows():
            neg_records.append({
                "id": f"NEG_{row['id']}_REJECTED_SURFACE",
                "source": "retry_six_RESPINSE_ANTERIOR",
                "lot": 2,
                "label": NEGATIVE_LABEL,
                "category": "REJECTED_GROUND_VEGETATION",
                "geometry": row["geometry"]
            })

        pos_gdf = gpd.GeoDataFrame(pos_records, crs=self.crs)
        neg_gdf = gpd.GeoDataFrame(neg_records, crs=self.crs)
        return pos_gdf, neg_gdf

    def create_spatial_split(
        self,
        pos_gdf: gpd.GeoDataFrame,
        neg_gdf: gpd.GeoDataFrame,
        split_axis: str = "y",
        split_coord: Optional[float] = None,
        buffer_m: float = 20.0
    ) -> Dict[str, Any]:
        """
        Splits annotations into Train and Val using a spatial boundary line with a buffer zone.
        Guarantees 0 spatial overlap and minimum spatial separation >= buffer_m.
        """
        all_geoms = list(pos_gdf.geometry) + list(neg_gdf.geometry)
        total_bounds = unary_union(all_geoms).bounds
        minx, miny, maxx, maxy = total_bounds

        buffer_half = buffer_m / 2.0

        if split_axis.lower() == "y":
            if split_coord is None:
                split_coord = 585490.0  # Natural 79-meter gap between South cluster and North campus
            train_envelope = box(minx - 100.0, split_coord + buffer_half, maxx + 100.0, maxy + 100.0)
            val_envelope = box(minx - 100.0, miny - 100.0, maxx + 100.0, split_coord - buffer_half)
            buffer_corridor = box(minx - 100.0, split_coord - buffer_half, maxx + 100.0, split_coord + buffer_half)

            train_pos = pos_gdf[pos_gdf.geometry.bounds["miny"] >= (split_coord + buffer_half)].copy()
            val_pos = pos_gdf[pos_gdf.geometry.bounds["maxy"] <= (split_coord - buffer_half)].copy()
            train_neg = neg_gdf[neg_gdf.geometry.bounds["miny"] >= (split_coord + buffer_half)].copy()
            val_neg = neg_gdf[neg_gdf.geometry.bounds["maxy"] <= (split_coord - buffer_half)].copy()
        else:
            if split_coord is None:
                centroids_x = [g.centroid.x for g in all_geoms]
                split_coord = float(np.median(centroids_x))
            train_envelope = box(minx - 100.0, miny - 100.0, split_coord - buffer_half, maxy + 100.0)
            val_envelope = box(split_coord + buffer_half, miny - 100.0, maxx + 100.0, maxy + 100.0)
            buffer_corridor = box(split_coord - buffer_half, miny - 100.0, split_coord + buffer_half, maxy + 100.0)

            train_pos = pos_gdf[pos_gdf.geometry.bounds["maxx"] <= (split_coord - buffer_half)].copy()
            val_pos = pos_gdf[pos_gdf.geometry.bounds["minx"] >= (split_coord + buffer_half)].copy()
            train_neg = neg_gdf[neg_gdf.geometry.bounds["maxx"] <= (split_coord - buffer_half)].copy()
            val_neg = neg_gdf[neg_gdf.geometry.bounds["minx"] >= (split_coord + buffer_half)].copy()

        excluded_pos = pos_gdf[~pos_gdf.index.isin(train_pos.index) & ~pos_gdf.index.isin(val_pos.index)]
        excluded_neg = neg_gdf[~neg_gdf.index.isin(train_neg.index) & ~neg_gdf.index.isin(val_neg.index)]

        train_union = unary_union(list(train_pos.geometry) + list(train_neg.geometry)) if (len(train_pos) + len(train_neg)) > 0 else Polygon()
        val_union = unary_union(list(val_pos.geometry) + list(val_neg.geometry)) if (len(val_pos) + len(val_neg)) > 0 else Polygon()

        overlap = train_union.intersects(val_union)
        min_dist = float(train_union.distance(val_union)) if not train_union.is_empty and not val_union.is_empty else float("inf")

        return {
            "split_axis": split_axis,
            "split_coord": split_coord,
            "buffer_m": buffer_m,
            "corridor_envelope": buffer_corridor,
            "train_envelope": train_envelope,
            "val_envelope": val_envelope,
            "train_pos": train_pos,
            "val_pos": val_pos,
            "train_neg": train_neg,
            "val_neg": val_neg,
            "excluded_pos_count": len(excluded_pos),
            "excluded_neg_count": len(excluded_neg),
            "zero_leakage_verified": (not overlap) and (min_dist >= buffer_m - 0.01),
            "measured_min_distance_m": round(min_dist, 3)
        }

    def rasterize_sparse_patch(
        self,
        patch_bounds: Tuple[float, float, float, float],
        transform: rasterio.Affine,
        out_shape: Tuple[int, int],
        positive_geoms: List[Any],
        negative_geoms: List[Any],
        ignore_index: int = IGNORE_INDEX
    ) -> np.ndarray:
        """
        Rasterizes sparse label mask:
        - Default / unannotated = ignore_index (255)
        - Explicit negative = NEGATIVE_LABEL (0)
        - Verified building = ROOF_LABEL (1)
        """
        mask = np.full(out_shape, fill_value=ignore_index, dtype=np.uint8)

        if negative_geoms:
            valid_neg = [(g, NEGATIVE_LABEL) for g in negative_geoms if g is not None and not g.is_empty]
            if valid_neg:
                rasterize(valid_neg, out=mask, transform=transform, dtype=np.uint8)

        if positive_geoms:
            valid_pos = [(g, ROOF_LABEL) for g in positive_geoms if g is not None and not g.is_empty]
            if valid_pos:
                rasterize(valid_pos, out=mask, transform=transform, dtype=np.uint8)

        return mask

    def build_bucharest_holdout_catalog(
        self,
        orto_path: Path,
        visual_plan_path: Optional[Path] = None,
        patch_size: int = 512
    ) -> Dict[str, Any]:
        """
        Prepares evaluation grid and metadata for Bucharest FIFIM geographic holdout.
        Completely isolated from Cluj USAMV development.
        """
        if not orto_path.exists():
            raise FileNotFoundError(f"Bucharest ORTO.tif not found: {orto_path}")

        with rasterio.open(orto_path) as src:
            w, h = src.width, src.height
            tr = src.transform
            crs = str(src.crs)
            bounds = src.bounds
            res = src.res

            patches = []
            stride = patch_size
            for r0 in range(0, h - patch_size + 1, stride):
                for c0 in range(0, w - patch_size + 1, stride):
                    x0, y1 = tr * (c0, r0)
                    x1, y0 = tr * (c0 + patch_size, r0 + patch_size)
                    patch_box = [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]
                    patches.append({
                        "patch_id": f"FIFIM_P{len(patches):04d}",
                        "row_off": r0,
                        "col_off": c0,
                        "width": patch_size,
                        "height": patch_size,
                        "bounds": patch_box,
                        "center": [round((x0 + x1) / 2.0, 2), round((y0 + y1) / 2.0, 2)],
                    })

        plan_meta = None
        if visual_plan_path and visual_plan_path.exists():
            try:
                with rasterio.open(visual_plan_path) as src_p:
                    plan_meta = {
                        "path": str(visual_plan_path.resolve()),
                        "width": src_p.width,
                        "height": src_p.height,
                        "res_m": round(float(src_p.res[0]), 3),
                        "bounds": [round(v, 2) for v in src_p.bounds]
                    }
            except Exception:
                plan_meta = {"path": str(visual_plan_path.resolve()), "status": "EXISTS_ON_DISK"}

        return {
            "dataset_name": "BUCHAREST_FIFIM_GEOGRAPHIC_HOLDOUT",
            "role": "INDEPENDENT_TEST_RGB_ONLY",
            "crs": crs,
            "ortho_source": str(orto_path.resolve()),
            "ortho_resolution_m": round(float(res[0]), 3),
            "ortho_dimensions": [w, h],
            "ortho_bounds": [round(v, 2) for v in bounds],
            "visual_plan_cadastre_1_500": plan_meta,
            "total_evaluation_patches": len(patches),
            "patch_dimension_px": [patch_size, patch_size],
            "patches_sample": patches[:20]
        }
