# -*- coding: utf-8 -*-
"""
Project Context Engine for StratumRO AI (MD 4 Conformance).
Collects read-only environmental information (project, QGIS/Python, active CRS,
AOI, loaded layers, raster/LiDAR metadata, hardware, and provider health)
in a compact, cached snapshot without duplicating geospatial data.
"""

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from stratum_ro.ai.tools.security import resolve_sandboxed_path


def _detect_system_ram_mb() -> Optional[int]:
    """Safely detects total system RAM in MB without adding external dependencies."""
    try:
        if sys.platform == "win32":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys // (1024 * 1024))
    except Exception:
        pass
    return None


def detect_hardware_context() -> Dict[str, Any]:
    """
    Detects CPU, RAM, GPU vendor, CUDA, and DirectML acceleration based only
    on actually verified system properties (no unverified claims).
    """
    # 1. CPU & OS
    cpu_count = os.cpu_count() or 1
    os_name = sys.platform

    # 2. CUDA GPU
    cuda_available = False
    gpu_name = "None"
    try:
        import torch
        if torch.cuda.is_available():
            cuda_available = True
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    # 3. DirectML GPU (Windows DirectX 12 acceleration)
    directml_available = False
    try:
        import onnxruntime as ort
        if "DmlExecutionProvider" in ort.get_available_providers():
            directml_available = True
    except Exception:
        pass

    ram_mb = _detect_system_ram_mb()

    return {
        "os": os_name,
        "cpu_count": cpu_count,
        "ram_total_mb": ram_mb,
        "gpu_available": cuda_available or directml_available,
        "gpu_name": gpu_name,
        "cuda_available": cuda_available,
        "directml_available": directml_available
    }


def detect_qgis_context() -> Dict[str, Any]:
    """Detects whether running inside active QGIS application or headless/standalone."""
    try:
        from qgis.core import Qgis, QgsProject
        project = QgsProject.instance()
        return {
            "running": True,
            "version": Qgis.QGIS_VERSION,
            "project_title": project.title() or "Untitled",
            "project_path": project.fileName() or "in-memory",
            "crs": project.crs().authid() if project.crs().isValid() else "EPSG:3844"
        }
    except Exception:
        return {
            "running": False,
            "version": "standalone / headless (PyQGIS not bound)",
            "project_title": "StratumRO_Stereo70",
            "project_path": "standalone",
            "crs": "EPSG:3844"
        }


@dataclass
class ProjectContext:
    """
    Backward-compatible Project Context configuration container.
    Maintains compatibility with existing code and config.yaml loading.
    """
    project_name: str = "StratumRO_Stereo70"
    crs: str = "EPSG:3844"
    vertical_datum: str = "EPSG:5781"
    output_dir: str = "workspace/output"
    lidar_path: Optional[str] = None
    dtm_path: Optional[str] = None
    ortho_path: Optional[str] = None
    thresholds: Dict[str, Any] = field(default_factory=dict)
    active_layers: List[str] = field(default_factory=list)

    @classmethod
    def load_from_config(cls, config_path: str = "config.yaml") -> "ProjectContext":
        """Loads context thresholds and default paths from config.yaml."""
        p_cfg = Path(config_path)
        cfg_data = {}
        if p_cfg.is_file():
            try:
                with open(p_cfg, "r", encoding="utf-8") as f:
                    cfg_data = yaml.safe_load(f) or {}
            except Exception:
                pass

        paths = cfg_data.get("paths", {})
        lidar_cfg = cfg_data.get("lidar", {})
        reg_cfg = cfg_data.get("regularization", {})
        class_cfg = cfg_data.get("classification", {})

        thresholds = {
            "min_building_height_m": lidar_cfg.get("min_building_height_m", 2.5),
            "mrr_rectangularity_trigger": reg_cfg.get("mrr_rectangularity_trigger", 0.70),
            "eave_offset_meters": reg_cfg.get("eave_offset_meters", 0.40),
            "main_building_min_area_m2": class_cfg.get("main_building_min_area_m2", 45.0),
            "outbuilding_min_area_m2": class_cfg.get("outbuilding_min_area_m2", 8.0),
        }

        # Resolve paths
        lidar_laz = paths.get("lidar_laz")
        if lidar_laz and not os.path.isfile(lidar_laz):
            fallback_laz = "data/teren.laz"
            if os.path.isfile(fallback_laz):
                lidar_laz = fallback_laz

        return cls(
            project_name=cfg_data.get("project_name", "StratumRO_Stereo70"),
            crs="EPSG:3844",
            vertical_datum="EPSG:5781",
            output_dir=paths.get("output_dir", "workspace/output"),
            lidar_path=lidar_laz,
            dtm_path=paths.get("dtm_raster"),
            ortho_path=paths.get("ortho_vrt"),
            thresholds=thresholds
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "crs": self.crs,
            "vertical_datum": self.vertical_datum,
            "output_dir": self.output_dir,
            "lidar_path": self.lidar_path,
            "dtm_path": self.dtm_path,
            "ortho_path": self.ortho_path,
            "thresholds": self.thresholds,
            "active_layers": self.active_layers
        }


class ContextEngine:
    """
    Central environmental context engine for StratumRO AI.
    Assembles compact, cached snapshots of project status, CRS, AOI, input metadata,
    hardware, and provider health.
    """

    def __init__(self, config_path: str = "config.yaml", cache_ttl_sec: float = 5.0):
        self.config_path = config_path
        self.cache_ttl_sec = max(0.1, cache_ttl_sec)
        self.base_context = ProjectContext.load_from_config(config_path)
        self._cached_snapshot: Optional[Dict[str, Any]] = None
        self._last_snapshot_time: float = 0.0
        self._explicit_aoi: Optional[Dict[str, Any]] = None

    def set_explicit_aoi(self, bbox: List[float], source: str = "explicit_input"):
        """Sets an explicit AOI bbox [minx, miny, maxx, maxy]. Invalidate cache."""
        self._explicit_aoi = {
            "source": source,
            "bbox": [round(float(c), 3) for c in bbox],
            "crs": "EPSG:3844"
        }
        self.invalidate()

    def invalidate(self):
        """Clears cached context snapshot to force fresh collection."""
        self._cached_snapshot = None
        self._last_snapshot_time = 0.0

    def refresh(self) -> Dict[str, Any]:
        """Invalidates cache and collects fresh snapshot immediately."""
        self.invalidate()
        return self.get_snapshot()

    def get_aoi_context(self) -> Dict[str, Any]:
        """
        Provides current AOI with identifiable source (explicit input, QGIS canvas,
        or default active test sector in Stereo 70).
        """
        if self._explicit_aoi:
            return dict(self._explicit_aoi)

        # Check if QGIS canvas is available
        try:
            from qgis.utils import iface
            if iface and iface.mapCanvas():
                ext = iface.mapCanvas().extent()
                return {
                    "source": "map_canvas",
                    "bbox": [round(ext.xMinimum(), 3), round(ext.yMinimum(), 3),
                             round(ext.xMaximum(), 3), round(ext.yMaximum(), 3)],
                    "crs": "EPSG:3844"
                }
        except Exception:
            pass

        # Standard active cadastral benchmark sector (USAMV Cluj-Napoca, Stereo 70)
        return {
            "source": "config_default",
            "bbox": [391500.0, 584500.0, 392500.0, 585500.0],
            "crs": "EPSG:3844"
        }

    def get_inputs_metadata(self) -> Dict[str, Any]:
        """
        Inspects orthophoto and LiDAR headers safely without reading full datasets into memory.
        """
        repo_root = resolve_sandboxed_path(".")
        rasters_meta = []
        lidar_meta = []

        # 1. Raster Inspection
        candidate_rasters = []
        if self.base_context.ortho_path:
            candidate_rasters.append(self.base_context.ortho_path)
        data_dir = repo_root / "data"
        if data_dir.exists():
            candidate_rasters.extend([str(p) for p in data_dir.glob("**/*.tif")][:3])

        seen_r = set()
        for r_path in candidate_rasters:
            try:
                p = resolve_sandboxed_path(r_path, must_exist=True)
                if str(p) in seen_r:
                    continue
                seen_r.add(str(p))

                import rasterio
                with rasterio.open(p) as src:
                    rasters_meta.append({
                        "path": str(p.relative_to(repo_root)),
                        "crs": str(src.crs) if src.crs else "EPSG:3844",
                        "dimensions": [src.width, src.height],
                        "bands": src.count,
                        "resolution_gsd_m": [round(src.res[0], 3), round(src.res[1], 3)],
                        "bounds": [round(b, 2) for b in src.bounds],
                        "nodata": src.nodata
                    })
            except Exception:
                continue

        # 2. LiDAR Inspection
        candidate_lidar = []
        if self.base_context.lidar_path:
            candidate_lidar.append(self.base_context.lidar_path)
        if data_dir.exists():
            candidate_lidar.extend([str(p) for p in list(data_dir.glob("**/*.laz"))[:2] + list(data_dir.glob("**/*.las"))[:2]])

        seen_l = set()
        for l_path in candidate_lidar:
            try:
                p = resolve_sandboxed_path(l_path, must_exist=True)
                if str(p) in seen_l:
                    continue
                seen_l.add(str(p))

                import laspy
                with laspy.open(p) as las_file:
                    hdr = las_file.header
                    crs_str = "EPSG:3844"
                    try:
                        parsed_crs = hdr.parse_crs()
                        if parsed_crs:
                            crs_str = parsed_crs.to_string()
                    except Exception:
                        pass

                    b_min = [round(hdr.min[0], 2), round(hdr.min[1], 2), round(hdr.min[2], 2)]
                    b_max = [round(hdr.max[0], 2), round(hdr.max[1], 2), round(hdr.max[2], 2)]
                    area_est = max(1.0, (hdr.max[0] - hdr.min[0]) * (hdr.max[1] - hdr.min[1]))
                    density = round(hdr.point_count / area_est, 2)

                    lidar_meta.append({
                        "path": str(p.relative_to(repo_root)),
                        "point_count": hdr.point_count,
                        "density_pts_m2": density,
                        "crs": crs_str,
                        "bounds_min": b_min,
                        "bounds_max": b_max
                    })
            except Exception:
                continue

        return {
            "rasters": rasters_meta[:3],
            "lidar": lidar_meta[:3]
        }

    def get_layers_summary(self) -> List[Dict[str, Any]]:
        """Provides compact metadata for loaded/available vector layers."""
        repo_root = resolve_sandboxed_path(".")
        layers = []
        gt_path = repo_root / "data" / "ground_truth" / "tier1_teren.geojson"
        if gt_path.exists():
            try:
                import geopandas as gpd
                gdf = gpd.read_file(gt_path)
                b = gdf.total_bounds
                layers.append({
                    "name": "tier1_teren_ground_truth",
                    "type": "vector_polygon",
                    "crs": str(gdf.crs) if gdf.crs else "EPSG:3844",
                    "feature_count": len(gdf),
                    "extent": [round(float(c), 2) for c in b],
                    "source": "data/ground_truth/tier1_teren.geojson"
                })
            except Exception:
                pass

        # Check output directory
        ws_out = repo_root / "workspace" / "output"
        if ws_out.exists():
            import warnings
            for gpkg_path in ws_out.glob("*.gpkg"):
                try:
                    import geopandas as gpd
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        gdf = gpd.read_file(gpkg_path)
                    layers.append({
                        "name": gpkg_path.stem,
                        "type": "vector_layer",
                        "crs": str(gdf.crs) if gdf.crs else "EPSG:3844",
                        "feature_count": len(gdf),
                        "extent": [round(float(c), 2) for c in gdf.total_bounds] if len(gdf) > 0 else [],
                        "source": str(gpkg_path.relative_to(repo_root))
                    })
                except Exception:
                    pass

        return layers[:5]

    def get_providers_status(self) -> Dict[str, Any]:
        """Queries active AI provider registry health without hardcoding."""
        try:
            from stratum_ro.ai.registry import ProviderRegistry
            reg = ProviderRegistry()
            return reg.get_status_summary()
        except Exception as exc:
            return {"error": f"ProviderRegistry inspection failed: {exc}"}

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Returns structured, compact snapshot conforming to MD 4 Section 6.
        Cached with configurable TTL.
        """
        now = time.time()
        if self._cached_snapshot is not None and (now - self._last_snapshot_time) < self.cache_ttl_sec:
            return self._cached_snapshot

        qgis_info = detect_qgis_context()
        hardware_info = detect_hardware_context()
        aoi_info = self.get_aoi_context()
        inputs_info = self.get_inputs_metadata()
        layers_info = self.get_layers_summary()
        providers_info = self.get_providers_status()

        # CRS breakdown (Section 8: separate detected CRS for each domain)
        crs_breakdown = {
            "project_crs": "EPSG:3844",
            "vertical_datum": "EPSG:5781",
            "raster_crs": inputs_info["rasters"][0]["crs"] if inputs_info["rasters"] else "EPSG:3844",
            "lidar_crs": inputs_info["lidar"][0]["crs"] if inputs_info["lidar"] else "EPSG:3844",
            "vector_crs": layers_info[0]["crs"] if layers_info else "EPSG:3844"
        }

        snapshot = {
            "project": {
                "name": self.base_context.project_name,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "qgis": qgis_info,
                "output_dir": self.base_context.output_dir,
                "thresholds": self.base_context.thresholds
            },
            "crs": crs_breakdown,
            "aoi": aoi_info,
            "inputs": inputs_info,
            "layers": layers_info,
            "hardware": hardware_info,
            "providers": providers_info,
            "collected_at": round(now, 3)
        }

        self._cached_snapshot = snapshot
        self._last_snapshot_time = now
        return snapshot


_default_context_engine: Optional[ContextEngine] = None


def get_default_context_engine() -> ContextEngine:
    """Singleton getter for global ContextEngine."""
    global _default_context_engine
    if _default_context_engine is None:
        _default_context_engine = ContextEngine()
    return _default_context_engine


def get_context_snapshot() -> Dict[str, Any]:
    """Module-level helper to obtain current cached context snapshot."""
    return get_default_context_engine().get_snapshot()


def invalidate_context_cache():
    """Module-level helper to force context cache invalidation."""
    get_default_context_engine().invalidate()


def get_agent_context_package(
    task_type: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    MD 4 Section 26 & 27: Combines live environment context with task-aware relevant memory.
    Task-aware filtering prioritizes only data pertinent to task_type (e.g. segmentation vs export).
    """
    engine = get_default_context_engine()
    live_ctx = engine.get_snapshot()

    # Import SessionMemory safely
    from stratum_ro.ai.memory.session import SessionMemory
    memory = SessionMemory(session_id=session_id)

    recent_runs = memory.get_recent_runs(limit=3)
    relevant_memory: Dict[str, Any] = {
        "recent_runs": recent_runs
    }

    t_clean = (task_type or "").lower().strip()
    if "segment" in t_clean:
        # Prioritize raster, LiDAR, previous segmentation runs, validation results
        relevant_memory["past_segmentations"] = memory.search_memory("segmentation", category="task")
        relevant_memory["validations"] = memory.get_validation_history(limit=3)
    elif "export" in t_clean or "cad" in t_clean:
        # Prioritize CRS, geometry validations, approvals, previous export artifacts
        relevant_memory["approvals"] = memory.search_memory("export", category="approval")
        relevant_memory["exported_artifacts"] = memory.get_artifact_history(limit=5)
    elif "regulariz" in t_clean:
        relevant_memory["validations"] = memory.get_validation_history(limit=3)

    return {
        "status": "ready",
        "task_type": task_type or "general",
        "environment": live_ctx,
        "relevant_memory": relevant_memory
    }
