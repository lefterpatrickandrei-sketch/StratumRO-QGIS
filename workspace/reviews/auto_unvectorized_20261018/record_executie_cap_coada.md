# StratumRO — Record Execuție Cap-Coadă (Full-Auto)

Data Rulării: 2026-10-18 18:07:50
Mediul de Rulare: Python 3.10.10 pe Windows, QGIS Desktop 3.40 Live Bridge.

## 1. Sumar Executiv de Performanță

| Metrică | Valoare Obținută |
|---|---|
| **Timp Total de Execuție** | **3.43 secunde** |
| **Număr Clădiri Noi Rectificate** | **264 corpuri unice** |
| **Viteza de Procesare** | **10.2 ms / clădire** (~98.0 clădiri/secundă) |
| **Coliziuni / Duplicate Prevenite** | **174 corpuri** (0 duplicate sau suprapuneri) |
| **Ortogonalitate Medie (90° Manhattan)** | **22.0% -> 97.3% (+75.2%)** |
| **Reducere Vârfuri Parazite** | **6175 -> 5415 noduri** |
| **Retragere Parametrică ANCPI** | **-0.40m mitre join** aplicată pe toate corpurile |
| **Statut Atribuit** | `PENDING_OWNER_REVIEW` |

## 2. Descompunerea Timpilor pe Faze (Cap-Coadă)

1. **Faza 1: Indexare Spatială Referințe (Lot 1..4):** 0.112 s
2. **Faza 2: Colectare Candidati Nevectorizați (Regional + Complex):** 0.068 s
3. **Faza 3: Deduplicare Spațială Strictă (STRtree zero-overlap):** 0.049 s
4. **Faza 4 & 5: Regularizare Ortogonală 90° & Retragere Sol:** 2.693 s
5. **Faza 6: Salvare GeoPackage & Raportare:** 0.503 s

## 3. Garanția Deduplicării Stricte & Zero Coliziuni

Au fost încărcate și verificate toate cele 7 surse istorice de corpuri create anterior:
- Lot 1: T01..T04
- Lot 2: T05..T10, Simple, Selectate, B5
- Lot 3: T11..T20 (20 corpuri canonice)
- Lot 4: T21..T30 (10 corpuri canonice)

Toate coliziunile au fost excluse atât pre-regularizare, cât și post-regularizare (prin cliping diferențial strict).
Niciun corp din Lot 1..4 nu este suprapus sau rescris.
Niciun corp nou nu se suprapune cu un corp vecin nou.

## 4. Straturi Generate în GPKG (`auto_unvectorized_orthogonal.gpkg`)

- `ROOF_HYPOTHESES_ORTHO90`: 264 clădiri cu unghiuri drepte
- `FOOTPRINT_HYPOTHESES_SOL`: 264 amprente la sol cu retragere canonică ANCPI -0.40m
- `RAW_CANDIDATES_BEFORE`: 264 măști brute pentru audit vizual
- `DEDUPLICATED_SKIPPED`: 174 candidate respinse prin deduplicare
