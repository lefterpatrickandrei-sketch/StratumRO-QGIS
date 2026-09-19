# -*- coding: utf-8 -*-
"""
Generate QGIS 3.40 project for Phase 3 visual comparison:
BEFORE (Phase 2 Baseline: Red) vs AFTER (Phase 3 Integrated: Green) vs Ground Truth (Cyan)
"""

import os

PROJECT_ROOT = r"C:\Users\lefpa\Downloads\QGIS-AI"
QGS_PATH = os.path.join(PROJECT_ROOT, "workspace", "phase3", "StratumRO_Cluj_Phase3_Spectator.qgs")

ORTHO_PATH = os.path.join(PROJECT_ROOT, "workspace", "e2e", "04_orthophoto", "active_ortho_crop.tif")
NDSM_PATH = os.path.join(PROJECT_ROOT, "workspace", "derived", "cluj_ndsm_1m.tif")
REF_PATH = os.path.join(PROJECT_ROOT, "data", "derived_reference", "cluj_combined_unique_150.geojson")
P2_BASE_PATH = os.path.join(PROJECT_ROOT, "workspace", "phase3", "predictions", "EXP_000_baseline_raw.geojson")
P3_FINAL_PATH = os.path.join(PROJECT_ROOT, "workspace", "phase3", "predictions", "EXP_009_integrated_pipeline_reg.geojson")
P3_CAND_PATH = os.path.join(PROJECT_ROOT, "workspace", "phase3", "predictions", "EXP_001_candidate_gen_raw.geojson")

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
  <layer-tree-group>
    <customproperties><Option/></customproperties>
    <layer-tree-layer id="layer_p3_final" name="🟢 Phase 3: Integrated Pipeline E9 (26 Footprints)" source="{P3_FINAL_PATH}" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_ref_gt" name="🔵 Ground Truth: Cluj Reference (65 Clădiri)" source="{REF_PATH}" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_p2_base" name="🔴 Phase 2 Baseline: Raw AI E0 (94 Poligoane, 90 FP)" source="{P2_BASE_PATH}" providerKey="ogr" expanded="1" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_p3_cand" name="🟡 Phase 3: Candidate Blobs E1 (75 Poligoane)" source="{P3_CAND_PATH}" providerKey="ogr" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_ndsm" name="StratumRO — LiDAR nDSM (1m Grid)" source="{NDSM_PATH}" providerKey="gdal" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_ortho" name="StratumRO — Ortofotoplan Aerian Cluj (RGB 0.2m)" source="{ORTHO_PATH}" providerKey="gdal" expanded="1" checked="Qt::Checked"/>
  </layer-tree-group>
  <projectlayers>

    <!-- PHASE 3 FINAL PREDICTIONS (GREEN) -->
    <maplayer id="layer_p3_final" name="🟢 Phase 3: Integrated Pipeline E9 (26 Footprints)" type="vector" geometry="Polygon">
      <id>layer_p3_final</id>
      <datasource>{P3_FINAL_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="0,220,50,255"/>
                <Option name="line_width" type="QString" value="1.0"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- GROUND TRUTH REFERENCE (CYAN) -->
    <maplayer id="layer_ref_gt" name="🔵 Ground Truth: Cluj Reference (65 Clădiri)" type="vector" geometry="Polygon">
      <id>layer_ref_gt</id>
      <datasource>{REF_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="0,180,255,255"/>
                <Option name="line_width" type="QString" value="0.9"/>
                <Option name="line_style" type="QString" value="dash"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- PHASE 2 BASELINE (RED) -->
    <maplayer id="layer_p2_base" name="🔴 Phase 2 Baseline: Raw AI E0 (94 Poligoane, 90 FP)" type="vector" geometry="Polygon">
      <id>layer_p2_base</id>
      <datasource>{P2_BASE_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="255,50,50,255"/>
                <Option name="line_width" type="QString" value="0.7"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- PHASE 3 CANDIDATES (YELLOW) -->
    <maplayer id="layer_p3_cand" name="🟡 Phase 3: Candidate Blobs E1 (75 Poligoane)" type="vector" geometry="Polygon">
      <id>layer_p3_cand</id>
      <datasource>{P3_CAND_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol">
        <symbols>
          <symbol type="fill" name="0" alpha="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="255,220,0,255"/>
                <Option name="line_width" type="QString" value="0.5"/>
                <Option name="line_style" type="QString" value="dot"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- NDSM -->
    <maplayer id="layer_ndsm" name="StratumRO — LiDAR nDSM (1m Grid)" type="raster">
      <id>layer_ndsm</id>
      <datasource>{NDSM_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <provider>gdal</provider>
    </maplayer>

    <!-- ORTHOPHOTO -->
    <maplayer id="layer_ortho" name="StratumRO — Ortofotoplan Aerian Cluj (RGB 0.2m)" type="raster">
      <id>layer_ortho</id>
      <datasource>{ORTHO_PATH}</datasource>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <provider>gdal</provider>
    </maplayer>

  </projectlayers>
</qgis>
"""

with open(QGS_PATH, "w", encoding="utf-8") as f:
    f.write(qgs_content)

print(f"[+] Saved Phase 3 QGIS Spectator Project: {QGS_PATH}")
