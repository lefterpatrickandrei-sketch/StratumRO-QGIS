# GHID DE UTILIZARE — SERVER NAȚIONAL DE DATE OFICIALE (ROMÂNIA)

Acest director (`national_server`) reprezintă depozitul central de date oficiale brute și servicii geospatiale de stat pentru România, pregătit pentru utilizare prin simplu **Drag & Drop** în QGIS.

## Regula de Aur
- **Toate seturile naționale sunt BRUTE și COMPLETE** (așa cum sunt publicate de ANCPI, APIA, ANAR, INP/cIMeC, EEA).
- **NU s-a efectuat nicio decupare sau alterare de geometrii în afara UAT Iepurești.**
- Orice specialist sau surveyor autorizat poate utiliza aceste fișiere pentru **oricare dintre cele 3.186 UAT-uri din România**.

---

## Cum se utilizează prin Drag & Drop în QGIS

### 1. Importul Conexiunilor WMS / WFS (1 secundă)
- Trage fișierul `CONEXIUNI_QGIS_OFICIALE.xml` direct în panoul **Browser** din stânga ecranului QGIS.
- QGIS va importa automat conexiunile de stat:
  - **ANCPI Ortofotoplan Național** (WMS)
  - **ANAR RO-FLOODS Zone Inundabile T100** (WMS)
  - **EEA Natura 2000 Situri Comunitare** (WMS)
  - **cIMeC Repertoriul Arheologic Național** (WMS)

### 2. Încărcarea Limitelor Administrative (ANCPI)
- Intră în `01_ADMINISTRATIV_ANCPI/`
- Trage fișierul `Unitate_administrativa_UAT.shp` în QGIS Canvas.
- Conține toate cele 3.186 de UAT-uri din România (`natCode`, denumire oficială, cod SIRUTA).

### 3. Încărcarea Blocurilor Fizice Agricole (APIA LPIS 2025)
- Intră în `03_AGRICOL_APIA_LPIS_2025/`
- Trage arhiva `blocuri_fizice_2025_Romania_Complet.zip` direct în QGIS. QGIS o citește instant via driverul virtual GDAL `/vsizip/`.

### 4. Încărcarea Hidrografiei Naționale (ANAR ROWATER)
- Intră în `04_HIDROGRAFIE_ANAR_ROWATER/`
- Trage `CursuriApaRauriSegmente.shp` (toate râurile), `BazineHidrografice.shp` sau `Diguri.shp`.
- Trage `RO_FLOODS_Hazard_T100_WMS.qlr` pentru a vizualiza riscul de inundații pe cursul de apă analizat.

### 5. Încărcarea Siturilor Arheologice (INP / cIMeC RAN)
- Intră în `02_PATRIMONIU_RAN_CIMEC/`
- Trage `cIMeC_RAN_Romania_WMS.qlr` pentru harta națională de patrimoniu.
- Deschide `Portal_Oficial_RAN_cIMeC.url` pentru fișa de sit arheologic detaliată.

---

## Clasificare Riguroasă (Fără Ambiguități)
- Toate datele din acest server sunt clasificate ca: **`oficial`** (date suverane de stat emise de autorități publice).
- Niciun strat din acest server nu este generat de AI și nu conține modificări algoritmice.
