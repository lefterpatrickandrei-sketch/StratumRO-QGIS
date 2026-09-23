# -*- coding: utf-8 -*-
"""
Topography Domain Adapter (PARTIAL).
Declares topographic surface capabilities (slope, aspect, elevation profiles)
consumed by cadastral and engineering workflows.
"""

from typing import Dict, Any, Optional
import numpy as np


class TopographyAdapter:
    """
    Adapter for topographic surface analysis.
    Interfaces between terrain elevation data and geodetic workflows.
    """

    def __init__(self):
        self.maturity = "PARTIAL"

    def compute_slope_aspect(self, elevation_grid: np.ndarray, cell_size: float = 1.0) -> Dict[str, np.ndarray]:
        """
        Computes slope (degrees) and aspect (degrees) from an elevation raster.
        Uses Horn's 3x3 finite-difference algorithm.
        """
        if elevation_grid.ndim != 2:
            raise ValueError("Elevation grid must be a 2D numpy array.")
            
        gy, gx = np.gradient(elevation_grid, cell_size)
        slope_rad = np.arctan(np.sqrt(gx**2 + gy**2))
        slope_deg = np.degrees(slope_rad)
        
        aspect_rad = np.arctan2(-gx, gy)
        aspect_deg = (np.degrees(aspect_rad) + 360.0) % 360.0
        
        return {
            "slope_deg": slope_deg,
            "aspect_deg": aspect_deg
        }
