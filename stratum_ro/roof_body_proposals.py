"""Deterministic color-guided roof body proposals from RGB and LiDAR evidence.

Extracts candidate roof bodies based on spectral cues (neutral, red) restricted
to LiDAR returns with building evidence (class 6).
This step generates prompt hypotheses for downstream delineation and inspection;
it never provides final cadastral approval.
"""
from typing import Any, Dict, List, Optional
import numpy as np
import rasterio.transform
from rasterio.features import shapes
from scipy.ndimage import (
    binary_closing,
    distance_transform_edt,
    label,
    find_objects,
)
from shapely.geometry import shape, Point


def color_body_proposals(
    lidar_data: Dict[str, Any],
    image_rgb: np.ndarray,
    image_transform: Any,
    min_area_m2: float = 20.0,
) -> List[Dict[str, Any]]:
    """Propose candidate roof bodies from RGB imagery and LiDAR building returns.

    Parameters
    ----------
    lidar_data : dict
        LiDAR analysis product containing:
          - 'transform': rasterio Affine transform for the LiDAR grid.
          - 'class_evidence': dict containing 'building' (and optionally 'observed', 'vegetation').
          - optionally 'ndsm': 2D height array to verify grid shape.
    image_rgb : np.ndarray
        RGB image of shape (H, W, 3) or (3, H, W), finite uint8 or float in 0..255.
    image_transform : Affine or transform-like
        Affine transform for image_rgb.
    min_area_m2 : float, default 20.0
        Minimum physical area threshold in square meters.

    Returns
    -------
    list of dict
        Each proposal contains:
          - 'geometry': shapely geometry (Polygon or MultiPolygon) in map coordinates.
          - 'mask': 2D boolean ndarray within the returned bounding slice (ROI).
          - 'slice': tuple of slice objects (row_slice, col_slice) bounding the component.
          - 'area_m2': float, physical area in square meters.
          - 'source': str, 'COLOR_NEUTRAL' or 'COLOR_RED'.
          - 'positive_point_geo': shapely Point in map coordinates, chosen at the
            distance transform maximum within the component.
    """
    # 1. Validate inputs
    if not isinstance(lidar_data, dict):
        raise ValueError("lidar_data must be a dictionary")

    if "transform" not in lidar_data:
        raise ValueError("lidar_data missing 'transform'")
    lidar_transform = lidar_data["transform"]
    if not isinstance(lidar_transform, rasterio.transform.Affine):
        try:
            lidar_transform = rasterio.transform.Affine(*lidar_transform[:6])
        except Exception as err:
            raise ValueError(f"Invalid lidar_transform: {err}")

    det_lidar = lidar_transform.a * lidar_transform.e - lidar_transform.b * lidar_transform.d
    if not np.all(np.isfinite(tuple(lidar_transform))) or abs(det_lidar) <= 1e-12:
        raise ValueError("lidar_transform must be finite and nonsingular")

    if "class_evidence" not in lidar_data or not isinstance(lidar_data["class_evidence"], dict):
        raise ValueError("lidar_data missing 'class_evidence' dict")

    class_evidence = lidar_data["class_evidence"]
    if "building" not in class_evidence:
        raise ValueError("class_evidence must contain 'building' count array")

    building_counts = np.asarray(class_evidence["building"])
    if building_counts.ndim != 2:
        raise ValueError("building count array must be 2D")
    if 'ndsm' in lidar_data and np.asarray(lidar_data['ndsm']).shape != building_counts.shape:
        raise ValueError('nDSM and building evidence shapes must match')
    if not np.all(np.isfinite(building_counts)) or np.any(building_counts < 0):
        raise ValueError("building counts must be finite and nonnegative")

    lidar_rows, lidar_cols = building_counts.shape
    if lidar_rows <= 0 or lidar_cols <= 0:
        raise ValueError("LiDAR grid must be non-empty")

    if not isinstance(min_area_m2, (int, float, np.floating, np.integer)):
        raise ValueError("min_area_m2 must be a finite positive number")
    min_area = float(min_area_m2)
    if not np.isfinite(min_area) or min_area <= 0.0:
        raise ValueError("min_area_m2 must be finite and positive")

    # Image validation
    img = np.asarray(image_rgb)
    if not np.all(np.isfinite(img)):
        raise ValueError("image_rgb must contain finite values")

    if img.ndim != 3:
        raise ValueError("image_rgb must be a 3D array")

    # Support (H, W, 3) or (3, H, W)
    if img.shape[2] == 3:
        img_h, img_w = img.shape[0], img.shape[1]
        # Channels last
        img_channels_last = img
    elif img.shape[0] == 3:
        img_h, img_w = img.shape[1], img.shape[2]
        img_channels_last = np.transpose(img, (1, 2, 0))
    else:
        raise ValueError(f"image_rgb must have 3 channels, got shape {img.shape}")

    if img_h <= 0 or img_w <= 0:
        raise ValueError("image_rgb dimensions must be positive")

    if not np.issubdtype(img.dtype, np.uint8):
        if not np.issubdtype(img.dtype, np.floating) and not np.issubdtype(img.dtype, np.integer):
            raise ValueError("image_rgb must be uint8 or float")
        if np.any(img < 0) or np.any(img > 255):
            raise ValueError("image_rgb values must be in range [0, 255]")

    # Image transform validation
    if not isinstance(image_transform, rasterio.transform.Affine):
        try:
            img_transform = rasterio.transform.Affine(*image_transform[:6])
        except Exception as err:
            raise ValueError(f"Invalid image_transform: {err}")
    else:
        img_transform = image_transform

    det_img = img_transform.a * img_transform.e - img_transform.b * img_transform.d
    if not np.all(np.isfinite(tuple(img_transform))) or abs(det_img) <= 1e-12:
        raise ValueError("image_transform must be finite and nonsingular")

    try:
        inv_img_transform = ~img_transform
    except Exception as err:
        raise ValueError(f"Cannot invert image_transform: {err}")

    # Physical pixel area of LiDAR cell
    cell_area_m2 = abs(det_lidar)

    # 2. Sample RGB at LiDAR cell centers
    # Coordinates of LiDAR cell centers: (col + 0.5, row + 0.5)
    r_idx, c_idx = np.indices((lidar_rows, lidar_cols))
    x_geo, y_geo = lidar_transform * (c_idx + 0.5, r_idx + 0.5)

    # Transform map coordinates to image coordinates
    img_c_f, img_r_f = inv_img_transform * (x_geo, y_geo)

    # Inside-image cells: floor indices
    valid_finite = np.isfinite(img_c_f) & np.isfinite(img_r_f)
    img_c = np.floor(img_c_f).astype(np.int64)
    img_r = np.floor(img_r_f).astype(np.int64)

    valid_inside = valid_finite & (img_c >= 0) & (img_c < img_w) & (img_r >= 0) & (img_r < img_h)

    # Initialize sampled RGB arrays
    sampled_rgb = np.zeros((lidar_rows, lidar_cols, 3), dtype=np.float32)
    if np.any(valid_inside):
        sampled_rgb[valid_inside] = img_channels_last[img_r[valid_inside], img_c[valid_inside]].astype(np.float32)

    R = sampled_rgb[..., 0]
    G = sampled_rgb[..., 1]
    B = sampled_rgb[..., 2]

    # Candidate color classes:
    # NEUTRAL: saturation (max-min)/max <= 0.25 with max >= 1
    # RED: R - G > 25 and R - B > 15
    rgb_max = np.maximum(np.maximum(R, G), B)
    rgb_min = np.minimum(np.minimum(R, G), B)

    # Avoid division by zero where rgb_max == 0
    safe_max = np.where(rgb_max >= 1.0, rgb_max, 1.0)
    saturation = (rgb_max - rgb_min) / safe_max
    neutral_mask = (saturation <= 0.25) & (rgb_max >= 1.0)

    red_mask = ((R - G) > 25.0) & ((R - B) > 15.0)

    # Strict restriction: valid_inside AND building evidence > 0
    building_evidence_mask = (building_counts > 0)
    base_valid = valid_inside & building_evidence_mask

    raw_classes = [
        ("COLOR_NEUTRAL", neutral_mask & base_valid),
        ("COLOR_RED", red_mask & base_valid),
    ]

    proposals: List[Dict[str, Any]] = []
    footprint_3x3 = np.ones((3, 3), dtype=bool)

    for source_name, candidate_mask in raw_classes:
        if not np.any(candidate_mask):
            continue

        # Morphological closing 3x3 to bridge local roof gaps
        closed = binary_closing(np.pad(candidate_mask, 1), structure=footprint_3x3)[1:-1,1:-1]
        # Restrict closed mask back to the valid candidate color region
        # This only creates prompt hypotheses, never approval
        color_region = neutral_mask if source_name == 'COLOR_NEUTRAL' else red_mask
        filtered_mask = closed & color_region & valid_inside

        if not np.any(filtered_mask):
            continue

        # Four-connectivity avoids merging diagonal roof corners into one body.
        lbl, num_features = label(filtered_mask)
        if num_features == 0:
            continue

        slices = find_objects(lbl)
        for comp_idx, sl in enumerate(slices, start=1):
            if sl is None:
                continue

            comp_bool = (lbl[sl] == comp_idx)
            cell_count = int(np.sum(comp_bool))
            area_m2 = float(cell_count * cell_area_m2)

            if area_m2 < min_area:
                continue

            # Rasterio shapes on the component
            comp_uint8 = comp_bool.astype(np.uint8)
            sub_transform = lidar_transform * rasterio.transform.Affine.translation(sl[1].start, sl[0].start)
            poly_geoms = [
                shape(geom)
                for geom, val in shapes(comp_uint8, mask=comp_bool, transform=sub_transform)
                if val == 1
            ]
            if not poly_geoms:
                continue

            if len(poly_geoms) == 1:
                prop_geom = poly_geoms[0]
            else:
                from shapely.ops import unary_union
                prop_geom = unary_union(poly_geoms)

            # Positive prompt point inside geometry chosen via padded distance_transform
            # Compute distance transform on component
            dist = distance_transform_edt(np.pad(comp_bool,1))[1:-1,1:-1]
            dist[~candidate_mask[sl]] = 0
            # Find maximum in the component
            max_r, max_c = np.unravel_index(np.argmax(dist), dist.shape)

            # Coordinate of center of cell (max_r, max_c)
            px, py = sub_transform * (max_c + 0.5, max_r + 0.5)
            pos_pt = Point(px, py)

            proposals.append({
                "geometry": prop_geom,
                "mask": comp_bool,
                "slice": sl,
                "area_m2": area_m2,
                "source": source_name,
                "positive_point_geo": pos_pt,
            })

    return proposals
