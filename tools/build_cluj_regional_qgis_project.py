# -*- coding: utf-8 -*-
"""
tools/build_cluj_regional_qgis_project.py - Cluj Regional PUG QGIS Master Project Builder

Builds the complete production QGIS project file (Cluj_Regional_PUG_Oficial.qgs)
and CAD DXF deliverable in Stereo 70 (EPSG:3844) with professional urban planning
symbology and layer hierarchy conforming to Order MDLPA nr. 904/2023.
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import geopandas as gpd
import ezdxf


def build_qgis_project():
    out_dir = ROOT / "workspace" / "reviews" / "cluj_regional_pug"
    gpkg_path = out_dir / "Cluj_Regional_PUG_Master.gpkg"
    qgs_path = out_dir / "Cluj_Regional_PUG_Oficial.qgs"
    cad_path = out_dir / "CAD_Export" / "Cluj_Regional_ZMC_Cadastru_si_PUG.dxf"

    assert gpkg_path.exists(), f"Master GPKG not found: {gpkg_path}"

    print(f"[1/2] Building Master QGIS Project: {qgs_path}")

    # Build QGIS 3.40 XML Project Document
    rel_gpkg = "./Cluj_Regional_PUG_Master.gpkg"

    layers_config = [
        {"id": "lyr_cladiri_usamv", "name": "01. Clădiri Detaliate LOD1 USAMV (Stereo 70)", "layer": "Cladiri_LOD1_USAMV", "geom": "Polygon", "color": "220,50,50", "border": "120,0,0"},
        {"id": "lyr_patrimoniu_ran", "name": "02. Situri Arheologice Clasate RAN (cIMeC)", "layer": "Patrimoniu_RAN_cIMeC", "geom": "Point", "color": "180,80,220", "border": "100,0,150"},
        {"id": "lyr_hidro_anar", "name": "03. Râul Someșul Mic & Afluenți (ANAR)", "layer": "Ape_Somesul_Mic_ANAR", "geom": "LineString", "color": "0,140,255", "border": "0,90,190"},
        {"id": "lyr_transport_cnair", "name": "04. Culoare Transport Rutier A3/DN1 (CNAIR)", "layer": "ReteleTransport_ZMC", "geom": "Polygon", "color": "255,160,0", "border": "180,100,0"},
        {"id": "lyr_zf_existenta", "name": "05. Zonificare Funcțională Existentă (Ord. 904/2023)", "layer": "ZFExistenta", "geom": "Polygon", "color": "255,240,160", "border": "180,170,100"},
        {"id": "lyr_limita_zmc", "name": "06. Limite Administrative ZMC (ANCPI)", "layer": "Limita_ZMC_UAT", "geom": "Polygon", "color": "0,0,0,0", "border": "220,20,20"},
    ]

    qgs_xml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="StratumRO — PUG Cluj Regional (ZMC) Oficial" version="3.40.0-Bratislava">
  <homePath path=""/>
  <title>StratumRO — Plan Urbanistic Cluj Regional (ZMC) conform Ord. 904/2023</title>
  <autotransaction active="0"/>
  <evaluateDefaultValues active="0"/>
  <trust active="0"/>
  <projectCrs>
    <spatialrefsys>
      <wkt>PROJCRS["Pulkovo 1942(58) / Stereo 70",BASEGEOGCRS["Pulkovo 1942(58)",DATUM["Pulkovo 1942(58)",ELLIPSOID["Krassowsky 1940",6378245,298.3,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4179]],CONVERSION["Romania Oblique Stereographic 1970",METHOD["Oblique Stereographic",ID["EPSG",9809]],PARAMETER["Latitude of natural origin",46,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",25,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.99975,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",500000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["northing (X)",north,ORDER[1],LENGTHUNIT["metre",1]],AXIS["easting (Y)",east,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Cadastre, engineering survey, topographic mapping (large and medium scale)."],AREA["Romania - onshore."],BBOX[43.62,20.26,48.27,29.74]],ID["EPSG",3844]]</wkt>
      <proj4>+proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass +towgs84=2.329,-147.042,-92.08,0.309,-0.324,-0.497,5.69 +units=m +no_defs</proj4>
      <srsid>100000</srsid>
      <srid>3844</srid>
      <authid>EPSG:3844</authid>
      <description>Pulkovo 1942(58) / Stereo 70</description>
      <projectionacronym>sterea</projectionacronym>
      <ellipsoidacronym>krass</ellipsoidacronym>
      <geographicflag>false</geographicflag>
    </spatialrefsys>
  </projectCrs>
  <layer-tree-group>
    <customproperties>
      <Option/>
    </customproperties>
"""
    for cfg in layers_config:
        qgs_xml += f'    <layer-tree-layer checked="Qt::Checked" expanded="1" id="{cfg["id"]}" name="{cfg["name"]}" source="{rel_gpkg}|layername={cfg["layer"]}" providerKey="ogr"/>\n'

    qgs_xml += """  </layer-tree-group>
  <projectlayers>
"""

    for cfg in layers_config:
        qgs_xml += f"""    <maplayer autoRefreshTime="0" autoRefreshMode="Disabled" geometry="{cfg['geom']}" hasScaleBasedVisibilityFlag="0" id="{cfg['id']}" maxScale="0" minScale="1e+08" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" styleCategories="AllStyleCategories" type="vector" wktType="{cfg['geom']}">
      <id>{cfg['id']}</id>
      <datasource>{rel_gpkg}|layername={cfg['layer']}</datasource>
      <keywordList><value></value></keywordList>
      <layername>{cfg['name']}</layername>
      <srs>
        <spatialrefsys>
          <authid>EPSG:3844</authid>
          <description>Pulkovo 1942(58) / Stereo 70</description>
          <projectionacronym>sterea</projectionacronym>
          <ellipsoidacronym>krass</ellipsoidacronym>
        </spatialrefsys>
      </srs>
      <provider encoding="UTF-8">ogr</provider>
    </maplayer>
"""

    qgs_xml += """  </projectlayers>
</qgis>
"""

    with open(qgs_path, "w", encoding="utf-8") as f:
        f.write(qgs_xml)
    print(f"  -> QGIS Project saved: {qgs_path}")

    # 2. Build CAD DXF Deliverable
    print(f"\n[2/2] Exporting CAD TopoLT Deliverable: {cad_path}")
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    doc.layers.new("LIM_ZMC_UAT", dxfattribs={"color": 1, "linetype": "Continuous"})
    doc.layers.new("1CC_CLADIRI_USAMV", dxfattribs={"color": 1, "linetype": "Continuous"})
    doc.layers.new("ZF_EXISTENTA", dxfattribs={"color": 2, "linetype": "Continuous"})

    # Export UAT Boundaries
    uats = gpd.read_file(str(gpkg_path), layer="Limita_ZMC_UAT")
    total_uats = 0
    for idx, row in uats.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        polys = geom.geoms if hasattr(geom, "geoms") else [geom]
        for p in polys:
            pts = list(p.exterior.coords)[:-1]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "LIM_ZMC_UAT", "color": 1})
            total_uats += 1

    # Export Buildings
    blds = gpd.read_file(str(gpkg_path), layer="Cladiri_LOD1_USAMV")
    total_blds = 0
    for idx, row in blds.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        polys = geom.geoms if hasattr(geom, "geoms") else [geom]
        for p in polys:
            pts = list(p.exterior.coords)[:-1]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "1CC_CLADIRI_USAMV", "color": 1})
            total_blds += 1

    doc.saveas(str(cad_path))
    print(f"  -> CAD DXF saved: {cad_path} ({total_uats} UAT polylines, {total_blds} building polylines)")

    print("\n===================================================================")
    print("  CLUJ REGIONAL PUG PRODUCTION PACKAGE ASSEMBLED SUCCESSFULLY!")
    print("===================================================================")


if __name__ == "__main__":
    build_qgis_project()
