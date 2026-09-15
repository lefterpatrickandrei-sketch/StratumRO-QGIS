# -*- coding: utf-8 -*-
"""
Project & Workspace Context Tool Wrappers for StratumRO AI.
Inspects active workspace files, CRS parameters, and GPU hardware.
"""

import os
from pathlib import Path
from typing import Any, Dict


def get_workspace_context(base_dir: str = ".") -> Dict[str, Any]:
    """
    Returns environment metadata: CRS, data paths, output directory, and GPU status.
    """
    p_base = Path(base_dir).resolve()

    # Hardware detection
    gpu_available = False
    device_name = "CPU"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            device_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    # Inspect key directories
    ws_output = p_base / "workspace" / "output"
    gt_dir = p_base / "data" / "ground_truth"

    return {
        "base_directory": str(p_base),
        "crs": "EPSG:3844",
        "vertical_datum": "EPSG:5781",
        "hardware": {
            "gpu_available": gpu_available,
            "device": device_name,
            "os": os.name
        },
        "workspace_exists": ws_output.exists(),
        "ground_truth_exists": gt_dir.exists(),
        "status": "ready"
    }
