# -*- coding: utf-8 -*-
"""
High-Resolution Orthophoto Extraction & Cropping Engine for StratumRO.
Locates and crops MrSID (.sid) or GeoTIFF (.tif) orthophotos
strictly georeferenced in Stereo 70 (EPSG:3844).
Uses QGIS OSGeo4W GDAL for rapid spatial window extraction.
"""

import os
import subprocess
import numpy as np
import rasterio
from typing import Tuple, Optional, Dict, Any


class OrthoExtractor:
    """Extracts sub-meter RGB orthophoto tiles matching AOI bounding boxes."""

    # Căi dinamice configurabile prin variabile de mediu sau ierarhie de foldere locale
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CLUJ_USAMV_DIR = os.environ.get("STRATUMRO_ORTHO_DIR", os.path.join(BASE_DIR, "datasets", "ortho"))
    DEFAULT_ORTO_TIF = os.environ.get("STRATUMRO_ORTHO_TIF", os.path.join(BASE_DIR, "workspace", "output", "orto.tif"))
    _DEV_FALLBACK_DIR = r"C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV"
    _DEV_FALLBACK_TIF = r"C:\Users\lefpa\Desktop\date\georeferentiere\ORTO\ORTO.tif"
    OSGEO4W_ENV_BAT = os.environ.get("OSGEO4W_ENV_BAT", r"C:\Program Files\QGIS 3.40.0\bin\o4w_env.bat")

    def __init__(self, tiles_dir: Optional[str] = None):
        if tiles_dir:
            self.tiles_dir = tiles_dir
        elif os.path.exists(self.CLUJ_USAMV_DIR):
            self.tiles_dir = self.CLUJ_USAMV_DIR
        elif os.path.exists(self._DEV_FALLBACK_DIR):
            self.tiles_dir = self._DEV_FALLBACK_DIR
        else:
            self.tiles_dir = None
        self.tiles_index = self._index_sid_tiles()

    def _index_sid_tiles(self) -> list:
        """Indexes all MrSID tiles with their Stereo 70 bounding boxes."""
        index = []
        if not self.tiles_dir or not os.path.exists(self.tiles_dir):
            return index

        sdw_files = [f for f in os.listdir(self.tiles_dir) if f.endswith(".sdw")]
        for sdw_name in sdw_files:
            sid_name = sdw_name.replace(".sdw", ".sid")
            sid_path = os.path.join(self.tiles_dir, sid_name)
            sdw_path = os.path.join(self.tiles_dir, sdw_name)

            if not os.path.exists(sid_path):
                continue

            try:
                with open(sdw_path, "r", encoding="utf-8") as f:
                    lines = [float(l.strip()) for l in f.readlines() if l.strip()]
                rx = lines[0]
                ry = lines[3]
                x0 = lines[4]
                y0 = lines[5]
                # Tiles are standard 30,000 x 30,000 pixels
                w, h = 30000, 30000
                x1 = x0 + w * rx
                y1 = y0 + h * ry

                index.append({
                    "name": sid_name,
                    "path": sid_path,
                    "xmin": min(x0, x1),
                    "xmax": max(x0, x1),
                    "ymin": min(y0, y1),
                    "ymax": max(y0, y1),
                    "resolution": rx
                })
            except Exception as e:
                print(f"[OrthoExtractor] Warning: could not parse {sdw_name}: {e}")

        return index

    def find_best_tile(self, xmin: float, ymin: float, xmax: float, ymax: float) -> Optional[str]:
        """Finds the MrSID tile having maximum overlap with the requested AOI bounding box."""
        best_tile = None
        max_overlap = 0.0

        for t in self.tiles_index:
            dx = max(0.0, min(xmax, t["xmax"]) - max(xmin, t["xmin"]))
            dy = max(0.0, min(ymax, t["ymax"]) - max(ymin, t["ymin"]))
            overlap = dx * dy
            if overlap > max_overlap:
                max_overlap = overlap
                best_tile = t["path"]

        return best_tile

    def crop_aoi(
        self,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        output_crop_path: str,
        target_res: float = 0.20
    ) -> Dict[str, Any]:
        """
        Crops an RGB GeoTIFF of the AOI from the optimal MrSID or GeoTIFF source.

        :param xmin, ymin, xmax, ymax: Coordinates in Stereo 70 (EPSG:3844).
        :param output_crop_path: Destination path for the cropped GeoTIFF.
        :param target_res: Target resolution in meters per pixel (default 20cm).
        :return: Dict containing image array (H, W, 3), transform, and metadata.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_crop_path)), exist_ok=True)
        source_sid = self.find_best_tile(xmin, ymin, xmax, ymax)

        if not source_sid:
            if os.path.exists(self.DEFAULT_ORTO_TIF):
                source_sid = self.DEFAULT_ORTO_TIF
            else:
                raise FileNotFoundError("Nu a fost gasit niciun ortofotoplan care sa acopere AOI-ul specificat.")

        # If source is MrSID, execute gdal_translate via QGIS environment
        if source_sid.endswith(".sid"):
            cmd = f'call "{self.OSGEO4W_ENV_BAT}" && gdal_translate -projwin {xmin} {ymax} {xmax} {ymin} -tr {target_res} {target_res} -a_srs EPSG:3844 "{source_sid}" "{output_crop_path}"'
            proc = subprocess.run(f'cmd.exe /c "{cmd}"', capture_output=True, text=True, shell=True)
            if proc.returncode != 0 and not os.path.exists(output_crop_path):
                raise RuntimeError(f"Eroare gdal_translate la decupare MrSID: {proc.stderr}")
        else:
            # Source is standard GeoTIFF, crop using rasterio
            with rasterio.open(source_sid) as src:
                inv = ~src.transform
                c1, r1 = inv * (xmin, ymax)
                c2, r2 = inv * (xmax, ymin)
                window = rasterio.windows.Window.from_slices(
                    (int(min(r1, r2)), int(max(r1, r2))),
                    (int(min(c1, c2)), int(max(c1, c2)))
                )
                data = src.read(window=window)
                new_transform = rasterio.windows.transform(window, src.transform)
                with rasterio.open(
                    output_crop_path, "w", driver="GTiff",
                    height=data.shape[1], width=data.shape[2], count=min(3, data.shape[0]),
                    dtype=data.dtype, crs="EPSG:3844", transform=new_transform
                ) as dst:
                    dst.write(data[:3])

        # Read the cropped GeoTIFF as RGB array
        with rasterio.open(output_crop_path) as crop_src:
            rgb_data = crop_src.read([1, 2, 3])  # Shape: (3, H, W)
            rgb_image = np.transpose(rgb_data, (1, 2, 0))  # Shape: (H, W, 3)
            transform = crop_src.transform
            bounds = crop_src.bounds

        return {
            "image": rgb_image,
            "transform": transform,
            "bounds": bounds,
            "path": output_crop_path,
            "width": rgb_image.shape[1],
            "height": rgb_image.shape[0]
        }
