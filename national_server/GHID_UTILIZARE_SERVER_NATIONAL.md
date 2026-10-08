# GHID DE UTILIZARE — BROWSERUL NAȚIONAL DE DATE OFICIALE (ROMÂNIA)
## StratumRO / romanian-opendata-specialist

Acest director (`national_server`) reprezintă depozitul centralizat și autoritar de date oficiale deschise la nivel național, optimizat pentru **panoul Browser din QGIS** (`/browser`) și fluxuri de lucru cadastrale / geodezice în **Stereo 70 (EPSG:3844)**.

---

## 1. Cum se utilizează în Panoul QGIS Browser (`/browser`)

### A. Adăugarea directorului ca "Favorite" în QGIS Browser
1. În QGIS, în panoul **Browser** din stânga:
2. Faceți clic dreapta pe secțiunea **Favorites** (Favorite) -> **Add a Directory...** (Adaugă director...).
3. Selectați folderul:
   `c:\Users\lefpa\Downloads\QGIS-AI\national_server`
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
