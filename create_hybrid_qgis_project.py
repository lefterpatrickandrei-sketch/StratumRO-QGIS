# -*- coding: utf-8 -*-
"""
Generates the complete StratumRO v3 QGIS Project (.qgz and .qgs)
incorporating all ANCPI (Ordinul 600/2023) layers:
  - LIMITA_SECTOR_CADASTRAL (Dashed boundary line)
  - CLADIRI_SOL_ANCPI (Ground footprint, red outline)
  - CLADIRI_HIBRID (Roofline, cyan outline)
  - ANEXE_GOSPODARESTI (Outbuildings, orange outline)
  - DR (Roads & parking, asphalt gray)
  - HR (Hydrography / Waterways, blue)
  - VN (Vineyards, olive green)
  - CIMITIR (Cemetery TDS/CC, slate purple)
  - A (Arable agricultural parcels, warm beige)
  - UNCLASSIFIED (100% planar partition, soft yellow)
  - ARBORI (Filtered trees, green markers)
  - STALPI_TURNURI (Poles & towers, magenta diamonds)
  - nDSM (Height raster, unchecked)
  - Ortofotoplan Aerian Cluj USAMV RGB (Base raster, checked)
"""

import os
import sys
import zipfile
import pyogrio

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

gpkg_path = os.path.abspath(r"workspace\output\cladiri_stereo70.gpkg")
ndsm_path = os.path.abspath(r"workspace\output\ndsm_stereo70.tif")
orto_vrt = os.path.abspath(r"workspace\output\ortofoto_cluj_usamv_rgb.vrt")
qgs_path = os.path.abspath(r"workspace\output\StratumRO_Rezultate.qgs")
qgz_path = os.path.abspath(r"workspace\output\StratumRO_Rezultate.qgz")

def get_count(layer):
    if not os.path.exists(gpkg_path):
        return 0
    try:
        return len(pyogrio.read_dataframe(gpkg_path, layer=layer))
    except Exception:
        return 0

count_sector = get_count("LIMITA_SECTOR_CADASTRAL")
count_sol = get_count("CLADIRI_SOL_ANCPI")
count_bldg = get_count("CLADIRI_HIBRID")
count_anexe = get_count("ANEXE_GOSPODARESTI")
count_dr = get_count("DR")
count_hr = get_count("HR")
count_vn = get_count("VN")
count_cimitir = get_count("CIMITIR")
count_a = get_count("A")
count_unclass = get_count("UNCLASSIFIED")
count_trees = get_count("ARBORI")
count_poles = get_count("STALPI_TURNURI")

qgs_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="StratumRO — Cadastru Sistematic &amp; Cartografiere ANCPI v3" version="3.40.0">
  <homePath path=""/>
  <title>StratumRO — Cadastru General &amp; Partiție Planară 100% (Cluj USAMV)</title>
  <autotransaction active="0"/>
  <evaluateDefaultValues active="0"/>
  <trust active="0"/>
  <projectCrs>
    <spatialrefsys nativeFormat="Wkt">
      <wkt>PROJCRS["Pulkovo 1942(58) / Stereo70",BASEGEOGCRS["Pulkovo 1942",DATUM["Pulkovo 1942",ELLIPSOID["Krassowsky 1940",6378245,298.3,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4284]],CONVERSION["Stereo70",METHOD["Oblique Stereographic",ID["EPSG",9809]],PARAMETER["Latitude of natural origin",46,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",25,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.99975,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",500000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["northing (X)",north,ORDER[1],LENGTHUNIT["metre",1]],AXIS["easting (Y)",east,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Cadastre, engineering survey, topographic mapping (large and medium scale)."],AREA["Romania - onshore."],BBOX[43.62,20.26,48.27,29.74]],ID["EPSG",3844]]</wkt>
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
    <layer-tree-layer id="layer_limita" name="StratumRO — Limită Sector Cadastral (Cadru Lucru)" source="{gpkg_path}|layername=LIMITA_SECTOR_CADASTRAL" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_stalpi" name="StratumRO — Stâlpi &amp; Turnuri ({count_poles} Puncte)" source="{gpkg_path}|layername=STALPI_TURNURI" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_arbori" name="StratumRO — Arbori Solitari Validați ({count_trees:,} Puncte)" source="{gpkg_path}|layername=ARBORI" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_cladiri_sol" name="StratumRO — Clădiri Sol ANCPI (-40cm) ({count_sol} Clădiri)" source="{gpkg_path}|layername=CLADIRI_SOL_ANCPI" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_cladiri_hibrid" name="StratumRO — Acoperișuri Clădiri 90° ({count_bldg} Clădiri)" source="{gpkg_path}|layername=CLADIRI_HIBRID" providerKey="ogr" expanded="1" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_anexe" name="StratumRO — Anexe Gospodărești ({count_anexe} Clădiri)" source="{gpkg_path}|layername=ANEXE_GOSPODARESTI" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_dr" name="StratumRO — DR: Căi Comunicații Rutiere &amp; Parcări ({count_dr} Parcele)" source="{gpkg_path}|layername=DR" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_hr" name="StratumRO — HR: Hidrografie &amp; Cursuri Apă ({count_hr} Parcele)" source="{gpkg_path}|layername=HR" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_vn" name="StratumRO — VN: Vii &amp; Plantații Didactice ({count_vn} Parcele)" source="{gpkg_path}|layername=VN" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_cimitir" name="StratumRO — CIMITIR: Destinație Specială CC ({count_cimitir} Parcele)" source="{gpkg_path}|layername=CIMITIR" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_a" name="StratumRO — A: Terenuri Arabile ({count_a} Parcele)" source="{gpkg_path}|layername=A" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_unclassified" name="StratumRO — UNCLASSIFIED: Teren Rezidual / Curți ({count_unclass} Parcele)" source="{gpkg_path}|layername=UNCLASSIFIED" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="layer_ndsm" name="StratumRO — Model Înălțimi nDSM (1m)" source="{ndsm_path}" providerKey="gdal" expanded="1" checked="Qt::Unchecked"/>
    <layer-tree-layer id="layer_ortofoto" name="StratumRO — Ortofotoplan Aerian Cluj USAMV (RGB)" source="{orto_vrt}" providerKey="gdal" expanded="1" checked="Qt::Checked"/>
  </layer-tree-group>
  <projectlayers>

    <!-- LIMITA SECTOR CADASTRAL -->
    <maplayer id="layer_limita" name="StratumRO — Limită Sector Cadastral (Cadru Lucru)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_limita</id>
      <datasource>{gpkg_path}|layername=LIMITA_SECTOR_CADASTRAL</datasource>
      <layername>StratumRO — Limită Sector Cadastral (Cadru Lucru)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1">
            <layer class="SimpleLine" pass="0" locked="0">
              <Option type="Map">
                <Option name="line_color" type="QString" value="0,0,0,255"/>
                <Option name="line_width" type="QString" value="1.2"/>
                <Option name="line_style" type="QString" value="dash"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- CLADIRI SOL ANCPI -->
    <maplayer id="layer_cladiri_sol" name="StratumRO — Clădiri Sol ANCPI (-40cm) ({count_sol} Clădiri)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_cladiri_sol</id>
      <datasource>{gpkg_path}|layername=CLADIRI_SOL_ANCPI</datasource>
      <layername>StratumRO — Clădiri Sol ANCPI (-40cm) ({count_sol} Clădiri)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.95" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="255,40,40,80"/>
                <Option name="outline_color" type="QString" value="230,0,0,255"/>
                <Option name="outline_width" type="QString" value="1.0"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- CLADIRI HIBRID -->
    <maplayer id="layer_cladiri_hibrid" name="StratumRO — Acoperișuri Clădiri 90° ({count_bldg} Clădiri)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_cladiri_hibrid</id>
      <datasource>{gpkg_path}|layername=CLADIRI_HIBRID</datasource>
      <layername>StratumRO — Acoperișuri Clădiri 90° ({count_bldg} Clădiri)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.8" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="0,255,255,40"/>
                <Option name="outline_color" type="QString" value="0,220,255,255"/>
                <Option name="outline_width" type="QString" value="0.8"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- DR: DRUMURI -->
    <maplayer id="layer_dr" name="StratumRO — DR: Căi Comunicații Rutiere &amp; Parcări ({count_dr} Parcele)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_dr</id>
      <datasource>{gpkg_path}|layername=DR</datasource>
      <layername>StratumRO — DR: Căi Comunicații Rutiere &amp; Parcări ({count_dr} Parcele)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.6" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="130,130,130,140"/>
                <Option name="outline_color" type="QString" value="80,80,80,255"/>
                <Option name="outline_width" type="QString" value="0.6"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- HR: HIDROGRAFIE -->
    <maplayer id="layer_hr" name="StratumRO — HR: Hidrografie &amp; Cursuri Apă ({count_hr} Parcele)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_hr</id>
      <datasource>{gpkg_path}|layername=HR</datasource>
      <layername>StratumRO — HR: Hidrografie &amp; Cursuri Apă ({count_hr} Parcele)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.75" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="65,150,240,160"/>
                <Option name="outline_color" type="QString" value="30,100,200,255"/>
                <Option name="outline_width" type="QString" value="0.7"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- VN: VII -->
    <maplayer id="layer_vn" name="StratumRO — VN: Vii &amp; Plantații Didactice ({count_vn} Parcele)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_vn</id>
      <datasource>{gpkg_path}|layername=VN</datasource>
      <layername>StratumRO — VN: Vii &amp; Plantații Didactice ({count_vn} Parcele)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.6" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="100,160,50,110"/>
                <Option name="outline_color" type="QString" value="60,110,30,255"/>
                <Option name="outline_width" type="QString" value="0.6"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- CIMITIR -->
    <maplayer id="layer_cimitir" name="StratumRO — CIMITIR: Destinație Specială CC ({count_cimitir} Parcele)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_cimitir</id>
      <datasource>{gpkg_path}|layername=CIMITIR</datasource>
      <layername>StratumRO — CIMITIR: Destinație Specială CC ({count_cimitir} Parcele)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.55" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="160,130,170,120"/>
                <Option name="outline_color" type="QString" value="110,80,120,255"/>
                <Option name="outline_width" type="QString" value="0.7"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- A: ARABIL -->
    <maplayer id="layer_a" name="StratumRO — A: Terenuri Arabile ({count_a} Parcele)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_a</id>
      <datasource>{gpkg_path}|layername=A</datasource>
      <layername>StratumRO — A: Terenuri Arabile ({count_a} Parcele)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.5" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="235,215,140,110"/>
                <Option name="outline_color" type="QString" value="180,150,70,255"/>
                <Option name="outline_width" type="QString" value="0.6"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- UNCLASSIFIED: PARTITIE PLANARA 100% -->
    <maplayer id="layer_unclassified" name="StratumRO — UNCLASSIFIED: Teren Rezidual / Curți ({count_unclass} Parcele)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_unclassified</id>
      <datasource>{gpkg_path}|layername=UNCLASSIFIED</datasource>
      <layername>StratumRO — UNCLASSIFIED: Teren Rezidual / Curți ({count_unclass} Parcele)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.35" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="245,240,215,90"/>
                <Option name="outline_color" type="QString" value="200,190,160,180"/>
                <Option name="outline_width" type="QString" value="0.4"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- ARBORI (Puncte Verzi) -->
    <maplayer id="layer_arbori" name="StratumRO — Arbori Solitari Validați ({count_trees:,} Puncte)" type="vector" geometry="Point" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_arbori</id>
      <datasource>{gpkg_path}|layername=ARBORI</datasource>
      <layername>StratumRO — Arbori Solitari Validați ({count_trees:,} Puncte)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="marker" name="0" alpha="1" clip_to_extent="1">
            <layer class="SimpleMarker" pass="0" locked="0">
              <Option type="Map">
                <Option name="name" type="QString" value="circle"/>
                <Option name="size" type="QString" value="3.0"/>
                <Option name="color" type="QString" value="34,180,34,255"/>
                <Option name="outline_color" type="QString" value="0,80,0,255"/>
                <Option name="outline_width" type="QString" value="0.5"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- STALPI TURNURI -->
    <maplayer id="layer_stalpi" name="StratumRO — Stâlpi &amp; Turnuri ({count_poles} Puncte)" type="vector" geometry="Point" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_stalpi</id>
      <datasource>{gpkg_path}|layername=STALPI_TURNURI</datasource>
      <layername>StratumRO — Stâlpi &amp; Turnuri ({count_poles} Puncte)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="marker" name="0" alpha="1" clip_to_extent="1">
            <layer class="SimpleMarker" pass="0" locked="0">
              <Option type="Map">
                <Option name="name" type="QString" value="diamond"/>
                <Option name="size" type="QString" value="4.5"/>
                <Option name="color" type="QString" value="0,230,255,255"/>
                <Option name="outline_color" type="QString" value="0,0,139,255"/>
                <Option name="outline_width" type="QString" value="0.8"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- ANEXE GOSPODARESTI -->
    <maplayer id="layer_anexe" name="StratumRO — Anexe Gospodărești ({count_anexe} Clădiri)" type="vector" geometry="Polygon" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" readOnly="0">
      <id>layer_anexe</id>
      <datasource>{gpkg_path}|layername=ANEXE_GOSPODARESTI</datasource>
      <layername>StratumRO — Anexe Gospodărești ({count_anexe} Clădiri)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.8" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="255,180,0,50"/>
                <Option name="outline_color" type="QString" value="255,140,0,255"/>
                <Option name="outline_width" type="QString" value="0.7"/>
                <Option name="style" type="QString" value="solid"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- nDSM (Unchecked) -->
    <maplayer id="layer_ndsm" name="StratumRO — Model Înălțimi nDSM (1m)" type="raster" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" autoRefreshEnabled="0">
      <id>layer_ndsm</id>
      <datasource>{ndsm_path}</datasource>
      <layername>StratumRO — Model Înălțimi nDSM (1m)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <pipe-data-defined-properties><Option type="Map"><Option name="name" type="QString" value=""/><Option name="properties"/><Option name="type" type="QString" value="collection"/></Option></pipe-data-defined-properties>
      <pipe>
        <provider><operation>gdal</operation></provider>
        <rasterrenderer type="singlebandgray" opacity="0.7" alphaBand="-1" grayBand="1" gradient="BlackToWhite">
          <rasterTransparency/>
          <contrastEnhancement>
            <minValue>0.0</minValue>
            <maxValue>25.0</maxValue>
            <algorithm>StretchToMinimumMaximum</algorithm>
          </contrastEnhancement>
        </rasterrenderer>
        <brightnesscontrast brightness="0" contrast="0"/>
        <huesaturation colorizeOn="0" colorizeStrength="100"/>
        <resamplingStage>resamplingFilter</resamplingStage>
      </pipe>
      <blendMode>0</blendMode>
    </maplayer>

    <!-- ORTOFOTOPLAN RGB (Checked at bottom) -->
    <maplayer id="layer_ortofoto" name="StratumRO — Ortofotoplan Aerian Cluj USAMV (RGB)" type="raster" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" autoRefreshEnabled="0">
      <id>layer_ortofoto</id>
      <datasource>{orto_vrt}</datasource>
      <layername>StratumRO — Ortofotoplan Aerian Cluj USAMV (RGB)</layername>
      <srs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:3844</authid></spatialrefsys></srs>
      <pipe>
        <provider><operation>gdal</operation></provider>
        <rasterrenderer type="multibandcolor" opacity="1.0" redBand="1" greenBand="2" blueBand="3">
          <rasterTransparency/>
        </rasterrenderer>
      </pipe>
      <blendMode>0</blendMode>
    </maplayer>

  </projectlayers>
</qgis>
"""

with open(qgs_path, "w", encoding="utf-8") as f:
    f.write(qgs_content)
print(f"[OK] Fișier Proiect XML generat: {qgs_path}")

with zipfile.ZipFile(qgz_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    z.write(qgs_path, arcname="StratumRO_Rezultate.qgs")
print(f"[OK] Pachet QGIS Zipped (.qgz) generat cu succes: {qgz_path}")
