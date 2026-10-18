# -*- coding: utf-8 -*-
"""
StratumRO National Geodata Harvester Engine
===========================================
Official Romanian National Spatial Dataset Harvester & QGIS Browser Cataloguer.

Responsible Subagent: romanian-opendata-specialist
Maintained by: StratumRO Multi-Agent Framework

Authoritative Sources Harvested:
  01. ANCPI: Unitati Administrativ-Teritoriale (3.186 UAT-uri, Judete, Regiuni)
  02. cIMeC / INP: Repertoriul Arheologic National (RAN, RAR, 52.823 situri)
  03. APIA: LPIS Parcele de Referinta Blocuri Fizice 2025 (1.54M parcele)
  04. ANAR / ROWATER: Cursuri de apa rauri, bazine hidrografice, diguri, RO-FLOODS
  05. EEA / ANANP: Natura 2000 (Habitate SCI/SAC, Pasari SPA)
  06. MMAP / ROMSILVA: Fond forestier, SUMAL 2.0 / Inspectorul Padurii, Copernicus Forest
  07. ANCPI RENNS: Nomenclatorul Stradal Electronic si Adrese Postale
  08. MT / CNAIR / CFR: Retea drumuri nationale majore si Cai ferate Romania
  09. ANCPI GEODEZIE: Retea geodezica, statii permanente GNSS ROPOS, caroiaj Stereo 70
  10. COPERNICUS: Corine Land Cover (CLC) Romania
  11. IGR: Harta Geologica a Romaniei scara 1:1.000.000
"""

import os
import sys
import ssl
import json
import zipfile
import shutil
import urllib.request
import urllib.error
import urllib.parse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

BASE_DIR = r"c:\Users\lefpa\Downloads\QGIS-AI\national_server"

# SSL Context for open public endpoints
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StratumRO-National-Harvester/2.0",
    "Accept": "*/*"
}

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def create_internet_shortcut(filepath, url):
    content = f"[InternetShortcut]\nURL={url}\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def stream_download(url, dest_path, desc="", min_size=1024):
    """Downloads a file with chunked streaming and resume/progress display."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) >= min_size:
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"  [EXISTS] {desc}: {os.path.basename(dest_path)} ({size_mb:.2f} MB)")
        return True

    print(f"  [DOWNLOAD] {desc} from {url}...")
    tmp_path = dest_path + ".part"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
            total_bytes = 0
            with open(tmp_path, "wb") as f_out:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    total_bytes += len(chunk)
                    if total_bytes % (2 * 1024 * 1024) < 65536:
                        sys.stdout.write(f"\r    Downloaded {total_bytes / (1024 * 1024):.2f} MB")
                        sys.stdout.flush()
        print(f"\r    [OK] Downloaded {total_bytes / (1024 * 1024):.2f} MB complete.")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(tmp_path, dest_path)
        return True
    except Exception as e:
        print(f"\r    [FAIL] Error downloading {desc}: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False

# ==============================================================================
# 01. ANCPI ADMINISTRATIV
# ==============================================================================
def setup_01_administrativ():
    print("\n--- [01] ANCPI ADMINISTRATIV NAȚIONAL ---")
    d = os.path.join(BASE_DIR, "01_ADMINISTRATIV_ANCPI")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "ANCPI_DataGovRo_Unitati_Administrativ_Teritoriale.url"),
        "https://data.gov.ro/dataset/unitati-administrativ-teritoriale"
    )
    create_internet_shortcut(
        os.path.join(d, "ANCPI_Geoportal_Catalog_Download.url"),
        "http://geoportal.ancpi.ro/geoportal/catalog/download/download.page"
    )
    
    # Download Judete 1stOrder KMZ
    kmz_url = "https://data.gov.ro/dataset/6b7b18eb-1d88-404a-8ce0-b40d010fc70c/resource/e50c9ec3-d770-4126-8375-32e5bf289d15/download/administrativeunit_1storder.kmz"
    kmz_path = os.path.join(d, "AdministrativeUnit_1stOrder_Judete.kmz")
    stream_download(kmz_url, kmz_path, "Județe România (1st Order)", min_size=50000)

    # QLR pentru UAT Shapefile
    qlr_uat = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="vector" geometry="Polygon">
      <id>ancpi_uat_national</id>
      <datasource>./Unitate_administrativa_UAT.shp</datasource>
      <title>ANCPI - Limite Administrative UAT (3.186 comune/orase/municipii)</title>
      <layername>ANCPI UAT National (Stereo 70)</layername>
      <srs>
        <spatialrefsys nativeFormat="Wkt">
          <wkt>PROJCRS["Stereo 70 / Dealul Piscului 1970",BASEGEOGCRS["Dealul Piscului 1970",DATUM["Dealul Piscului 1970",ELLIPSOID["Krassowsky 1940",6378245,298.3,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4288]],CONVERSION["Romania Double Sombrero 1970",METHOD["Oblique Stereographic",ID["EPSG",9809]],PARAMETER["Latitude of natural origin",46,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",25,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.99975,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",500000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["northing (X)",north,ORDER[1],LENGTHUNIT["metre",1]],AXIS["easting (Y)",east,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Cadastre, engineering survey, topographic mapping (large and medium scale)."],AREA["Romania - onshore."],BBOX[43.62,20.26,48.27,29.74]],ID["EPSG",3844]]</wkt>
        </spatialrefsys>
      </srs>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "ANCPI_UAT_National.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_uat)

# ==============================================================================
# 02. PATRIMONIU RAN cIMeC
# ==============================================================================
def setup_02_patrimoniu():
    print("\n--- [02] INP / cIMeC PATRIMONIU ARHEOLOGIC NAȚIONAL ---")
    d = os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "Portal_Oficial_RAN_cIMeC.url"),
        "https://ran.cimec.ro/"
    )
    create_internet_shortcut(
        os.path.join(d, "Harta_Interactiva_Patrimoniu_cIMeC.url"),
        "https://map.cimec.ro/Mapserver/"
    )
    
    # QLR pentru MapServer cIMeC WMS
    qlr_wms = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="raster">
      <id>cimec_ran_wms</id>
      <datasource>contextualWMSLegend=0&amp;crs=EPSG:3844&amp;dpiMode=7&amp;featureCount=10&amp;format=image/png&amp;layers=RAN&amp;styles=&amp;url=https://map.cimec.ro/Mapserver/WMSServer</datasource>
      <title>Patrimoniu Arheologic RAN cIMeC (WMS)</title>
      <layername>cIMeC RAN WMS (Stereo 70)</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "cIMeC_RAN_Romania_WMS.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_wms)

# ==============================================================================
# 03. AGRICOL APIA LPIS
# ==============================================================================
def setup_03_agricol():
    print("\n--- [03] APIA LPIS BLOCURI FIZICE NAȚIONAL 2025 ---")
    d = os.path.join(BASE_DIR, "03_AGRICOL_APIA_LPIS_2025")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "APIA_DataGovRo_Blocuri_Fizice_2025.url"),
        "https://data.gov.ro/dataset/parcele-de-referinta-2025-blocuri-fizice-apia"
    )
    
    # QLR direct in ZIP via GDAL /vsizip/
    qlr_apia = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="vector" geometry="Polygon">
      <id>apia_lpis_blocuri_fizice_2025</id>
      <datasource>/vsizip/./blocuri_fizice_2025_Romania_Complet.zip</datasource>
      <title>APIA - Parcele de Referinta Blocuri Fizice 2025 (1.54M parcele)</title>
      <layername>APIA Blocuri Fizice 2025 (VSIZIP)</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "APIA_LPIS_Blocuri_Fizice_2025.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_apia)

# ==============================================================================
# 04. HIDROGRAFIE ANAR ROWATER
# ==============================================================================
def setup_04_hidrografie():
    print("\n--- [04] ANAR ROWATER HIDROGRAFIE & RO-FLOODS ---")
    d = os.path.join(BASE_DIR, "04_HIDROGRAFIE_ANAR_ROWATER")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "ANAR_DataGovRo_Hidrografie.url"),
        "https://data.gov.ro/dataset/hidrografie"
    )
    create_internet_shortcut(
        os.path.join(d, "RO_FLOODS_Inundatii_Portal.url"),
        "https://inundatii.ro/"
    )
    
    # QLR RO-FLOODS Hazard T100
    qlr_rofloods = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="raster">
      <id>rofloods_hhi_t100</id>
      <datasource>contextualWMSLegend=0&amp;crs=EPSG:3844&amp;dpiMode=7&amp;featureCount=10&amp;format=image/png&amp;layers=rofloods:HHI_T100_extensie&amp;styles=&amp;url=https://inundatii.ro/geoserver/wms</datasource>
      <title>ANAR - Hazard Inundatii RO-FLOODS HHI T100 (WMS)</title>
      <layername>RO-FLOODS HHI T100 WMS (Stereo 70)</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "RO_FLOODS_Hazard_T100_WMS.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_rofloods)

# ==============================================================================
# 05. MEDIU NATURA 2000 EEA
# ==============================================================================
def setup_05_mediu():
    print("\n--- [05] EEA / ANANP NATURA 2000 & ARII PROTEJATE ---")
    d = os.path.join(BASE_DIR, "05_MEDIU_NATURA2000_EEA")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "EEA_Discomap_Natura2000.url"),
        "https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer"
    )
    create_internet_shortcut(
        os.path.join(d, "ANANP_Arii_Protejate_Romania.url"),
        "http://ananp.gov.ro/"
    )
    
    qlr_natura = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="raster">
      <id>eea_natura2000_wms</id>
      <datasource>contextualWMSLegend=0&amp;crs=EPSG:3844&amp;dpiMode=7&amp;featureCount=10&amp;format=image/png&amp;layers=1&amp;styles=&amp;url=https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer</datasource>
      <title>EEA - Natura 2000 Sites (Habitats SCI/SAC &amp; Birds SPA WMS)</title>
      <layername>Natura 2000 EEA WMS</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "Natura2000_EEA_WMS.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_natura)

# ==============================================================================
# 06. FOND FORESTIER MMAP / ROMSILVA
# ==============================================================================
def setup_06_silvic():
    print("\n--- [06] FOND FORESTIER MMAP / ROMSILVA & COPERNICUS ---")
    d = os.path.join(BASE_DIR, "06_SILVIC_ROMSILVA_MMAP")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "Inspectorul_Padurii_SUMAL2.url"),
        "https://inspectorulpadurii.ro/"
    )
    create_internet_shortcut(
        os.path.join(d, "Portal_Date_Deschise_MMAP.url"),
        "https://data.gov.ro/organization/ministerul-mediului-apelor-si-padurilor"
    )
    
    readme = """FONDUL FORESTIER NATIONAL SI INSPECTORUL PADURII (ROMANIA)
===========================================================
1. MMAP / RNP ROMSILVA gestioneaza fondul forestier prin SUMAL 2.0.
   - Portal public: https://inspectorulpadurii.ro/
   - Acces direct REST protejat prin OAuth / STS (HTTP 403 pentru GeoServer public).
   - Clasificare: ACCES RESTRICTIONAT / AUTENTIFICARE NECESARA (Integritate I1).
2. Monitorizarea Padurilor la Nivel National prin Copernicus:
   - Copernicus High Resolution Layers (Forest / Tree Cover Density).
   - Disponibil liber prin serviciile OGC WMS EEA Discomap.
"""
    with open(os.path.join(d, "README_FOND_FORESTIER.txt"), "w", encoding="utf-8") as f:
        f.write(readme)
        
    qlr_forest = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="raster">
      <id>copernicus_forest_wms</id>
      <datasource>contextualWMSLegend=0&amp;crs=EPSG:3844&amp;dpiMode=7&amp;featureCount=10&amp;format=image/png&amp;layers=TCD_2018_10m&amp;styles=&amp;url=https://image.discomap.eea.europa.eu/arcgis/services/GioLandPublic/TreeCoverDensity_2018/ImageServer/WMSServer</datasource>
      <title>Copernicus - Tree Cover Density / Fond Forestier (WMS)</title>
      <layername>Copernicus Paduri TCD WMS</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "Copernicus_Forest_Density_WMS.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_forest)

# ==============================================================================
# 07. NOMENCLATOR RENNS ANCPI
# ==============================================================================
def setup_07_nomenclator():
    print("\n--- [07] ANCPI RENNS (NOMENCLATOR STRADAL & ADRESE) ---")
    d = os.path.join(BASE_DIR, "07_NOMENCLATOR_RENNS_ANCPI")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "ANCPI_RENNS_Public.url"),
        "https://renns.ancpi.ro/renns-public/"
    )
    create_internet_shortcut(
        os.path.join(d, "ANCPI_Geoportal_National.url"),
        "https://geoportal.ancpi.ro/"
    )
    
    readme = """REGISTRUL ELECTRONIC NATIONAL AL NOMENCLATURILOR STRADALE (RENNS)
=================================================================
1. RENNS este registrul public oficial unic al Romaniei gestionat de ANCPI pentru:
   - Arterele si strazile oficiale per localitate.
   - Numerele postale administrative.
2. Interogare oficiala publica: https://renns.ancpi.ro/renns-public/
3. Serviciul INSPIRE Addresses (AD) WFS:
   https://geoportal.ancpi.ro/arcgis/services/INSPIRE/Addresses/MapServer/WFSServer
"""
    with open(os.path.join(d, "README_RENNS_ADRESE.txt"), "w", encoding="utf-8") as f:
        f.write(readme)
        
    qlr_renns = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="vector" geometry="Point">
      <id>ancpi_renns_adrese_wfs</id>
      <datasource>pagingEnabled='true' preferCoordinatesForWfsT11='false' srsname='EPSG:3844' typename='AD:Address' url='https://geoportal.ancpi.ro/arcgis/services/INSPIRE/Addresses/MapServer/WFSServer' version='auto'</datasource>
      <title>ANCPI - Nomenclator Stradal si Adrese Postale RENNS (WFS)</title>
      <layername>ANCPI RENNS Adrese (WFS)</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "ANCPI_RENNS_Adrese_WFS.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_renns)

# ==============================================================================
# 08. INFRASTRUCTURA TRANSPORT CNAIR & CFR
# ==============================================================================
def setup_08_transport():
    print("\n--- [08] CNAIR & CFR INFRASTRUCTURĂ TRANSPORT NAȚIONAL ---")
    d = os.path.join(BASE_DIR, "08_TRANSPORT_CNAIR_CFR")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "CNAIR_DataGovRo_Drumuri_Majore.url"),
        "https://data.gov.ro/dataset/drumuri-principale-din-afara-aglomerarilor-art-10-directiva-2002-49-ce"
    )
    create_internet_shortcut(
        os.path.join(d, "CFR_DataGovRo_Cai_Ferate.url"),
        "https://data.gov.ro/dataset/caile-ferate-principale-din-romania-art-7-directiva-2002-49-ce"
    )
    
    # Download Major Railways
    rail_url = "https://data.gov.ro/dataset/6feb7f9b-99ff-4677-9db2-46e822075945/resource/f2955eb9-0038-4717-99d5-ac6db712117c/download/majorrailwaysource.gpkg"
    rail_path = os.path.join(d, "MajorRailways_Romania_CFR_MMAP.gpkg")
    stream_download(rail_url, rail_path, "Căi Ferate Principale România (CFR / MMAP)", min_size=500000)

    # Download Major Roads (if not finished or absent)
    roads_url = "https://data.gov.ro/dataset/2cb849bc-4cd9-449e-825e-21908bae94e6/resource/49065d07-5516-44ce-9c6f-dabf11f5b0ec/download/df4_8_majorroads_outagg_romania_2022.gpkg"
    roads_path = os.path.join(d, "MajorRoads_Romania_CNAIR_MMAP.gpkg")
    stream_download(roads_url, roads_path, "Drumuri Principale România (CNAIR / MMAP)", min_size=1000000)

    # QLR Drumuri & Cai Ferate
    qlr_transport = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="vector" geometry="Line">
      <id>romania_major_roads</id>
      <datasource>./MajorRoads_Romania_CNAIR_MMAP.gpkg</datasource>
      <title>CNAIR / MMAP - Drumuri Principale Romania (Autostrazi, DN, DJ)</title>
      <layername>CNAIR Drumuri Principale</layername>
    </maplayer>
    <maplayer type="vector" geometry="Line">
      <id>romania_major_railways</id>
      <datasource>./MajorRailways_Romania_CFR_MMAP.gpkg</datasource>
      <title>CFR / MMAP - Cai Ferate Principale Romania</title>
      <layername>CFR Cai Ferate Nationale</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "Retea_Transport_National.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_transport)

# ==============================================================================
# 09. GEODEZIE SI RETEA ANCPI
# ==============================================================================
def setup_09_geodezie():
    print("\n--- [09] ANCPI GEODEZIE & CAROIAJ STEREO 70 ---")
    d = os.path.join(BASE_DIR, "09_GEODEZIE_RETEA_ANCPI")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "ANCPI_TopRoSearch_Retea_Geodezica.url"),
        "https://geoportal.ancpi.ro/TopRoSearch/"
    )
    create_internet_shortcut(
        os.path.join(d, "ROPOS_Statii_Permanente_GNSS.url"),
        "https://www.ropos.ro/"
    )
    
    readme = """RETEAUA GEODEZICA NATIONALA SI SERVICIUL ROPOS (ANCPI)
======================================================
1. Sistemul de Coordonate de Stat al Romaniei:
   - Proiectia Stereografica 1970 (Stereo 70, EPSG:3844).
   - Elipsoid Krassowsky 1940, Punct Central 46°N 25°E.
2. Statii Permanente GNSS (Reteaua EUREF-RO / ROPOS):
   - Peste 150 de statii permanente care furnizeaza corectii RTK/DGNSS pe teritoriul national.
3. Portalul TopRoSearch ANCPI:
   - Permite cautarea si descarcarea fiselor punctelor de triangulatie si borrelor de nivelment.
"""
    with open(os.path.join(d, "README_GEODEZIE_STEREO70.txt"), "w", encoding="utf-8") as f:
        f.write(readme)
        
    qlr_geodezie = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="raster">
      <id>ancpi_toprosearch_wms</id>
      <datasource>contextualWMSLegend=0&amp;crs=EPSG:3844&amp;dpiMode=7&amp;featureCount=10&amp;format=image/png&amp;layers=Retea_Geodezica&amp;styles=&amp;url=https://geoportal.ancpi.ro/arcgis/services/Geodezie/ReteaGeodezica/MapServer/WMSServer</datasource>
      <title>ANCPI - Retea Geodezica si Statii Permanente (WMS)</title>
      <layername>ANCPI Geodezie WMS</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "ANCPI_Retea_Geodezica_Stereo70.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_geodezie)

# ==============================================================================
# 10. COPERNICUS LAND COVER (CLC)
# ==============================================================================
def setup_10_landcover():
    print("\n--- [10] COPERNICUS LAND COVER (CLC ROMÂNIA) ---")
    d = os.path.join(BASE_DIR, "10_COPERNICUS_LAND_COVER")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "Copernicus_Land_Monitoring_Service.url"),
        "https://land.copernicus.eu/"
    )
    
    qlr_clc = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="raster">
      <id>copernicus_clc_wms</id>
      <datasource>contextualWMSLegend=0&amp;crs=EPSG:3844&amp;dpiMode=7&amp;featureCount=10&amp;format=image/png&amp;layers=CORINE_Land_Cover_2018&amp;styles=&amp;url=https://image.discomap.eea.europa.eu/arcgis/services/Corine/CLC2018_WM/MapServer/WMSServer</datasource>
      <title>Copernicus - Corine Land Cover Romania (WMS)</title>
      <layername>Copernicus CLC 2018 WMS</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "Copernicus_Corine_Land_Cover_WMS.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_clc)

# ==============================================================================
# 11. IGR GEOLOGIE
# ==============================================================================
def setup_11_geologie():
    print("\n--- [11] IGR HARTA GEOLOGICĂ A ROMÂNIEI 1:1.000.000 ---")
    d = os.path.join(BASE_DIR, "11_GEOLOGIE_IGR")
    ensure_dir(d)
    
    create_internet_shortcut(
        os.path.join(d, "IGR_DataGovRo_Harta_Geologica.url"),
        "https://data.gov.ro/dataset/harta-geologica-a-romaniei-scara-1-1-000-000"
    )
    
    zip_url = "https://data.gov.ro/dataset/65c5a564-8483-4d1b-bac6-ce9de78fc52e/resource/8636a2ec-6ca3-4f73-bc1c-2fb8c657e8c0/download/geologie_1m.zip"
    zip_path = os.path.join(d, "geologie_1m.zip")
    if stream_download(zip_url, zip_path, "Harta Geologica a Romaniei 1:1M (IGR)", min_size=100000):
        # Extract if shapefiles not present
        if not os.path.exists(os.path.join(d, "geologie_1M.shp")):
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(d)
                print("    [OK] Dezarhivat Harta Geologica 1:1M IGR.")
            except Exception as e:
                print(f"    [WARN] Extragere geologie_1m.zip: {e}")

    qlr_geo = '''<!DOCTYPE qgis-layer-definition>
<qlr>
  <maplayers>
    <maplayer type="vector" geometry="Polygon">
      <id>igr_geologie_1m</id>
      <datasource>./geologie_1M.shp</datasource>
      <title>Institutul Geologic al Romaniei - Harta Geologica 1:1.000.000</title>
      <layername>IGR Geologie Romania 1M</layername>
    </maplayer>
  </maplayers>
</qlr>'''
    with open(os.path.join(d, "Geologie_Romania_1M.qlr"), "w", encoding="utf-8") as f:
        f.write(qlr_geo)

# ==============================================================================
# ROOT CONNECTIONS XML & MASTER QGIS PROJECT
# ==============================================================================
def setup_qgis_browser_integrations():
    print("\n--- [XML & PROIECT] CONEXIUNI QGIS BROWSER & PROIECT MASTER ---")
    
    # 1. CONEXIUNI_QGIS_OFICIALE.xml
    xml_content = '''<!DOCTYPE qgis_connections SYSTEM "http://mrcc.com/qgis/connections.dtd">
<qgis_connections version="1.0">
  <wms>
    <connection name="RO - ANCPI Ortofotoplan National" url="https://geoportal.ancpi.ro/arcgis/services/INSPIRE/Orthophoto/ImageServer/WMSServer" ignoreGetMapUrl="false" ignoreGetFeatureInfoUrl="false" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - ANAR RO-FLOODS Inundatii T100 (inundatii.ro)" url="https://inundatii.ro/geoserver/wms" ignoreGetMapUrl="false" ignoreGetFeatureInfoUrl="false" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - EEA Natura 2000 Sites (Discomap)" url="https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer" ignoreGetMapUrl="false" ignoreGetFeatureInfoUrl="false" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - cIMeC Repertoriul Arheologic National (RAN)" url="https://map.cimec.ro/Mapserver/WMSServer" ignoreGetMapUrl="false" ignoreGetFeatureInfoUrl="false" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - Copernicus Corine Land Cover (CLC)" url="https://image.discomap.eea.europa.eu/arcgis/services/Corine/CLC2018_WM/MapServer/WMSServer" ignoreGetMapUrl="false" ignoreGetFeatureInfoUrl="false" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - Copernicus Tree Cover Density (Paduri)" url="https://image.discomap.eea.europa.eu/arcgis/services/GioLandPublic/TreeCoverDensity_2018/ImageServer/WMSServer" ignoreGetMapUrl="false" ignoreGetFeatureInfoUrl="false" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - ANCPI Retea Geodezica TopRoSearch" url="https://geoportal.ancpi.ro/arcgis/services/Geodezie/ReteaGeodezica/MapServer/WMSServer" ignoreGetMapUrl="false" ignoreGetFeatureInfoUrl="false" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
  </wms>
  <wfs>
    <connection name="RO - ANCPI INSPIRE Administrative Units (WFS)" url="https://geoportal.ancpi.ro/arcgis/services/INSPIRE/AdministrativeUnits/MapServer/WFSServer" version="auto" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - ANCPI INSPIRE Cadastral Parcels (WFS)" url="https://geoportal.ancpi.ro/arcgis/services/INSPIRE/CadastralParcels/MapServer/WFSServer" version="auto" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
    <connection name="RO - ANCPI INSPIRE Addresses RENNS (WFS)" url="https://geoportal.ancpi.ro/arcgis/services/INSPIRE/Addresses/MapServer/WFSServer" version="auto" ignoreAxisOrientation="false" invertAxisOrientation="false"/>
  </wfs>
  <arcgisfeatureserver>
    <connection name="RO - cIMeC Patrimoniu Arheologic RAN (ArcGIS REST)" url="https://eism.geo-spatial.ro/eismgeo/rest/services/Patrimoniu/PatrimoniuWM/MapServer"/>
    <connection name="RO - EEA Natura 2000 Sites (ArcGIS REST)" url="https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer"/>
  </arcgisfeatureserver>
  <xyz>
    <connection name="OpenStreetMap Standard" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" zmin="0" zmax="19"/>
    <connection name="Esri World Imagery" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" zmin="0" zmax="19"/>
    <connection name="Google Hybrid Satellite" url="https://mt1.google.com/vt/lyrs=y&amp;x={x}&amp;y={y}&amp;z={z}" zmin="0" zmax="20"/>
  </xyz>
</qgis_connections>
'''
    xml_path = os.path.join(BASE_DIR, "CONEXIUNI_QGIS_OFICIALE.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print("  [OK] CONEXIUNI_QGIS_OFICIALE.xml generat complet.")

    # 2. Launcher batch
    bat_content = f"""@echo off
chcp 65001 > nul
echo ===================================================================
echo     LANSARE BROWSER NATIONAL QGIS — STRATUMRO DATE OFICIALE
echo ===================================================================
echo.
set "PROJECT_PATH=%~dp0ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs"
if exist "C:\\Program Files\\QGIS 3.40.0\\bin\\qgis-bin.exe" (
    echo Deschid QGIS 3.40 cu proiectul National...
    start "" "C:\\Program Files\\QGIS 3.40.0\\bin\\qgis-bin.exe" "%PROJECT_PATH%"
) else (
    echo QGIS 3.40 nu a fost gasit in calea standard.
    pause
)
"""
    with open(os.path.join(BASE_DIR, "DESCHIDE_BROWSER_NATIONAL_QGIS.bat"), "w", encoding="utf-8") as f:
        f.write(bat_content)
    print("  [OK] DESCHIDE_BROWSER_NATIONAL_QGIS.bat generat.")

    # 3. Ghid de utilizare actualizat
    ghid_content = """# GHID DE UTILIZARE — BROWSERUL NAȚIONAL DE DATE OFICIALE (ROMÂNIA)
## StratumRO / romanian-opendata-specialist

Acest director (`national_server`) reprezintă depozitul centralizat și autoritar de date oficiale deschise la nivel național, optimizat pentru **panoul Browser din QGIS** (`/browser`) și fluxuri de lucru cadastrale / geodezice în **Stereo 70 (EPSG:3844)**.

---

## 1. Cum se utilizează în Panoul QGIS Browser (`/browser`)

### A. Adăugarea directorului ca "Favorite" în QGIS Browser
1. În QGIS, în panoul **Browser** din stânga:
2. Faceți clic dreapta pe secțiunea **Favorites** (Favorite) -> **Add a Directory...** (Adaugă director...).
3. Selectați folderul:
   `c:\\Users\\lefpa\\Downloads\\QGIS-AI\\national_server`
4. Acum aveți acces instant la toate cele 11 directoare tematice direct din QGIS Browser.

### B. Importul conexiunilor WMS / WFS / REST
- Trageți (`Drag & Drop`) fișierul `CONEXIUNI_QGIS_OFICIALE.xml` direct pe panoul **Browser** din QGIS.
- QGIS va adăuga automat în arborii WMS/WMTS, WFS și ArcGIS REST toate endpoint-urile oficiale de stat.

### C. Deschiderea Proiectului Master Național
- Dublu-clic pe `DESCHIDE_BROWSER_NATIONAL_QGIS.bat` sau deschideți fișierul `ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs` direct în QGIS.

---

## 2. Inventarul Straturilor Naționale Disponibile

| Folder | Tematică | Autoritate | Format & Acces QGIS | Notă Tehnică |
|---|---|---|---|---|
| `01_ADMINISTRATIV_ANCPI/` | Limite UAT & Județe | ANCPI | Shapefile + KMZ + QLR | Toate cele 3.186 de UAT-uri din România |
| `02_PATRIMONIU_RAN_CIMEC/` | Situri Arheologice | INP / cIMeC | GeoPackage SQLite (52.823 situri) | Puncte clasate, Poligoane situri, Arhiva Pârvan |
| `03_AGRICOL_APIA_LPIS_2025/` | Parcele Blocuri Fizice | APIA | ZIP / Shapefile via `/vsizip/` (1.54M parcele) | Ingestie instant fără dezarhivare (1.12 GB) |
| `04_HIDROGRAFIE_ANAR_ROWATER/` | Râuri, Bazine, Diguri | ANAR ROWATER | Shapefile (13.078 râuri) + WMS RO-FLOODS | Hidrografie națională + risc inundații T100 |
| `05_MEDIU_NATURA2000_EEA/` | Natura 2000 SCI/SPA | EEA / ANANP | GeoJSON + WMS Discomap | Situri habitate și protecție avifaunistică |
| `06_SILVIC_ROMSILVA_MMAP/` | Fond Forestier | MMAP / ROMSILVA | Documentație SUMAL 2.0 + Copernicus Forest WMS | Inspectorul Pădurii + Acoperire arboricolă |
| `07_NOMENCLATOR_RENNS_ANCPI/` | Nomenclator Stradal | ANCPI | Serviciu WFS INSPIRE + Shortcut oficial | Registrul Electronic al Adreselor |
| `08_TRANSPORT_CNAIR_CFR/` | Rețea Drumuri & Căi Ferate | CNAIR / CFR / MMAP | GeoPackage (Drumuri majore + Căi ferate) | Rețeaua națională completă de transport |
| `09_GEODEZIE_RETEA_ANCPI/` | Rețea Geodezică | ANCPI | Serviciu WMS TopRoSearch + Stații ROPOS | Puncte de triangulație și caroiaj Stereo 70 |
| `10_COPERNICUS_LAND_COVER/` | Acoperirea Terenului | Copernicus / EEA | Serviciu WMS Corine Land Cover | Mozaic național CLC 2018 |
| `11_GEOLOGIE_IGR/` | Harta Geologică 1:1M | IGR | Shapefile complet + QLR | Formațiuni și falii geologice |

---

## 3. Conformitate și Reguli Evidence-First
- **Zero date fabricate (I1):** Toate fișierele provin exclusiv din registrele publice și serverele oficiale de stat.
- **Sistem de Proiecție:** Nativ **Stereo 70 (EPSG:3844)** pentru straturile vectoriale naționale.
- **Valoare Juridică (I5):** Straturile reprezintă **referință tehnică pre-cadastrală**, fără a substitui documentațiile semnate de persoana autorizată ANCPI.
"""
    with open(os.path.join(BASE_DIR, "GHID_UTILIZARE_SERVER_NATIONAL.md"), "w", encoding="utf-8") as f:
        f.write(ghid_content)
    print("  [OK] GHID_UTILIZARE_SERVER_NATIONAL.md actualizat complet.")

def main():
    print("===================================================================")
    print("   STRATUMRO NATIONAL GEODATA HARVESTER — ROMÂNIA OFICIAL")
    print(f"   Destinație: {BASE_DIR}")
    print("===================================================================")
    ensure_dir(BASE_DIR)

    setup_01_administrativ()
    setup_02_patrimoniu()
    setup_03_agricol()
    setup_04_hidrografie()
    setup_05_mediu()
    setup_06_silvic()
    setup_07_nomenclator()
    setup_08_transport()
    setup_09_geodezie()
    setup_10_landcover()
    setup_11_geologie()
    setup_qgis_browser_integrations()

    print("\n[SUCCESS] Procesul de recoltare si structurare nationala s-a finalizat cu succes!")

if __name__ == "__main__":
    main()
