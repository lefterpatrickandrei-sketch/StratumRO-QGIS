import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cad_gpkg = os.path.abspath(r"workspace\output\cadastru_ancpi.gpkg")
pug_gpkg = os.path.abspath(r"workspace\output\urbanism_pug.gpkg")
ndsm_path = os.path.abspath(r"workspace\output\ndsm_stereo70.tif")

# =================================================================
# 1. PROIECT CADASTRU ANCPI
# =================================================================
qgs_cad_path = os.path.abspath(r"workspace\output\StratumRO_Cadastru_ANCPI.qgs")

qgs_cad_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="StratumRO — Cadastru Oficial ANCPI (Stereo 70)" version="3.40.0">
  <homePath path=""/>
  <title>StratumRO — Livrabil Cadastru ANCPI (Legea 7/1996)</title>
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
    <layer-tree-layer id="cad_stalpi" name="ANCPI — Stâlpi &amp; Rețele Utilități (8 Puncte)" source="{cad_gpkg}|layername=STALPI_UTILITATI" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="cad_arbori" name="ANCPI — Arbori Aliniament (Fără Suprapunere Clădiri - 3,927 Puncte)" source="{cad_gpkg}|layername=ARBORI_ALINIAMENT" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="cad_anexe" name="ANCPI — Corpuri C2: Anexe Gospodărești (6 Clădiri)" source="{cad_gpkg}|layername=ANEXE" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="cad_constructii" name="ANCPI — Corpuri C1: Construcții Principale Ortogonalizate 90° (377 Clădiri)" source="{cad_gpkg}|layername=CONSTRUCTII" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="cad_ndsm" name="Cadastru — Model Înălțimi nDSM (1m)" source="{ndsm_path}" providerKey="gdal" expanded="1" checked="Qt::Checked"/>
    <custom-order enabled="0">
      <item>cad_stalpi</item>
      <item>cad_arbori</item>
      <item>cad_anexe</item>
      <item>cad_constructii</item>
      <item>cad_ndsm</item>
    </custom-order>
  </layer-tree-group>
  <projectlayers>
    <!-- STALPI -->
    <maplayer id="cad_stalpi" name="ANCPI — Stâlpi &amp; Rețele Utilități (8 Puncte)" type="vector" geometry="Point">
      <id>cad_stalpi</id>
      <datasource>{cad_gpkg}|layername=STALPI_UTILITATI</datasource>
      <layername>ANCPI — Stâlpi &amp; Rețele Utilități (8 Puncte)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="marker" name="0" alpha="1" clip_to_extent="1">
            <layer class="SimpleMarker" pass="0" locked="0">
              <Option type="Map">
                <Option name="name" type="QString" value="diamond"/>
                <Option name="size" type="QString" value="4.0"/>
                <Option name="color" type="QString" value="0,230,255,255"/>
                <Option name="outline_color" type="QString" value="0,0,139,255"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- ARBORI ALINIAMENT -->
    <maplayer id="cad_arbori" name="ANCPI — Arbori Aliniament (Fără Suprapunere Clădiri - 3,927 Puncte)" type="vector" geometry="Point">
      <id>cad_arbori</id>
      <datasource>{cad_gpkg}|layername=ARBORI_ALINIAMENT</datasource>
      <layername>ANCPI — Arbori Aliniament (Fără Suprapunere Clădiri - 3,927 Puncte)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="marker" name="0" alpha="0.7" clip_to_extent="1">
            <layer class="SimpleMarker" pass="0" locked="0">
              <Option type="Map">
                <Option name="name" type="QString" value="circle"/>
                <Option name="size" type="QString" value="1.8"/>
                <Option name="color" type="QString" value="34,197,94,180"/>
                <Option name="outline_color" type="QString" value="21,128,61,255"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- ANEXE C2 -->
    <maplayer id="cad_anexe" name="ANCPI — Corpuri C2: Anexe Gospodărești (6 Clădiri)" type="vector" geometry="Polygon">
      <id>cad_anexe</id>
      <datasource>{cad_gpkg}|layername=ANEXE</datasource>
      <layername>ANCPI — Corpuri C2: Anexe Gospodărești (6 Clădiri)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.85" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="250,204,21,140"/>
                <Option name="outline_color" type="QString" value="202,138,4,255"/>
                <Option name="outline_width" type="QString" value="0.7"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- CONSTRUCTII C1 -->
    <maplayer id="cad_constructii" name="ANCPI — Corpuri C1: Construcții Principale Ortogonalizate 90° (377 Clădiri)" type="vector" geometry="Polygon">
      <id>cad_constructii</id>
      <datasource>{cad_gpkg}|layername=CONSTRUCTII</datasource>
      <layername>ANCPI — Corpuri C1: Construcții Principale Ortogonalizate 90° (377 Clădiri)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.9" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="239,68,68,140"/>
                <Option name="outline_color" type="QString" value="185,28,28,255"/>
                <Option name="outline_width" type="QString" value="0.9"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- nDSM -->
    <maplayer id="cad_ndsm" name="Cadastru — Model Înălțimi nDSM (1m)" type="raster">
      <id>cad_ndsm</id>
      <datasource>{ndsm_path}</datasource>
      <layername>Cadastru — Model Înălțimi nDSM (1m)</layername>
      <pipe>
        <rasterrenderer type="singlebandpseudocolor" opacity="0.6" band="1">
          <rastershader>
            <colorrampshader colorRampType="INTERPOLATED">
              <item label="0.0 m" value="0" color="44,123,182,0"/>
              <item label="3.0 m" value="3" color="171,217,233,180"/>
              <item label="8.0 m" value="8" color="255,255,191,210"/>
              <item label="20.0 m" value="20" color="215,25,28,255"/>
            </colorrampshader>
          </rastershader>
        </rasterrenderer>
      </pipe>
    </maplayer>
  </projectlayers>
</qgis>"""

with open(qgs_cad_path, "w", encoding="utf-8") as f:
    f.write(qgs_cad_content)

print(f"[OK] Proiect Cadastru ANCPI salvat la: {qgs_cad_path}")

# =================================================================
# 2. PROIECT URBANISM & PUG
# =================================================================
qgs_pug_path = os.path.abspath(r"workspace\output\StratumRO_Urbanism_PUG.qgs")

qgs_pug_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="StratumRO — Urbanism &amp; PUG (Legea 350/2001 &amp; Legea 24/2007)" version="3.40.0">
  <homePath path=""/>
  <title>StratumRO — Urbanism, PUG &amp; Registru Spatii Verzi</title>
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
    <layer-tree-layer id="pug_retele" name="PUG — Rețele &amp; Echipamente Utilități (8 Puncte)" source="{pug_gpkg}|layername=RETELE_UTILITATI" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="pug_arbori" name="PUG — Registru Spații Verzi: Arbori pe Sol Liber (3,927 Puncte)" source="{pug_gpkg}|layername=REGISTRU_ARBORI" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="pug_coronamente" name="PUG — Fond Vegetal: Acoperire Coronamente (21.2 ha)" source="{pug_gpkg}|layername=CORONAMENTE_FOND_VEGETAL" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="pug_anexe" name="PUG — Anexe Gospodărești Volumetrice (6 Clădiri)" source="{pug_gpkg}|layername=ANEXE_URBANISM" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="pug_cladiri" name="PUG — Fond Construit LOD1: Clădiri Volumetrice 3D (377 Clădiri)" source="{pug_gpkg}|layername=CLADIRI_VOLUMETRICE_LOD1" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="pug_utr" name="PUG — Zonificare UTR: Indicatori POT &amp; CUT (49 Celule)" source="{pug_gpkg}|layername=ZONIFICARE_POT_CUT" providerKey="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="pug_ndsm" name="PUG — Model Înălțimi nDSM (1m)" source="{ndsm_path}" providerKey="gdal" expanded="1" checked="Qt::Checked"/>
    <custom-order enabled="0">
      <item>pug_retele</item>
      <item>pug_arbori</item>
      <item>pug_coronamente</item>
      <item>pug_anexe</item>
      <item>pug_cladiri</item>
      <item>pug_utr</item>
      <item>pug_ndsm</item>
    </custom-order>
  </layer-tree-group>
  <projectlayers>
    <!-- 1. RETELE UTILITATI -->
    <maplayer id="pug_retele" name="PUG — Rețele &amp; Echipamente Utilități (8 Puncte)" type="vector" geometry="Point">
      <id>pug_retele</id>
      <datasource>{pug_gpkg}|layername=RETELE_UTILITATI</datasource>
      <layername>PUG — Rețele &amp; Echipamente Utilități (8 Puncte)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="marker" name="0" alpha="1" clip_to_extent="1">
            <layer class="SimpleMarker" pass="0" locked="0">
              <Option type="Map">
                <Option name="name" type="QString" value="diamond"/>
                <Option name="size" type="QString" value="4.0"/>
                <Option name="color" type="QString" value="6,182,212,255"/>
                <Option name="outline_color" type="QString" value="14,116,144,255"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- 2. REGISTRU ARBORI -->
    <maplayer id="pug_arbori" name="PUG — Registru Spații Verzi: Arbori pe Sol Liber (3,927 Puncte)" type="vector" geometry="Point">
      <id>pug_arbori</id>
      <datasource>{pug_gpkg}|layername=REGISTRU_ARBORI</datasource>
      <layername>PUG — Registru Spații Verzi: Arbori pe Sol Liber (3,927 Puncte)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="marker" name="0" alpha="1" clip_to_extent="1">
            <layer class="SimpleMarker" pass="0" locked="0">
              <Option type="Map">
                <Option name="name" type="QString" value="circle"/>
                <Option name="size" type="QString" value="2.2"/>
                <Option name="color" type="QString" value="34,197,94,255"/>
                <Option name="outline_color" type="QString" value="20,83,45,255"/>
                <Option name="outline_width" type="QString" value="0.4"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- 3. CORONAMENTE -->
    <maplayer id="pug_coronamente" name="PUG — Fond Vegetal: Acoperire Coronamente (21.2 ha)" type="vector" geometry="Polygon">
      <id>pug_coronamente</id>
      <datasource>{pug_gpkg}|layername=CORONAMENTE_FOND_VEGETAL</datasource>
      <layername>PUG — Fond Vegetal: Acoperire Coronamente (21.2 ha)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.4" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="74,222,128,120"/>
                <Option name="outline_color" type="QString" value="34,197,94,255"/>
                <Option name="outline_width" type="QString" value="0.5"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- 4. ANEXE URBANISM -->
    <maplayer id="pug_anexe" name="PUG — Anexe Gospodărești Volumetrice (6 Clădiri)" type="vector" geometry="Polygon">
      <id>pug_anexe</id>
      <datasource>{pug_gpkg}|layername=ANEXE_URBANISM</datasource>
      <layername>PUG — Anexe Gospodărești Volumetrice (6 Clădiri)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.85" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="250,204,21,160"/>
                <Option name="outline_color" type="QString" value="202,138,4,255"/>
                <Option name="outline_width" type="QString" value="0.7"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- 5. CLADIRI LOD1 -->
    <maplayer id="pug_cladiri" name="PUG — Fond Construit LOD1: Clădiri Volumetrice 3D (377 Clădiri)" type="vector" geometry="Polygon">
      <id>pug_cladiri</id>
      <datasource>{pug_gpkg}|layername=CLADIRI_VOLUMETRICE_LOD1</datasource>
      <layername>PUG — Fond Construit LOD1: Clădiri Volumetrice 3D (377 Clădiri)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.85" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="249,115,22,180"/>
                <Option name="outline_color" type="QString" value="194,65,12,255"/>
                <Option name="outline_width" type="QString" value="0.8"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- 6. ZONIFICARE POT / CUT -->
    <maplayer id="pug_utr" name="PUG — Zonificare UTR: Indicatori POT &amp; CUT (49 Celule)" type="vector" geometry="Polygon">
      <id>pug_utr</id>
      <datasource>{pug_gpkg}|layername=ZONIFICARE_POT_CUT</datasource>
      <layername>PUG — Zonificare UTR: Indicatori POT &amp; CUT (49 Celule)</layername>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.25" clip_to_extent="1">
            <layer class="SimpleFill" pass="0" locked="0">
              <Option type="Map">
                <Option name="color" type="QString" value="99,102,241,40"/>
                <Option name="outline_color" type="QString" value="79,70,229,200"/>
                <Option name="outline_width" type="QString" value="1.0"/>
                <Option name="line_style" type="QString" value="dash"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>

    <!-- 7. nDSM -->
    <maplayer id="pug_ndsm" name="PUG — Model Înălțimi nDSM (1m)" type="raster">
      <id>pug_ndsm</id>
      <datasource>{ndsm_path}</datasource>
      <layername>PUG — Model Înălțimi nDSM (1m)</layername>
      <pipe>
        <rasterrenderer type="singlebandpseudocolor" opacity="0.55" band="1">
          <rastershader>
            <colorrampshader colorRampType="INTERPOLATED">
              <item label="0.0 m (Teren)" value="0" color="44,123,182,0"/>
              <item label="3.0 m (Vegetație joasă)" value="3" color="171,217,233,160"/>
              <item label="8.0 m (Pomi / Anexe)" value="8" color="255,255,191,200"/>
              <item label="15.0 m (Clădiri P+2 / P+3)" value="15" color="253,174,97,230"/>
              <item label="25.0+ m (Arbori înalți / Blocuri)" value="25" color="215,25,28,255"/>
            </colorrampshader>
          </rastershader>
        </rasterrenderer>
      </pipe>
    </maplayer>
  </projectlayers>
</qgis>"""

with open(qgs_pug_path, "w", encoding="utf-8") as f:
    f.write(qgs_pug_content)

print(f"[OK] Proiect Urbanism & PUG salvat la: {qgs_pug_path}")
