# -*- coding: utf-8 -*-
"""
Platform Service for StratumRO Geospatial Backend.
Encapsulates geodetic operations, QGIS MCP socket communication,
GeoJSON reprojection for web visualization, and workflow execution.
"""

import base64
import json
import os
import socket
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Coordinate transformer: Stereo 70 (EPSG:3844) -> WGS84 (EPSG:4326) for Web Map
# Note: Stereo 70 is (X: Northing, Y: Easting) in classic Romanian geodesy,
# but EPSG:3844 in PROJ standard expects (Easting, Northing).
# We use always_xy=True to ensure (Easting, Northing) -> (Longitude, Latitude).
TRANSFORMER_3844_TO_4326 = Transformer.from_crs("EPSG:3844", "EPSG:4326", always_xy=True)


class PlatformService:
    """
    Central service connecting FastAPI to QGIS live socket,
    geospatial files, geodetic transformers, and AI orchestration.
    """

    def __init__(self, root: Optional[Path] = None):
        self.root = root or PROJECT_ROOT
        self.qgis_host = "127.0.0.1"
        self.qgis_port = 9876

    def query_qgis(self, msg_type: str, params: Optional[Dict[str, Any]] = None, timeout: float = 8.0) -> Dict[str, Any]:
        """Sends a framed JSON command to live QGIS MCP socket and returns decoded response."""
        params = params or {}
        req = {"type": msg_type, "params": params}
        payload = json.dumps(req).encode("utf-8")

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.qgis_host, self.qgis_port))
            s.sendall(struct.pack(">I", len(payload)) + payload)

            raw_len = s.recv(4)
            if len(raw_len) != 4:
                s.close()
                return {"status": "error", "message": "Incomplete socket header from QGIS"}

            resp_len = struct.unpack(">I", raw_len)[0]
            data = b""
            while len(data) < resp_len:
                chunk = s.recv(min(65536, resp_len - len(data)))
                if not chunk:
                    break
                data += chunk
            s.close()

            return json.loads(data.decode("utf-8"))
        except Exception as e:
            return {"status": "error", "message": f"QGIS socket connection error: {str(e)}"}

    def get_qgis_layers(self) -> List[Dict[str, Any]]:
        """Retrieves layers in the active QGIS project."""
        res = self.query_qgis("get_layers")
        if res.get("status") == "success":
            return res.get("result", {}).get("layers", [])
        return []

    def get_qgis_canvas_base64(self) -> Optional[str]:
        """Retrieves real-time canvas screenshot from QGIS Desktop as base64 string."""
        res = self.query_qgis("get_canvas_screenshot", timeout=12.0)
        if res.get("status") == "success":
            return res.get("result", {}).get("base64_data")
        return None

    def zoom_to_layer(self, layer_id: str) -> bool:
        """Sends zoom-to-layer command to QGIS Desktop."""
        res = self.query_qgis("zoom_to_layer", {"layer_id": layer_id})
        return res.get("status") == "success"

    def load_geojson_web(self, relative_path: str) -> Dict[str, Any]:
        """
        Loads a GeoJSON in Stereo 70 (EPSG:3844) and reprojects geometries
        to WGS84 (EPSG:4326) for interactive Leaflet rendering, while preserving
        original Stereo 70 coordinates in feature properties for surveyor accuracy.
        """
        fp = self.root / relative_path
        if not fp.exists():
            return {"type": "FeatureCollection", "features": []}

        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)

            features = []
            for feat in data.get("features", []):
                geom_raw = feat.get("geometry")
                props = dict(feat.get("properties") or {})
                if not geom_raw:
                    continue

                sh_geom = shape(geom_raw)
                # Store original Stereo 70 area & perimeter
                props["stereo70_area_m2"] = round(sh_geom.area, 2)
                props["stereo70_length_m"] = round(sh_geom.length, 2)

                # Reproject geometry to WGS84
                reprojected = transform(TRANSFORMER_3844_TO_4326.transform, sh_geom)
                features.append({
                    "type": "Feature",
                    "geometry": mapping(reprojected),
                    "properties": props
                })

            return {
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
                "features": features
            }
        except Exception as e:
            return {"type": "FeatureCollection", "features": [], "error": str(e)}

    def get_dataset_bounds_wgs84(self) -> List[List[float]]:
        """
        Returns bounding coordinates in [[lat_min, lon_min], [lat_max, lon_max]]
        for the active Cluj AOI (Stereo 70 X: 585000-585500, Y: 392000-392400 approx).
        """
        # Benchmark Cluj coordinates in Stereo 70
        x_min, y_min = 392000.0, 585000.0
        x_max, y_max = 392500.0, 585400.0

        lon_min, lat_min = TRANSFORMER_3844_TO_4326.transform(x_min, y_min)
        lon_max, lat_max = TRANSFORMER_3844_TO_4326.transform(x_max, y_max)

        return [[lat_min, lon_min], [lat_max, lon_max]]
