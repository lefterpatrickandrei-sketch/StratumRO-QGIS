# -*- coding: utf-8 -*-
"""
Project Context Engine for StratumRO AI.
Extracts project configuration, geodetic parameters, active raster/LiDAR layers,
and ANCPI cadastral thresholds from config.yaml and the filesystem.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class ProjectContext:
    project_name: str = "StratumRO_Default"
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
            # Check fallback in data/
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
