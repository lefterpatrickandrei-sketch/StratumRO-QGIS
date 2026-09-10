# Plan de Pilotare pe Teren & Protocol de Validare Geodezică Independentă 📐🛰️

**Proiect:** StratumRO-QGIS  
**Scop:** Trecerea de la validarea fotogrammetrică de laborator la **certificarea geodezică terestră independentă (Field Validation)** conform cerințelor ANCPI Ordinul 600/2023.

---

## 1. Context & Obiective

Până în prezent, evaluarea cantitativă a platformei StratumRO a fost efectuată pe arealul experimental **Campus USAMV Cluj-Napoca (AOI 1 - 46.5 ha)**, utilizând un set de referință restrâns de 29 clădiri digitizate fotogrammetric și parțial verificate topografic.

Pentru a stabili **generalizabilitatea** algoritmilor și pentru a fundamenta științific acuratețea metrică, este necesară extinderea pe un al doilea areal independent (**AOI 2 - Sit Pilot Urban/Rezidențial**) și aplicarea unui **protocol riguros de măsurători geodezice terestre (GNSS RTK + Stație Totală)**.

### Obiective Principale:
1. **Validare pe Teren a Acurateței Planimetrice:** Măsurarea directă pe soclu a colțurilor clădirilor cu precizie $\sigma_{XY} \le 0.02\text{ m}$.
2. **Determinarea Empirică a Distanței Streașină–Soclu ($d_{\text{streașină}}$):** Măsurarea decalajului orizontal dintre marginea acoperișului extrasă din ortofoto și peretele clădirii măsurat terestru.
3. **Testarea Separării la Calcan pe Morfologie Densă:** Evaluarea performanței de tăiere nDSM pe clădiri înșiruite cu acoperișuri la aceeași cotă.
4. **Validarea Reducerii Efortului Uman (89%):** Cronometrarea formală a doi operatori geodezi independenți (trasare manuală clasică vs. revizuire asistată de StratumRO).

---

## 2. Criterii de Selecție pentru AOI 2 (Sit Pilot Independent)

| Criteriu | Specificație Minimă | Raționament Geodezic |
| :--- | :--- | :--- |
| **Tipologie Urbană** | Mixtă: Rezidențial individual (case parter / P+1) + Corpuri alipite la calcan | Testează atât regularizarea 90° simplă, cât și separarea topologică complexă. |
| **Suprafață Eșantion** | 20 – 50 ha (~100 – 250 imobile/clădiri) | Eșantion statistic reprezentativ ($N \ge 100$) pentru intervale de confidență 95% înguste. |
| **Date Aeriene Disponibile** | Ortofoto RGB $\le 10\text{ cm}$ GSD + LiDAR dens ($\ge 8\text{ puncte/m}^2$) | Aceleași cerințe tehnice ca la AOI 1 pentru comparabilitate directă. |
| **Disponibilitate WFS ANCPI** | Plan parcelar recepționat oficial în Stereo 70 | Permite evaluarea modulului de potrivire Procrustes cu limitele de proprietate. |
| **Accesibilitate Teren** | Vizibilitate la cer pe fațadele principale și fronturi stradale | Asigură recepție satelitară optimă pentru ROMPOS RTK. |

---

## 3. Protocolul Tehnic de Măsurători Terestre (Tier 1 Survey Grade)

### 3.1. Echipamente & Rețea Geodezică
- **Receptor GNSS:** Receptor bifrecvență/multifrecvență (GPS + GLONASS + Galileo + BeiDou) cu capabilitate de compensare a înclinării jalonului (IMU-tilt compensation, ex. Leica GS18 T sau Trimble R12i).
- **Corecții Diferențiale:** Serviciul național **ROMPOS** (Rețeaua Națională de Stații GNSS Permanente), profil `RTK_ROMPOS_Stereo70` sau `VRS_Stereo70`.
  - Stare obligatorie de rezolvare: **`RTK FIXED`**.
  - Prag maxim de deviație standard admis: $\sigma_X \le 0.015\text{ m}$, $\sigma_Y \le 0.015\text{ m}$, $\sigma_H \le 0.025\text{ m}$.
- **Stație Totală Electronică (acuratețe unghiulară $\le 2''$, distanță $\le 1\text{ mm} + 1.5\text{ ppm}$):**  
  Utilizată obligatoriu pentru colțurile clădirilor situate sub coronament dens de arbori, în ganguri sau pe calcane unde semnalul GNSS este degradat (multipath).
- **Telemetru Laser Clasa 2 (precizie $\pm 1.0\text{ mm}$):**  
  Pentru determinarea lățimii streșinii ($d_{\text{streașină}}$) pe fiecare fațadă.

---

### 3.2. Metodologia de Preluare a Punctelor per Clădire

1. **Puncte pe Soclu (Cota Solului):**  
   Fiecare colț vizibil al clădirii este măsurat direct la intersecția fațadei cu trotuarul de protecție sau terenul natural. Se înregistrează minim 4 puncte per corp dreptunghiular și toate vârfurile de inflexiune pentru geometrii poligonale complexe.
2. **Offset-ul de Streașină ($d_{\text{streașină}}$):**  
   Pe fiecare latură se măsoară distanța orizontală perpendiculară de la suprafața tencuielii la linia jgheabului/streșinii. Dacă streașina este asimetrică, se notează valorile individuale per fațadă (Nord, Sud, Est, Vest).
3. **Cota Cornișă și Cota Coamă ($Z_{\text{cornisa}}$, $Z_{\text{coama}}$):**  
   Măsurate fără prismă (laser reflectorless) de la stație totală sau calculate prin profile transversale în norul de puncte LiDAR.
4. **Înregistrarea Fotografică & Fișa de Teren:**  
   Fiecare clădire pilot va avea o fotografie a fațadei principale și o schiță a amplasamentului cu numerotarea punctelor.

---

## 4. Formatul Datelor de Ieșire & Verificarea Calității

Datele de teren vor fi livrate în directorul `data/ground_truth/aoi2_pilot/` sub formă de:
1. **Fișier Coordonate Puncte Teren:** `aoi2_survey_points.csv`  
   Format: `Nr_Pct, X_Stereo70, Y_Stereo70, Z_MareaNeagra1975, Cod_Entitate, Tip_Punct, Sigma_XY, Metoda`
2. **Fișier Poligoane Soclu:** `aoi2_ground_truth_footprints.geojson`  
   CRS: `EPSG:3844` (Stereografic 1970). Conține atributele standardizate:
   - `bldg_id`: Cod unic (ex. `GT_AOI2_001`)
   - `surveyor_name`: Geodez autorizat ANCPI (Certificat seria/număr)
   - `eave_mean_offset_m`: Offset mediu măsurat al streșinii
   - `wall_material`: Material zidărie (cărămidă, beton, lemn)
   - `roof_type`: Tip acoperiș (șarpantă țiglă/tablă, terasă necirculabilă)
3. **Raport de Închidere pe Borne RGN:**  
   Verificarea pe minim 2 borne geodezice de ordin I-IV din rețeaua națională pentru excluderea erorilor de scară sau orientare.

---

## 5. Metodologia de Evaluare Comparativă (AI vs. Teren)

Odată integrat setul de date AOI 2, se va rula modulul de evaluare:
```bash
venv\Scripts\python engine/evaluation.py \
  --reference data/ground_truth/aoi2_ground_truth_footprints.geojson \
  --prediction workspace/output/aoi2_cladiri_stereo70.gpkg \
  --pred-layer CLADIRI_HIBRID \
  --prefix aoi2_pilot_validation
```

### Indicatori de Raportat Obligatoriu:
1. **Rata de Detecție Teritorială:** $P, R, F_1$ la nivel de clădire în interiorul perimetrului măsurat.
2. **Discrepanța Ariei Construite la Sol ($|\Delta A|$):** Comparație între aria PAD oficială și aria poligonului regularizat.
3. **Eroarea Medie Pătratică a Laturilor (Boundary RMSE):** Distanța punct la segment pe întregul contur.
4. **Analiză pe Straturi de Înălțime:** Comportamentul algoritmului pe anexe mici ($A < 20\text{ m}^2$) vs. clădiri principale ($A > 100\text{ m}^2$).

---

## 6. Calendar de Implementare Recomandat

| Faza | Activitate | Responsabil | Livrabil |
| :--- | :--- | :--- | :--- |
| **Faza 1** | Identificare sit pilot AOI 2 și achiziție zbor ortofoto/LiDAR | Coordonator GIS | Geopachet date primare |
| **Faza 2** | Măsurători terestre GNSS RTK + Stație Totală (50–100 clădiri) | Geodez Autorizat | `aoi2_ground_truth_footprints.geojson` |
| **Faza 3** | Rulare pipeline StratumRO și generare predicții brute | Antigravity Engine | `aoi2_cladiri_stereo70.gpkg` |
| **Faza 4** | Audit independent cu `engine/evaluation.py` și publicare raport | Auditor Tehnic | `docs/RAPORT_VALIDARE_AOI2.md` |
