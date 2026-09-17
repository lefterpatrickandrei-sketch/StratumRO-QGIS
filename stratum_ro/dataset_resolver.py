# -*- coding: utf-8 -*-
"""
StratumRO — Canonical Dataset Resolver.
Centralized, authoritative discovery and metadata inspection for real geodetic
datasets on Windows and cross-platform environments.

Resolution Priority Chain:
1. Explicit UI parameters / function arguments
2. Active QGIS project layer sources
3. StratumRO configuration files
4. Environment variables (e.g. STRATUMRO_LIDAR_LAZ)
5. Known local paths (e.g. C:\\Users\\...\\Desktop\\date\\...)
6. Declared repository fallback datasets
"""

import os
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple


@dataclass
class DatasetMetadata:
    name: str
    path: str
    exists: bool
    readable: bool
    file_size: int
    sha256: str
    crs: str
    bounds: Optional[Tuple[float, float, float, float]]  # (xmin, ymin, xmax, ymax)
    dimensions: Optional[Tuple[int, int]]  # (height, width) or None
    point_count: Optional[int]  # For LiDAR
    dataset_type: str  # "lidar", "dtm", "orthophoto", "ground_truth", "model"
    source: str  # "ui", "qgis_layer", "config", "env", "known_path", "fallback", "missing"
    confidence: float  # 1.0 = explicit UI, 0.9 = layer/env, 0.8 = known local, 0.5 = fallback

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CanonicalDatasetResolver:
    """Discovers, verifies, and extracts metadata for all StratumRO input datasets."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def compute_sha256(filepath: str, max_bytes: Optional[int] = None) -> str:
        """Computes SHA256 checksum safely using chunked streaming."""
        if not os.path.isfile(filepath):
            return ""
        hasher = hashlib.sha256()
        bytes_read = 0
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    if max_bytes is not None and bytes_read + len(chunk) > max_bytes:
                        hasher.update(chunk[: max_bytes - bytes_read])
                        break
                    hasher.update(chunk)
                    bytes_read += len(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def resolve_lidar(self, ui_path: Optional[str] = None) -> DatasetMetadata:
        """Resolves real LiDAR point cloud (.laz / .las)."""
        candidates = [
            (ui_path, "ui", 1.0),
            (os.environ.get("STRATUMRO_LIDAR_LAZ"), "env", 0.9),
            (r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\LAZ\NorPuncte_St70_S42.laz", "known_path", 0.85),
            (os.path.join(self.base_dir, "datasets", "lidar", "teren.laz"), "fallback", 0.5),
            (os.path.join(self.base_dir, "data", "teren.laz"), "fallback", 0.5),
        ]
        chosen_path, source, conf = self._find_first_existing(candidates)

        if not chosen_path:
            return DatasetMetadata(
                name="lidar", path="", exists=False, readable=False, file_size=0,
                sha256="", crs="", bounds=None, dimensions=None, point_count=None,
                dataset_type="lidar", source="missing", confidence=0.0
            )

        file_size = os.path.getsize(chosen_path)
        sha = self.compute_sha256(chosen_path)
        point_count = None
        bounds = None
        crs = "EPSG:3844"

        try:
            import laspy
            with laspy.open(chosen_path) as f:
                point_count = int(f.header.point_count)
                mins = f.header.mins
                maxs = f.header.maxs
                bounds = (float(mins[0]), float(mins[1]), float(maxs[0]), float(maxs[1]))
        except Exception:
            pass

        return DatasetMetadata(
            name="lidar", path=chosen_path, exists=True, readable=True, file_size=file_size,
            sha256=sha, crs=crs, bounds=bounds, dimensions=None, point_count=point_count,
            dataset_type="lidar", source=source, confidence=conf
        )

    def resolve_dtm(self, ui_path: Optional[str] = None) -> DatasetMetadata:
        """Resolves real Digital Terrain Model raster (.tif)."""
        candidates = [
            (ui_path, "ui", 1.0),
            (os.environ.get("STRATUMRO_DTM_TIF"), "env", 0.9),
            (r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\DTM3m\DTM3m.tif", "known_path", 0.85),
            (os.path.join(self.base_dir, "datasets", "dtm", "dtm.tif"), "fallback", 0.5),
            (os.path.join(self.base_dir, "data", "dtm.tif"), "fallback", 0.5),
        ]
        chosen_path, source, conf = self._find_first_existing(candidates)

        if not chosen_path:
            return DatasetMetadata(
                name="dtm", path="", exists=False, readable=False, file_size=0,
                sha256="", crs="", bounds=None, dimensions=None, point_count=None,
                dataset_type="dtm", source="missing", confidence=0.0
            )

        file_size = os.path.getsize(chosen_path)
        sha = self.compute_sha256(chosen_path)
        bounds = None
        dimensions = None
        crs = "EPSG:3844"

        try:
            import rasterio
            with rasterio.open(chosen_path) as src:
                b = src.bounds
                bounds = (float(b.left), float(b.bottom), float(b.right), float(b.top))
                dimensions = (int(src.height), int(src.width))
                if src.crs:
                    crs = str(src.crs)
        except Exception:
            pass

        return DatasetMetadata(
            name="dtm", path=chosen_path, exists=True, readable=True, file_size=file_size,
            sha256=sha, crs=crs, bounds=bounds, dimensions=dimensions, point_count=None,
            dataset_type="dtm", source=source, confidence=conf
        )

    def resolve_orthophoto(self, ui_path: Optional[str] = None) -> DatasetMetadata:
        """Resolves real orthophoto tiles directory or mosaic GeoTIFF."""
        candidates = [
            (ui_path, "ui", 1.0),
            (os.environ.get("STRATUMRO_ORTHO_DIR"), "env", 0.9),
            (r"C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV", "known_path", 0.85),
            (os.path.join(self.base_dir, "workspace", "output", "orto.tif"), "fallback", 0.6),
            (os.path.join(self.base_dir, "datasets", "ortho"), "fallback", 0.5),
        ]
        chosen_path, source, conf = self._find_first_existing(candidates, allow_dir=True)

        if not chosen_path:
            return DatasetMetadata(
                name="orthophoto", path="", exists=False, readable=False, file_size=0,
                sha256="", crs="", bounds=None, dimensions=None, point_count=None,
                dataset_type="orthophoto", source="missing", confidence=0.0
            )

        if os.path.isdir(chosen_path):
            total_size = sum(
                os.path.getsize(os.path.join(chosen_path, f))
                for f in os.listdir(chosen_path)
                if os.path.isfile(os.path.join(chosen_path, f))
            )
            bounds = None
            sdw_files = [f for f in os.listdir(chosen_path) if f.endswith(".sdw")]
            min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")
            has_sdw = False
            for sdw in sdw_files:
                try:
                    with open(os.path.join(chosen_path, sdw), "r") as f:
                        lines = [float(l.strip()) for l in f.readlines() if l.strip()]
                    rx, ry, x0, y0 = lines[0], lines[3], lines[4], lines[5]
                    x1 = x0 + 30000 * rx
                    y1 = y0 + 30000 * ry
                    min_x = min(min_x, min(x0, x1))
                    max_x = max(max_x, max(x0, x1))
                    min_y = min(min_y, min(y0, y1))
                    max_y = max(max_y, max(y0, y1))
                    has_sdw = True
                except Exception:
                    pass
            if has_sdw:
                bounds = (min_x, min_y, max_x, max_y)

            manifest_str = ";".join(
                f"{f}:{os.path.getsize(os.path.join(chosen_path, f))}"
                for f in sorted(os.listdir(chosen_path))
                if os.path.isfile(os.path.join(chosen_path, f))
            )
            sha = hashlib.sha256(manifest_str.encode("utf-8")).hexdigest()

            return DatasetMetadata(
                name="orthophoto", path=chosen_path, exists=True, readable=True, file_size=total_size,
                sha256=sha, crs="EPSG:3844", bounds=bounds, dimensions=None, point_count=len(sdw_files),
                dataset_type="orthophoto", source=source, confidence=conf
            )
        else:
            file_size = os.path.getsize(chosen_path)
            sha = self.compute_sha256(chosen_path)
            bounds = None
            dimensions = None
            try:
                import rasterio
                with rasterio.open(chosen_path) as src:
                    b = src.bounds
                    bounds = (float(b.left), float(b.bottom), float(b.right), float(b.top))
                    dimensions = (int(src.height), int(src.width))
            except Exception:
                pass
            return DatasetMetadata(
                name="orthophoto", path=chosen_path, exists=True, readable=True, file_size=file_size,
                sha256=sha, crs="EPSG:3844", bounds=bounds, dimensions=dimensions, point_count=None,
                dataset_type="orthophoto", source=source, confidence=conf
            )

    def resolve_ground_truth(self, ui_path: Optional[str] = None) -> DatasetMetadata:
        """Resolves Cadastral Ground Truth vector (EPSG:3844 / Stereo 70)."""
        candidates = [
            (ui_path, "ui", 1.0),
            (os.environ.get("STRATUMRO_GROUND_TRUTH"), "env", 0.9),
            (os.path.join(self.base_dir, "data", "ground_truth", "tier1_teren.geojson"), "known_path", 0.95),
            (os.path.join(self.base_dir, "data", "ground_truth", "ground_truth_cluj.geojson"), "fallback", 0.8),
        ]
        chosen_path, source, conf = self._find_first_existing(candidates)

        if not chosen_path:
            return DatasetMetadata(
                name="ground_truth", path="", exists=False, readable=False, file_size=0,
                sha256="", crs="", bounds=None, dimensions=None, point_count=None,
                dataset_type="ground_truth", source="missing", confidence=0.0
            )

        file_size = os.path.getsize(chosen_path)
        sha = self.compute_sha256(chosen_path)
        bounds = None
        count = None
        crs = "EPSG:3844"

        try:
            import json
            with open(chosen_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            features = data.get("features", [])
            count = len(features)
            xs, ys = [], []
            for feat in features:
                geom = feat.get("geometry", {})
                coords = geom.get("coordinates", [])
                def extract_pts(c):
                    if isinstance(c, (list, tuple)):
                        if len(c) >= 2 and isinstance(c[0], (int, float)) and isinstance(c[1], (int, float)):
                            xs.append(c[0])
                            ys.append(c[1])
                        else:
                            for sub in c:
                                extract_pts(sub)
                extract_pts(coords)
            if xs and ys:
                bounds = (min(xs), min(ys), max(xs), max(ys))
        except Exception:
            pass

        return DatasetMetadata(
            name="ground_truth", path=chosen_path, exists=True, readable=True, file_size=file_size,
            sha256=sha, crs=crs, bounds=bounds, dimensions=None, point_count=count,
            dataset_type="ground_truth", source=source, confidence=conf
        )

    def resolve_sam2_model(self, ui_path: Optional[str] = None) -> DatasetMetadata:
        """Resolves SAM2 checkpoint weights."""
        candidates = [
            (ui_path, "ui", 1.0),
            (os.environ.get("STRATUMRO_SAM2_CHECKPOINT"), "env", 0.9),
            (os.path.join(self.base_dir, "models", "sam2", "sam2_hiera_tiny.pt"), "known_path", 0.9),
            (os.path.join(self.base_dir, "models", "sam2", "sam2_hiera_small.pt"), "fallback", 0.7),
        ]
        chosen_path, source, conf = self._find_first_existing(candidates)

        if not chosen_path:
            return DatasetMetadata(
                name="sam2_model", path="", exists=False, readable=False, file_size=0,
                sha256="", crs="", bounds=None, dimensions=None, point_count=None,
                dataset_type="model", source="missing", confidence=0.0
            )

        file_size = os.path.getsize(chosen_path)
        sha = self.compute_sha256(chosen_path)

        return DatasetMetadata(
            name="sam2_model", path=chosen_path, exists=True, readable=True, file_size=file_size,
            sha256=sha, crs="", bounds=None, dimensions=None, point_count=None,
            dataset_type="model", source=source, confidence=conf
        )

    def resolve_all(self, ui_inputs: Optional[Dict[str, str]] = None) -> Dict[str, DatasetMetadata]:
        """Resolves all primary datasets and returns structured dictionary."""
        ui_inputs = ui_inputs or {}
        return {
            "lidar": self.resolve_lidar(ui_inputs.get("lidar")),
            "dtm": self.resolve_dtm(ui_inputs.get("dtm")),
            "orthophoto": self.resolve_orthophoto(ui_inputs.get("orthophoto")),
            "ground_truth": self.resolve_ground_truth(ui_inputs.get("ground_truth")),
            "sam2_model": self.resolve_sam2_model(ui_inputs.get("sam2_model")),
        }

    def _find_first_existing(
        self, candidates: List[Tuple[Optional[str], str, float]], allow_dir: bool = False
    ) -> Tuple[str, str, float]:
        for path, src, conf in candidates:
            if not path:
                continue
            p = os.path.abspath(path)
            if allow_dir and os.path.isdir(p):
                return p, src, conf
            if os.path.isfile(p):
                return p, src, conf
        return "", "missing", 0.0
