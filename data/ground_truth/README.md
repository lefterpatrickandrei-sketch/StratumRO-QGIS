# Protocolul Tehnic de Achiziție & Calibrare Ground Truth (Stereo 70)

Acest document reglementează protocolul de măsurare și înregistrare a datelor de referință (Ground Truth) utilizate pentru evaluarea cantitativă a platformei **StratumRO**.

---

## 1. Ierarhia Nivelelor de Certitudine (Tiers)

| Nivel (Tier) | Sursă Date | Acuratețe Planimetrică ($XY$) | Metodă de Achiziție & Validare | Rol Metodologic |
|---|---|---|---|---|
| **Tier 1 (Survey Grade)** | Teren (GNSS-RTK / Stație Totală) | **$\pm 0.02 \dots 0.05\text{ m}$** | Rețea ROMPOS (RTK fix) sau drumuire topografică legată la borne RGN. Măsurătoare directă pe soclu. | **Etalonul de Aur** pentru certificare cadastrală ANCPI Ordinul 600/2023. |
| **Tier 2 (ANCPI Official WFS)** | Baza de date eTerra / ANCPI WFS | **$\pm 0.10 \dots 0.20\text{ m}$** | Parcele și corpuri de clădire intabulate oficial, recepționate post-2020 în Stereo 70 cu PAD avizat. | **Benchmark Oficial** la scară teritorială pentru conformitate urbană și UTR. |
| **Tier 3 (Stereoscopic Ref)** | Reconstituire stereoscopică asistată | $\pm 0.20 \dots 0.30\text{ m}$ | Reconstituire manuală pe ortofoto 15 cm + profile transversale în norul de puncte LiDAR. | **Fixture-uri Morfologice** pentru geometrii complexe (L, T, anexe). |
| **Tier 4 (Diagnostic Auxiliary)** | Date comunitare (OpenStreetMap, etc.) | **Necunoscută / Variabilă ($\pm 0.5 \dots 2.0\text{ m}$)** | Vectori crowd-sourced fără responsabilitate geodezică, digitizați la scări eterogene. | **Exclusiv Diagnostic** (Sanity Check pentru depistarea anomaliilor de supra/sub-segmentare). **NU se utilizează pentru calibrare sau certificare cadastrală!** |

---

## 2. Protocol de Măsurare Teren (Tier 1)

Pentru obținerea etalonului de nivel 1:
1. **Sistem de Proiecție:** Stereografic 1970 (Plan secant unic, Krasovski 1940, `EPSG:3844`).
2. **Sistem de Altitudini:** Marea Neagră 1975 (`EPSG:5781`).
3. **Corecții Diferențiale:** Serviciul național ROMPOS (stații permanente ANCPI, soluție `RTK_FIXED` cu precizie $\sigma_{XY} \le 1.5\text{ cm}$).
4. **Puncte Măsurate per Clădire:**
   * Fiecare colț exterior al soclului (fundației) la cota solului.
   * Pentru fiecare latură cu streașină proeminentă, se măsoară distanța orizontală de la fațadă la marginea jgheabului/streșinii ($d_{\text{streașină}}$) cu telemetru laser, notată în fișa de atribute `eave_measured_offset`.
5. **Format de Livrare:** Fișiere `.dxf` / `.geojson` / `.csv` procesate în TopoLT / Leica Geo Office.

---

## 3. Atribute Obligatorii per Entitate în Ground Truth

Fiecare poligon de referință din directorul `data/ground_truth/` trebuie să conțină următoarele atribute standardizate:

```json
{
  "id": "GT_CLUJ_001",
  "crs": "EPSG:3844",
  "survey_source": "RTK_SURVEY",
  "equipment": "Leica GS18 T GNSS RTK",
  "survey_date": "2026-08-15",
  "morphology": "L_SHAPE",
  "eave_measured_offset_m": 0.45,
  "h_cornisa_m": 6.2,
  "h_coama_m": 8.8,
  "regim_inaltime": "P+1E",
  "true_area_m2": 138.4
}
```

---

## 4. Porți de Calitate la Evaluare (Quality Gates)

* **Poarta ANCPI (Inspirată din toleranța de intravilan Ordinul 600/2023):**
  * $RMSE_{\text{boundary}} \le 0.10\text{ m}$
  * $IoU \ge 0.85$
  * $|\Delta \text{Arie}| \le 5.0\%$
* **Poarta PUG (Conformitate Urbanistică MDLPA Ordinul 904/2023):**
  * $RMSE_{\text{boundary}} \le 0.30\text{ m}$
  * $IoU \ge 0.70$
  * $|\Delta \text{Arie}| \le 10.0\%$
