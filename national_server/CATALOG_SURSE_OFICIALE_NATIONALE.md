# CATALOGUL NAȚIONAL AL DATELOR OFICIALE DESCHISE — ROMÂNIA
## Depozitul Central StratumRO & Browser QGIS (`/browser`)

Acest catalog documentează toate seturile de date geografice naționale oficiale, brute și autoritare, colectate și structurate de subagentul **`romanian-opendata-specialist`** sub coordonarea **`stratumro-orchestrator`**, în deplină conformitate cu cele **8 Reguli Științifice Evidence-First**.

---

### Sinteză Executivă: 11 Categorii Tematice Naționale

| Nr. | Categorie & Tematică | Autoritate Publică Emitentă | Protocol / Format | Dimensiune & Nr. Entități | Bază Legală / Directivă |
|:---:|---|---|---|---|---|
| **01** | **Limite Administrative (UAT, Județe)** | ANCPI | Shapefile + KMZ + WFS | 3.186 UAT-uri (72.8 MB) + 42 Județe | Legea 7/1996, Directiva INSPIRE 2007/2/CE (AU) |
| **02** | **Patrimoniu Arheologic (RAN & RAR)** | INP / cIMeC | GeoPackage SQLite + ArcGIS REST | 52.823 situri clasate (puncte + poligoane) | OG 43/2000, Legea 422/2001 |
| **03** | **Parcele Agricole de Referință (LPIS)** | APIA / MADR | ZIP Shapefile via GDAL `/vsizip/` | 1.548.145 blocuri fizice (1.12 GB) | Reg. (UE) 2021/2115, Ordin MADR |
| **04** | **Hidrografie, Bazine & Risc Inundații** | ANAR ROWATER / MMAP | Shapefile + GeoServer WMS | 13.078 râuri (249 MB), 15 bazine, 3.063 diguri | Directiva 2007/60/CE, HG 892/2023 (PMRI) |
| **05** | **Arii Naturale Protejate (Natura 2000)** | EEA / ANANP / MMAP | GeoJSON + ArcGIS REST + WMS | Situri Habitate (SCI/SAC) & Păsări (SPA) | Directiva 92/43/CEE, Directiva 2009/147/CE |
| **06** | **Fond Forestier & Inspectorul Pădurii** | MMAP / RNP ROMSILVA | Documentație SUMAL 2.0 + Copernicus | Monitorizare acoperire arboricolă (TCD) | Legea 46/2008 (Codul Silvic) |
| **07** | **Nomenclator Stradal & Adrese (RENNS)** | ANCPI | Serviciu OGC WFS INSPIRE (AD) | Adrese administrative și artere stradale | Legea 7/1996, Ordin ANCPI |
| **08** | **Infrastructură Transport (Drumuri, Căi Ferate)** | CNAIR / CFR / MT / MMAP | GeoPackage SQLite | Rețeaua națională de autostrăzi, DN, DJ și căi ferate | Directiva 2002/49/CE |
| **09** | **Rețea Geodezică & Stații GNSS (ROPOS)** | ANCPI | Serviciu WMS TopRoSearch + Stații RTK | Peste 150 stații permanente EUREF-RO | Ordinul ANCPI 600/2023 |
| **10** | **Acoperirea Terenului (Corine Land Cover)** | Copernicus / EEA | Serviciu OGC WMS Discomap | Mozaic național CLC 2018 / 2021 | Programul Copernicus Land Monitoring |
| **11** | **Geologie Națională (Scara 1:1.000.000)** | IGR (Institutul Geologic) | Shapefile poligoane + linii falii | Formațiuni geologice și tectonică națională | Harta Geologică a României |

---

### Descrierea Detaliată a Directoarelor și Straturilor

#### 01_ADMINISTRATIV_ANCPI
- **Conținut:**
  - `Unitate_administrativa_UAT.shp`: Geometriile oficiale ale tuturor celor 3.186 de comune, orașe și municipii din România, inclusiv cod SIRUTA, natCode, denumire și județ. Sistem de coordonate: Stereo 70 (EPSG:3844).
  - `AdministrativeUnit_1stOrder_Judete.kmz`: Delimitarea oficială a celor 41 de județe și a Municipiului București.
  - `ANCPI_UAT_National.qlr`: Strat pre-configurat pentru QGIS.
  - Conexiune WFS directă către Geoportalul ANCPI.

#### 02_PATRIMONIU_RAN_CIMEC
- **Conținut:**
  - `RAN_Romania_National_Complet.gpkg`: Bază de date spațială unificată SQLite conținând:
    1. `01_RAN_National_Puncte` (28.988 situri clasate cu cod RAN unic)
    2. `02_RAN_National_Poligoane` (16.484 perimetre de protecție arheologică)
    3. `03_RAR_National_Arhiva_Parvan` (7.351 situri arheologice din repertoriul Vasile Pârvan)
  - `cIMeC_RAN_Romania_WMS.qlr`: Conexiune MapServer cIMeC.
  - `cIMeC_RAN_Romania_ArcGIS_REST.qlr`: Conexiune FeatureService REST.

#### 03_AGRICOL_APIA_LPIS_2025
- **Conținut:**
  - `blocuri_fizice_2025_Romania_Complet.zip`: Arhiva autoritară de 1.12 GB conținând 1.548.145 parcele de referință agricole din România.
  - `APIA_LPIS_Blocuri_Fizice_2025.qlr`: Permite vizualizarea și interogarea directă a arhivei ZIP prin driverul GDAL virtual `/vsizip/` fără a fi necesară dezarhivarea de 3+ GB.

#### 04_HIDROGRAFIE_ANAR_ROWATER
- **Conținut:**
  - `CursuriApaRauriSegmente.shp`: 13.078 cursuri de apă cadastrate din România (EPSG:3844).
  - `BazineHidrografice.shp`: Toate cele 15 bazine hidrografice naționale.
  - `Diguri.shp`: 3.063 diguri naționale de apărare împotriva inundațiilor.
  - `RO_FLOODS_Hazard_T100_WMS.qlr`: Harta de hazard la inundații HHI T100 conform Directivei Europene 2007/60/CE.

#### 05_MEDIU_NATURA2000_EEA
- **Conținut:**
  - `natura2000_eea_referinta.geojson`: Perimetrele siturilor de importanță comunitară (Habitate SCI/SAC) și ariilor de protecție specială avifaunistică (SPA).
  - `Natura2000_EEA_WMS.qlr`: Streaming oficial de înaltă performanță de la European Environment Agency.

#### 06_SILVIC_ROMSILVA_MMAP
- **Conținut:**
  - Documentație tehnică referitoare la sistemul național de trasabilitate a lemnului SUMAL 2.0 / Inspectorul Pădurii.
  - Notificare de acces restricționat (autentificare securizată STS / OAuth).
  - `Copernicus_Forest_Density_WMS.qlr`: Densitatea acoperirii arboricole (Tree Cover Density 10m) furnizată de Copernicus Land Monitoring.

#### 07_NOMENCLATOR_RENNS_ANCPI
- **Conținut:**
  - `ANCPI_RENNS_Adrese_WFS.qlr`: Serviciu WFS OGC pentru Registrul Electronic Național al Nomenclaturilor Stradale (Addresses - AD).
  - Legături directe către portalul public ANCPI RENNS.

#### 08_TRANSPORT_CNAIR_CFR
- **Conținut:**
  - `MajorRoads_Romania_CNAIR_MMAP.gpkg`: Rețeaua principală de transport rutier (Autostrăzi, Drumuri Naționale, Drumuri Județene).
  - `MajorRailways_Romania_CFR_MMAP.gpkg`: Căile ferate naționale magistrale și secundare.
  - `Retea_Transport_National.qlr`: Strat combinat QGIS.

#### 09_GEODEZIE_RETEA_ANCPI
- **Conținut:**
  - Ghid tehnic al Sistemului Național de Referință Stereo 70 (EPSG:3844) și elipsoidul Krassowsky 1940.
  - `ANCPI_Retea_Geodezica_Stereo70.qlr`: Rețeaua geodezică națională de stat și stațiile permanente GNSS ROPOS / EUREF-RO.

#### 10_COPERNICUS_LAND_COVER
- **Conținut:**
  - `Copernicus_Corine_Land_Cover_WMS.qlr`: Clasificarea europeană a utilizării terenului Corine Land Cover (CLC) pentru România.

#### 11_GEOLOGIE_IGR
- **Conținut:**
  - `geologie_1M.shp`: Harta geologică a României la scara 1:1.000.000 (formațiuni geologice litologice și cronostratigrafice).
  - `limite_geologice_1M.shp`: Falii și contacte tectonice.
  - `Geologie_Romania_1M.qlr`: Strat QGIS pre-configurat.

---

### Integrarea cu Panoul QGIS Browser (`/browser`)

Pentru a accesa toate aceste date direct în QGIS:
1. **Adăugare ca Director Favorit:**  
   În panoul **Browser** din stânga QGIS, faceți clic dreapta pe **Favorites** -> **Add a Directory...** și selectați:  
   `c:\Users\lefpa\Downloads\QGIS-AI\national_server`
2. **Import Conexiuni Web de Stat:**  
   Trageți (`Drag & Drop`) fișierul `CONEXIUNI_QGIS_OFICIALE.xml` peste panoul Browser.
3. **Deschidere Proiect Pre-configurat:**  
   Rulați `DESCHIDE_BROWSER_NATIONAL_QGIS.bat` sau deschideți `ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs`.
