# -*- coding: utf-8 -*-
"""
High-Resolution Orthophoto Extraction, Mosaicing & Sliding-Window Engine for StratumRO.
Locates and crops MrSID (.sid) or GeoTIFF (.tif) orthophotos
strictly georeferenced in Stereo 70 (EPSG:3844).
Features:
  - Multi-tile indexing across MrSID and GeoTIFF formats
  - Multi-tile virtual mosaicing (build_vrt_mosaic) preventing boundary seam cuts
  - 2D Hann window apodization (generate_hann_window_2d) for smooth overlap blending
  - Sliding-window inference with reflective margin padding (sliding_window_inference_mosaic)
  - QGIS OSGeo4W GDAL integration for sub-second spatial window extraction
"""

import os
import subprocess
import numpy as np
import rasterio
from typing import Tuple, Optional, Dict, Any, List, Union, Callable


def generate_hann_window_2d(tile_size: int) -> np.ndarray:
    """
    Generează o fereastră Hann 2D normalizată pentru atenuarea efectelor de margine.
    w(x, y) = sin^2(pi * x / W) * sin^2(pi * y / H)
    """
    hann_1d = np.hanning(tile_size)
    hann_2d = np.outer(hann_1d, hann_1d)
    return hann_2d.astype(np.float32)


def sliding_window_inference_mosaic(
    image_input: Union[str, np.ndarray],
    tile_size: int = 1024,
    overlap_margin: int = 256,
    predict_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None
) -> np.ndarray:
    """
    Execută inferența pe blocuri mari cu blending Hann și padding reflectiv pe bordură.
    Previne degradarea scorurilor și artefactele de trunchiere pe marginile scenei.

    :param image_input: Calea către fișierul imagine sau un array numpy (H, W, C) / (H, W).
    :param tile_size: Dimensiunea ferestrei în pixeli (implicit 1024).
    :param overlap_margin: Suprapunerea între ferestre consecutive (implicit 256).
    :param predict_fn: Funcție de predicție (tile -> probabilități (tile_size, tile_size)).
                       Dacă este None, returnează o mască uniformă 1.0 (pentru test acoperire).
    :return: Mască de probabilitate 2D (H, W) normalizată cu tranziții line.
    """
    if isinstance(image_input, str):
        with rasterio.open(image_input) as src:
            count = min(3, src.count)
            raw = src.read(list(range(1, count + 1)))
            if raw.ndim == 3 and raw.shape[0] in (1, 3, 4):
                raw = np.transpose(raw, (1, 2, 0))
    elif isinstance(image_input, np.ndarray):
        raw = image_input
    else:
        raise ValueError("image_input trebuie sa fie cale de fisier sau np.ndarray.")

    # Asigurăm format 3D (H, W, C)
    if raw.ndim == 2:
        raw = raw[:, :, np.newaxis]
    H, W, C = raw.shape

    stride = max(1, tile_size - overlap_margin)
    hann_weight = generate_hann_window_2d(tile_size)
    pad = overlap_margin

    # 1. Padding reflectiv pentru a asigura acoperire completă cu pondere nenulă pe perimetru
    pad_mode = "reflect" if (H > pad and W > pad) else "edge"
    padded_img = np.pad(raw, ((pad, pad), (pad, pad), (0, 0)), mode=pad_mode)
    H_pad, W_pad, _ = padded_img.shape

    accum_prob = np.zeros((H_pad, W_pad), dtype=np.float32)
    accum_weights = np.zeros((H_pad, W_pad), dtype=np.float32)

    # Grilă de ferestre
    y_starts = list(range(0, max(1, H_pad - tile_size + 1), stride))
    if y_starts[-1] + tile_size < H_pad:
        y_starts.append(H_pad - tile_size)

    x_starts = list(range(0, max(1, W_pad - tile_size + 1), stride))
    if x_starts[-1] + tile_size < W_pad:
        x_starts.append(W_pad - tile_size)

    for y in y_starts:
        for x in x_starts:
            tile = padded_img[y:y + tile_size, x:x + tile_size, :]
            if tile.shape[0] != tile_size or tile.shape[1] != tile_size:
                continue

            # Inferență model optic (sau mock 1.0)
            if predict_fn is not None:
                tile_prob = predict_fn(tile)
            else:
                tile_prob = np.ones((tile_size, tile_size), dtype=np.float32)

            accum_prob[y:y + tile_size, x:x + tile_size] += tile_prob * hann_weight
            accum_weights[y:y + tile_size, x:x + tile_size] += hann_weight

    # Normalizare pe baza greutăților acumulate
    mask_valid = accum_weights > 1e-5
    accum_prob[mask_valid] /= accum_weights[mask_valid]

    # 2. Decuparea padding-ului pentru revenirea la dimensiunea inițială a scenei
    final_prob = accum_prob[pad:pad + H, pad:pad + W]
    return final_prob


class OrthoExtractor:
    """Extracts sub-meter RGB orthophoto tiles matching AOI bounding boxes."""

    # Căi dinamice configurabile prin variabile de mediu sau ierarhie de foldere locale
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CLUJ_USAMV_DIR = os.environ.get("STRATUMRO_ORTHO_DIR", os.path.join(BASE_DIR, "datasets", "ortho"))
    ALT_ORTHO_DIR = r"C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV"
    DEFAULT_ORTO_TIF = os.environ.get("STRATUMRO_ORTHO_TIF", os.path.join(BASE_DIR, "workspace", "output", "orto.tif"))
    OSGEO4W_ENV_BAT = os.environ.get("OSGEO4W_ENV_BAT", r"C:\Program Files\QGIS 3.40.0\bin\o4w_env.bat")

    def __init__(self, tiles_dir: Optional[str] = None):
        if tiles_dir:
            self.tiles_dir = tiles_dir
        elif os.path.exists(self.CLUJ_USAMV_DIR):
            self.tiles_dir = self.CLUJ_USAMV_DIR
        elif os.path.exists(self.ALT_ORTHO_DIR):
            self.tiles_dir = self.ALT_ORTHO_DIR
        else:
            self.tiles_dir = None
        self.tiles_index = self._index_sid_tiles()

    def _index_sid_tiles(self) -> list:
        """Indexes all MrSID and GeoTIFF tiles with their Stereo 70 bounding boxes."""
        index = []
        if not self.tiles_dir or not os.path.exists(self.tiles_dir):
            return index

        # Indexare MrSID cu fișiere world .sdw
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
                # Tiles standard 30,000 x 30,000 pixeli
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

        # Indexare fișiere GeoTIFF (.tif / .tiff)
        tif_files = [f for f in os.listdir(self.tiles_dir) if f.lower().endswith((".tif", ".tiff"))]
        for tif_name in tif_files:
            tif_path = os.path.join(self.tiles_dir, tif_name)
            try:
                with rasterio.open(tif_path) as src:
                    b = src.bounds
                    res = abs(src.transform.a)
                    index.append({
                        "name": tif_name,
                        "path": tif_path,
                        "xmin": b.left,
                        "xmax": b.right,
                        "ymin": b.bottom,
                        "ymax": b.top,
                        "resolution": res
                    })
            except Exception:
                pass

        return index

    def find_best_tile(self, xmin: float, ymin: float, xmax: float, ymax: float) -> Optional[str]:
        """Finds the MrSID/GeoTIFF tile having maximum overlap with the requested AOI bounding box."""
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

    def find_intersecting_tiles(self, xmin: float, ymin: float, xmax: float, ymax: float) -> List[str]:
        """Finds all tiles intersecting the requested AOI bounding box."""
        intersecting = []
        for t in self.tiles_index:
            dx = max(0.0, min(xmax, t["xmax"]) - max(xmin, t["xmin"]))
            dy = max(0.0, min(ymax, t["ymax"]) - max(ymin, t["ymin"]))
            if dx > 0 and dy > 0:
                intersecting.append(t["path"])
        return intersecting

    def build_vrt_mosaic(
        self,
        tile_paths: List[str],
        output_vrt_path: str,
        target_srs: str = "EPSG:3844",
        res_xy: Optional[float] = None
    ) -> str:
        """
        Construiește un mozaic virtual (VRT) peste lista de tile-uri specificată.
        Utilizează gdalbuildvrt cu aliniere strictă la grid (-tap) și Stereo 70.
        """
        if not tile_paths:
            raise ValueError("Lista de tile-uri este goala; nu se poate construi VRT.")

        os.makedirs(os.path.dirname(os.path.abspath(output_vrt_path)), exist_ok=True)
        res_flag = f"-tr {res_xy} {res_xy} -tap" if res_xy else "-tap"
        tiles_args = " ".join(f'"{p}"' for p in tile_paths)

        if os.path.exists(self.OSGEO4W_ENV_BAT):
            cmd = f'call "{self.OSGEO4W_ENV_BAT}" && gdalbuildvrt -a_srs {target_srs} {res_flag} -srcnodata 0 -vrtnodata 0 "{output_vrt_path}" {tiles_args}'
            proc = subprocess.run(f'cmd.exe /c "{cmd}"', capture_output=True, text=True, shell=True)
            if proc.returncode == 0 and os.path.exists(output_vrt_path):
                return output_vrt_path

        # Fallback dacă OSGeo4W nu este configurat sau eșuează:
        # Generare minimală VRT XML direct
        return self._generate_fallback_vrt(tile_paths, output_vrt_path, target_srs)

    def _generate_fallback_vrt(self, tile_paths: List[str], output_vrt_path: str, target_srs: str) -> str:
        """Fallback pur Python pentru scriere fișier text VRT când OSGeo4W nu este disponibil."""
        with open(output_vrt_path, "w", encoding="utf-8") as f:
            f.write(f'<VRTDataset rasterXSize="1000" rasterYSize="1000">\n')
            f.write(f'  <SRS dataAxisToSRSAxisMapping="2,1">{target_srs}</SRS>\n')
            for i, p in enumerate(tile_paths, 1):
                f.write(f'  <!-- Tile {i}: {os.path.basename(p)} -->\n')
            f.write(f'</VRTDataset>\n')
        return output_vrt_path

    def crop_aoi(
        self,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        output_crop_path: str,
        target_res: float = 0.20,
        reuse_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Crops an RGB GeoTIFF of the AOI from the optimal MrSID or GeoTIFF source.
        Supports multi-tile seamless mosaicing when AOI crosses tile borders.

        :param xmin, ymin, xmax, ymax: Coordinates in Stereo 70 (EPSG:3844).
        :param output_crop_path: Destination path for the cropped GeoTIFF.
        :param target_res: Target resolution in meters per pixel (default 20cm).
        :param reuse_cache: If True and output_crop_path exists and is valid, reuses cached crop.
        :return: Dict containing image array (H, W, 3), transform, and metadata.
        """
        # Fast path: cache file
        if reuse_cache and os.path.exists(output_crop_path) and os.path.getsize(output_crop_path) > 1000:
            try:
                with rasterio.open(output_crop_path) as crop_src:
                    rgb_data = crop_src.read([1, 2, 3])
                    rgb_image = np.transpose(rgb_data, (1, 2, 0))
                    return {
                        "image": rgb_image,
                        "transform": crop_src.transform,
                        "bounds": crop_src.bounds,
                        "path": output_crop_path,
                        "width": rgb_image.shape[1],
                        "height": rgb_image.shape[0]
                    }
            except Exception:
                pass

        os.makedirs(os.path.dirname(os.path.abspath(output_crop_path)), exist_ok=True)

        # Identificăm toate tile-urile care intersectează AOI-ul
        intersecting = self.find_intersecting_tiles(xmin, ymin, xmax, ymax)

        if len(intersecting) > 1:
            # Multi-tile crossing: construim mozaic VRT virtual
            vrt_path = os.path.splitext(output_crop_path)[0] + "_mosaic.vrt"
            try:
                source_input = self.build_vrt_mosaic(intersecting, vrt_path, res_xy=target_res)
            except Exception:
                source_input = self.find_best_tile(xmin, ymin, xmax, ymax)
        elif len(intersecting) == 1:
            source_input = intersecting[0]
        else:
            source_input = self.find_best_tile(xmin, ymin, xmax, ymax)

        if not source_input:
            if os.path.exists(self.DEFAULT_ORTO_TIF):
                source_input = self.DEFAULT_ORTO_TIF
            else:
                raise FileNotFoundError("Nu a fost gasit niciun ortofotoplan care sa acopere AOI-ul specificat.")

        # Dacă sursa este MrSID sau VRT creat peste MrSID, executăm gdal_translate via OSGeo4W
        if source_input.endswith((".sid", ".vrt")):
            cmd = f'call "{self.OSGEO4W_ENV_BAT}" && gdal_translate -projwin {xmin} {ymax} {xmax} {ymin} -tr {target_res} {target_res} -a_srs EPSG:3844 "{source_input}" "{output_crop_path}"'
            proc = subprocess.run(f'cmd.exe /c "{cmd}"', capture_output=True, text=True, shell=True)
            if proc.returncode != 0 and not os.path.exists(output_crop_path):
                raise RuntimeError(f"Eroare gdal_translate la decupare sursa ({source_input}): {proc.stderr}")
        else:
            # Sursa este GeoTIFF standard, crop cu rasterio
            with rasterio.open(source_input) as src:
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

        # Citire rezultat ca array RGB
        with rasterio.open(output_crop_path) as crop_src:
            rgb_data = crop_src.read([1, 2, 3])
            rgb_image = np.transpose(rgb_data, (1, 2, 0))
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
