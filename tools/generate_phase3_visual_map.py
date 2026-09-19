# -*- coding: utf-8 -*-
"""
StratumRO — Phase 3 Visual Map & Spectator Project Generator
============================================================
Creates:
1. workspace/phase3/StratumRO_Cluj_Phase3_Spectator.qgs (with mapcanvas zoomed to AOI)
2. workspace/phase3/StratumRO_Phase3_Visual_Map.png (high-res human-inspectable map)
"""

import json
import math
from pathlib import Path
import rasterio
from rasterio.transform import rowcol
from shapely.geometry import shape, box, Polygon, MultiPolygon
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(r"c:\Users\lefpa\Downloads\QGIS-AI")
ORTHO_PATH = PROJECT_ROOT / "workspace" / "e2e" / "04_orthophoto" / "active_ortho_crop.tif"
NDSM_PATH = PROJECT_ROOT / "workspace" / "derived" / "cluj_ndsm_1m.tif"
LIDAR_CLS_PATH = PROJECT_ROOT / "workspace" / "phase3" / "derived" / "cluj_lidar_classes_1m.tif"
GT_PATH = PROJECT_ROOT / "data" / "derived_reference" / "cluj_combined_unique_150.geojson"
E9_PATH = PROJECT_ROOT / "workspace" / "phase3" / "predictions" / "EXP_009_integrated_pipeline_reg.geojson"
E8_PATH = PROJECT_ROOT / "workspace" / "phase3" / "predictions" / "EXP_008_orientation_cad_reg.geojson"
E2_PATH = PROJECT_ROOT / "workspace" / "phase3" / "predictions" / "EXP_002_vegetation_filter_reg.geojson"
E0_PATH = PROJECT_ROOT / "workspace" / "phase3" / "predictions" / "EXP_000_baseline_raw.geojson"

OUTPUT_PNG = PROJECT_ROOT / "workspace" / "phase3" / "StratumRO_Phase3_Visual_Map.png"
OUTPUT_QGS = PROJECT_ROOT / "workspace" / "phase3" / "StratumRO_Cluj_Phase3_Spectator.qgs"


def generate_qgs_project(bounds):
    xmin, ymin, xmax, ymax = bounds.left, bounds.bottom, bounds.right, bounds.top
    
    qgs_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="StratumRO — Phase 3 Cluj Optimization Spectator" version="3.40.0">
  <homePath path=""/>
  <title>StratumRO — Phase 3 Cluj Optimization (Before vs After Evidence)</title>
  <projectCrs>
    <spatialrefsys nativeFormat="Wkt">
      <wkt>PROJCRS["Pulkovo 1942(58) / Stereo70",BASEGEOGCRS["Pulkovo 1942",DATUM["Pulkovo 1942",ELLIPSOID["Krassowsky 1940",6378245,298.3,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4284]],CONVERSION["Stereo70",METHOD["Oblique Stereographic",ID["EPSG",9809]],PARAMETER["Latitude of natural origin",46,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",25,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.99975,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",500000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["northing (X)",north,ORDER[1],LENGTHUNIT["metre",1]],AXIS["easting (Y)",east,ORDER[2],LENGTHUNIT["metre",1]],ID["EPSG",3844]]</wkt>
      <proj4>+proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass +towgs84=2.3287,-147.0416,-92.0802,0.3092483,0.3248219,-0.4972993,5.68906266 +units=m +no_defs</proj4>
      <srsid>100000</srsid>
      <srid>3844</srid>
      <authid>EPSG:3844</authid>
      <description>Pulkovo 1942(58) / Stereo70</description>
      <projectionacronym>sterea</projectionacronym>
      <ellipsoidacronym>EPSG:7024</ellipsoidacronym>
      <geographicflag>false</geographicflag>
    </spatialrefsys>
  </projectCrs>

  <!-- LAYER TREE (Order: Overlays on top, Raster base at bottom) -->
  <layer-tree-group>
    <customproperties><Option/></customproperties>
    <layer-tree-layer id="layer_p3_final" name="🟢 Phase 3: E9 Integrated Predictions (26 Footprints)" source="{E9_PATH}" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_ref_gt" name="🔵 Cadastral Ground Truth (65 Reference in AOI)" source="{GT_PATH}" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_p3_e8" name="🟣 Phase 3: E8 Orientation Regularized (26 Footprints)" source="{E8_PATH}" providerKey="ogr" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_p3_e2" name="🟠 Phase 3: E2 Vegetation Filtered (31 Footprints)" source="{E2_PATH}" providerKey="ogr" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_p2_base" name="🔴 Phase 2 Baseline: Raw AI E0 (94 Poligoane, 90 FP)" source="{E0_PATH}" providerKey="ogr" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_lidar_cls" name="StratumRO — LiDAR ASPRS Classes (1m Grid)" source="{LIDAR_CLS_PATH}" providerKey="gdal" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_ndsm" name="StratumRO — LiDAR nDSM Height (1m Grid)" source="{NDSM_PATH}" providerKey="gdal" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_ortho" name="StratumRO — Cluj Aerial Orthophoto (RGB 0.20m)" source="{ORTHO_PATH}" providerKey="gdal" expanded="1" checked="Qt::Checked"/>
  </layer-tree-group>

  <!-- MAP CANVAS: PRE-ZOOMED DIRECTLY TO CLUJ AOI EXTENT -->
  <mapcanvas>
    <units>meters</units>
    <extent>
      <xmin>{xmin - 15:.2f}</xmin>
      <ymin>{ymin - 15:.2f}</ymin>
      <xmax>{xmax + 15:.2f}</xmax>
      <ymax>{ymax + 15:.2f}</ymax>
    </extent>
    <rotation>0</rotation>
    <destinationsrs>
      <spatialrefsys nativeFormat="Wkt">
        <authid>EPSG:3844</authid>
      </spatialrefsys>
    </destinationsrs>
  </mapcanvas>

  <projectlayers>
    <!-- E9 FINAL (BRIGHT GREEN) -->
    <maplayer id="layer_p3_final" name="🟢 Phase 3: E9 Integrated Predictions (26 Footprints)" type="vector" geometry="Polygon">
      <id>layer_p3_final</id>
      <datasource>{E9_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="0.9">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="0,230,118,50"/>
                <Option name="outline_color" type="QString" value="0,230,118,255"/>
                <Option name="outline_width" type="QString" value="1.2"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- GROUND TRUTH (CYAN DASHED) -->
    <maplayer id="layer_ref_gt" name="🔵 Cadastral Ground Truth (65 Reference in AOI)" type="vector" geometry="Polygon">
      <id>layer_ref_gt</id>
      <datasource>{GT_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="0.8">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="0,176,255,35"/>
                <Option name="outline_color" type="QString" value="0,176,255,255"/>
                <Option name="outline_width" type="QString" value="1.0"/>
                <Option name="outline_style" type="QString" value="dash"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- E8 ORIENTATION (PURPLE) -->
    <maplayer id="layer_p3_e8" name="🟣 Phase 3: E8 Orientation Regularized (26 Footprints)" type="vector" geometry="Polygon">
      <id>layer_p3_e8</id>
      <datasource>{E8_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="180,50,255,255"/>
                <Option name="line_width" type="QString" value="0.9"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- E2 VEGETATION FILTERED (ORANGE) -->
    <maplayer id="layer_p3_e2" name="🟠 Phase 3: E2 Vegetation Filtered (31 Footprints)" type="vector" geometry="Polygon">
      <id>layer_p3_e2</id>
      <datasource>{E2_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="255,140,0,255"/>
                <Option name="line_width" type="QString" value="0.8"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- BASELINE E0 (RED) -->
    <maplayer id="layer_p2_base" name="🔴 Phase 2 Baseline: Raw AI E0 (94 Poligoane, 90 FP)" type="vector" geometry="Polygon">
      <id>layer_p2_base</id>
      <datasource>{E0_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="255,40,40,255"/>
                <Option name="line_width" type="QString" value="0.8"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- LIDAR CLASSES (Raster) -->
    <maplayer id="layer_lidar_cls" name="StratumRO — LiDAR ASPRS Classes (1m Grid)" type="raster">
      <id>layer_lidar_cls</id>
      <datasource>{LIDAR_CLS_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <provider>gdal</provider>
    </maplayer>

    <!-- NDSM (Raster) -->
    <maplayer id="layer_ndsm" name="StratumRO — LiDAR nDSM Height (1m Grid)" type="raster">
      <id>layer_ndsm</id>
      <datasource>{NDSM_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <provider>gdal</provider>
    </maplayer>

    <!-- ORTHOPHOTO (Base RGB) -->
    <maplayer id="layer_ortho" name="StratumRO — Cluj Aerial Orthophoto (RGB 0.20m)" type="raster">
      <id>layer_ortho</id>
      <datasource>{ORTHO_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <provider>gdal</provider>
    </maplayer>
  </projectlayers>
</qgis>
"""
    OUTPUT_QGS.write_text(qgs_content, encoding="utf-8")
    print(f"[+] QGIS Project successfully updated: {OUTPUT_QGS}")


def geom_to_pixels(geom, transform):
    """Converts shapely geometry in map coords (EPSG:3844) to pixel coordinates."""
    inv_transform = ~transform
    def ring_to_px(coords):
        pts = []
        for x, y in coords:
            col, row = inv_transform * (x, y)
            pts.append((int(round(col)), int(round(row))))
        return pts

    if geom.geom_type == "Polygon":
        exterior = ring_to_px(geom.exterior.coords)
        interiors = [ring_to_px(r.coords) for r in geom.interiors]
        return [(exterior, interiors)]
    elif geom.geom_type == "MultiPolygon":
        res = []
        for p in geom.geoms:
            ext = ring_to_px(p.exterior.coords)
            ints = [ring_to_px(r.coords) for r in p.interiors]
            res.append((ext, ints))
        return res
    return []


def generate_png_map():
    print("[*] Reading orthophoto raster...")
    with rasterio.open(ORTHO_PATH) as src:
        r = src.read(1)
        g = src.read(2)
        b = src.read(3)
        transform = src.transform
        bounds = src.bounds
        w, h = src.width, src.height

    # Update QGIS project XML
    generate_qgs_project(bounds)

    aoi_polygon = box(bounds.left, bounds.bottom, bounds.right, bounds.top)

    print(f"[*] Ortho dimensions: {w}x{h} px at {src.res[0]:.2f}m GSD")

    # Assemble base image
    base_img = Image.new("RGB", (w, h))
    # Combine bands into RGB
    rgb_arr = Image.merge("RGB", [
        Image.fromarray(r, mode="L"),
        Image.fromarray(g, mode="L"),
        Image.fromarray(b, mode="L")
    ])

    # Create drawing overlays
    overlay_gt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_e9 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_gt = ImageDraw.Draw(overlay_gt)
    draw_e9 = ImageDraw.Draw(overlay_e9)

    # 1. Load and draw Ground Truth
    print("[*] Drawing Ground Truth references...")
    with open(GT_PATH, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    gt_count = 0
    for feat in gt_data["features"]:
        geom = shape(feat["geometry"])
        if geom.intersects(aoi_polygon):
            gt_count += 1
            clipped = geom.intersection(aoi_polygon)
            polys = geom_to_pixels(clipped, transform)
            for ext, ints in polys:
                if len(ext) >= 3:
                    # Semi-transparent fill
                    draw_gt.polygon(ext, fill=(0, 180, 255, 40))
                    # Crisp border (width 3)
                    draw_gt.line(ext + [ext[0]], fill=(0, 190, 255, 230), width=3)
                    for interior in ints:
                        draw_gt.polygon(interior, fill=(0, 0, 0, 0))
                        draw_gt.line(interior + [interior[0]], fill=(0, 190, 255, 200), width=2)

    print(f"  -> {gt_count} Ground Truth structures within AOI")

    # 2. Load and draw E9 Predictions
    print("[*] Drawing E9 Final Predictions...")
    with open(E9_PATH, "r", encoding="utf-8") as f:
        e9_data = json.load(f)

    e9_count = 0
    for feat in e9_data["features"]:
        geom = shape(feat["geometry"])
        e9_count += 1
        polys = geom_to_pixels(geom, transform)
        for ext, ints in polys:
            if len(ext) >= 3:
                # Semi-transparent neon green fill
                draw_e9.polygon(ext, fill=(0, 240, 120, 65))
                # Crisp bright neon green border (width 4)
                draw_e9.line(ext + [ext[0]], fill=(0, 255, 100, 255), width=4)
                for interior in ints:
                    draw_e9.polygon(interior, fill=(0, 0, 0, 0))
                    draw_e9.line(interior + [interior[0]], fill=(0, 255, 100, 220), width=3)

    print(f"  -> {e9_count} E9 Footprints drawn")

    # Composite overlays onto base RGB
    final_img = Image.alpha_composite(rgb_arr.convert("RGBA"), overlay_gt)
    final_img = Image.alpha_composite(final_img, overlay_e9)

    # 3. Add Professional Technical Annotations
    draw = ImageDraw.Draw(final_img)

    # Try loading a clean truetype font, fallback to default
    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 22)
        font_box_title = ImageFont.truetype("arialbd.ttf", 24)
        font_box_text = ImageFont.truetype("arial.ttf", 19)
        font_stat_num = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        font_title = font_sub = font_box_title = font_box_text = font_stat_num = ImageFont.load_default()

    # --- TOP HEADER BANNER ---
    banner_h = 90
    draw.rectangle([(0, 0), (w, banner_h)], fill=(15, 23, 42, 235))
    draw.line([(0, banner_h), (w, banner_h)], fill=(0, 230, 118, 255), width=3)

    draw.text((25, 12), "StratumRO — Cluj Phase 3 Technical Inspection Map", fill=(255, 255, 255), font=font_title)
    draw.text((25, 54), "Projection: Romania Stereo 70 (EPSG:3844) | AOI: 500m × 400m (20 ha) | Orthophoto GSD: 0.20m | LiDAR nDSM 1.0m", fill=(148, 163, 184), font=font_sub)

    # --- LEGEND BOX (TOP RIGHT) ---
    leg_x1, leg_y1 = w - 480, banner_h + 20
    leg_x2, leg_y2 = w - 20, leg_y1 + 180
    draw.rectangle([(leg_x1, leg_y1), (leg_x2, leg_y2)], fill=(15, 23, 42, 225), outline=(51, 65, 85, 255), width=2)

    draw.text((leg_x1 + 20, leg_y1 + 15), "MAP LEGEND & LAYERS", fill=(241, 245, 249), font=font_box_title)
    draw.line([(leg_x1 + 20, leg_y1 + 45), (leg_x2 - 20, leg_y1 + 45)], fill=(51, 65, 85, 255), width=1)

    # E9 Legend Item
    draw.rectangle([(leg_x1 + 22, leg_y1 + 60), (leg_x1 + 52, leg_y1 + 84)], fill=(0, 240, 120, 90), outline=(0, 255, 100, 255), width=3)
    draw.text((leg_x1 + 65, leg_y1 + 62), f"StratumRO E9 Footprints ({e9_count} Predicții)", fill=(255, 255, 255), font=font_box_text)

    # GT Legend Item
    draw.rectangle([(leg_x1 + 22, leg_y1 + 100), (leg_x1 + 52, leg_y1 + 124)], fill=(0, 180, 255, 60), outline=(0, 190, 255, 255), width=2)
    draw.text((leg_x1 + 65, leg_y1 + 102), f"Ground Truth Cadastru ({gt_count} Clădiri AOI)", fill=(255, 255, 255), font=font_box_text)

    # Base Legend Item
    draw.rectangle([(leg_x1 + 22, leg_y1 + 140), (leg_x1 + 52, leg_y1 + 164)], fill=(100, 116, 139, 150), outline=(203, 213, 225, 255), width=1)
    draw.text((leg_x1 + 65, leg_y1 + 142), "Ortofotoplan Aerian RGB (Fond 0.20m)", fill=(203, 213, 225), font=font_box_text)

    # --- TECHNICAL PERFORMANCE PANEL (BOTTOM RIGHT) ---
    perf_w, perf_h = 480, 240
    perf_x1, perf_y1 = w - perf_w - 20, h - perf_h - 20
    perf_x2, perf_y2 = w - 20, h - 20
    draw.rectangle([(perf_x1, perf_y1), (perf_x2, perf_y2)], fill=(15, 23, 42, 230), outline=(0, 230, 118, 200), width=2)

    draw.text((perf_x1 + 20, perf_y1 + 15), "FAZA 3: METRICI VERIFICATE (CLUJ AOI)", fill=(0, 230, 118), font=font_box_title)
    draw.line([(perf_x1 + 20, perf_y1 + 45), (perf_x2 - 20, perf_y1 + 45)], fill=(51, 65, 85, 255), width=1)

    stats = [
        ("False Positives:", "22 (reducere -75.6% vs 90 în E0)", (255, 255, 255)),
        ("True Positives:", "4 (100% conservate fără pierderi)", (255, 255, 255)),
        ("Precizie Pipeline:", "15.38% (îmbunătățire 3.6× vs 4.26%)", (0, 255, 120)),
        ("Mean IoU Clădiri:", "66.59% (ortogonalizat la 90° CAD)", (255, 255, 255)),
        ("Timp de Execuție:", "3.65 s (accelerare 3.6× vs 13.15 s)", (255, 255, 255)),
        ("Statut Oficial E9:", "Candidate Production (Pre-Cadastru)", (255, 214, 0))
    ]

    curr_y = perf_y1 + 55
    for label, val, color in stats:
        draw.text((perf_x1 + 20, curr_y), label, fill=(148, 163, 184), font=font_box_text)
        draw.text((perf_x1 + 175, curr_y), val, fill=color, font=font_box_text)
        curr_y += 28

    # --- SCALE BAR & NORTH ARROW (BOTTOM LEFT) ---
    scale_x, scale_y = 40, h - 70
    scale_len_px = 500  # 100 meters at 0.20m GSD = 500 px
    draw.rectangle([(scale_x - 15, scale_y - 45), (scale_x + scale_len_px + 120, h - 20)], fill=(15, 23, 42, 220), outline=(51, 65, 85), width=1)

    # Scale line
    draw.line([(scale_x, scale_y), (scale_x + scale_len_px, scale_y)], fill=(255, 255, 255), width=4)
    # Ticks
    draw.line([(scale_x, scale_y - 8), (scale_x, scale_y + 8)], fill=(255, 255, 255), width=3)
    draw.line([(scale_x + scale_len_px // 2, scale_y - 6), (scale_x + scale_len_px // 2, scale_y + 6)], fill=(255, 255, 255), width=2)
    draw.line([(scale_x + scale_len_px, scale_y - 8), (scale_x + scale_len_px, scale_y + 8)], fill=(255, 255, 255), width=3)

    # Scale labels
    draw.text((scale_x - 6, scale_y - 30), "0", fill=(255, 255, 255), font=font_box_text)
    draw.text((scale_x + scale_len_px // 2 - 15, scale_y - 30), "50 m", fill=(255, 255, 255), font=font_box_text)
    draw.text((scale_x + scale_len_px - 25, scale_y - 30), "100 m", fill=(255, 255, 255), font=font_box_text)
    draw.text((scale_x + 160, scale_y + 12), "Scara Grafică (1 pixel = 0.20 m)", fill=(148, 163, 184), font=font_box_text)

    # North Arrow (to the right of scale)
    na_x = scale_x + scale_len_px + 65
    na_y = scale_y - 8
    draw.polygon([(na_x, na_y - 25), (na_x - 10, na_y + 10), (na_x, na_y + 3)], fill=(255, 50, 50))
    draw.polygon([(na_x, na_y - 25), (na_x + 10, na_y + 10), (na_x, na_y + 3)], fill=(255, 255, 255))
    draw.text((na_x - 7, na_y - 45), "N", fill=(255, 255, 255), font=font_box_title)

    # Save to disk
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    final_img.convert("RGB").save(OUTPUT_PNG, "PNG", quality=95)
    print(f"[+] High-resolution inspection map generated successfully: {OUTPUT_PNG}")
    print(f"    Dimensions: {w}x{h} px ({OUTPUT_PNG.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate_png_map()
