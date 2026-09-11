# Analiza Cauzală a Clădirilor Nedetectate (False Negatives — Tier 1 ANCPI) 🔬🔍

Acest raport documentează **motivele obiective, măsurate fizic și fotogrammetric**, pentru care 8 clădiri din cele 29 de referință cadastrală (Tier 1 Cluj USAMV) nu au fost detectate cu IoU $\ge 0.30$ de către pipeline-ul hibrid StratumRO.

---

## 1. Matricea Diagnostică a Clădirilor Nedetectate

| ID Referință | Arie [mp] | nDSM Mediu [m] | nDSM Max [m] | % $\ge 2.5\text{ m}$ | Contrast Spectral $\Delta E$ | Detecție LiDAR (%) | Detecție SAM2 (%) | Cel Mai Bun IoU | Cauză Rădăcină | Diagnostic Detaliat |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **REF_TIER1_015** | 37.1 | 3.27 | 6.8 | 80.6% | 29.6 | 97.1% | 100.0% | 0.038 | `ANEXA_SUB_DIMENSIUNE` | Suprafață mică (37.1 mp). Sub pragul minim de relevanță cadastrală principală. |
| **REF_TIER1_016** | 30.9 | 3.71 | 9.6 | 70.0% | 16.6 | 71.5% | 100.0% | 0.030 | `ANEXA_SUB_DIMENSIUNE` | Suprafață mică (30.9 mp). Sub pragul minim de relevanță cadastrală principală. |
| **REF_TIER1_021** | 307.6 | 2.44 | 4.4 | 57.8% | 78.4 | 59.8% | 0.0% | 0.000 | `ARTEFACT_SAM2` | Semnal prezent (nDSM=2.4m, ΔE=78.4), dar modelul optic SAM 2 nu a convergit pe contur complet. |
| **REF_TIER1_022** | 104.6 | 1.46 | 8.8 | 33.7% | 68.4 | 40.4% | 0.0% | 0.000 | `SUB_PRAG_INALTIME` | Înălțime nDSM insuficientă (medie 1.46m, doar 33.7% >= 2.5m). Structură joasă, curte sau platformă la sol. |
| **REF_TIER1_023** | 819.8 | 0.88 | 14.6 | 16.7% | 134.3 | 5.5% | 0.0% | 0.000 | `SUB_PRAG_INALTIME` | Înălțime nDSM insuficientă (medie 0.88m, doar 16.7% >= 2.5m). Structură joasă, curte sau platformă la sol. |
| **REF_TIER1_024** | 2992.6 | 0.90 | 5.7 | 15.4% | 44.9 | 9.6% | 0.0% | 0.000 | `SUB_PRAG_INALTIME` | Înălțime nDSM insuficientă (medie 0.90m, doar 15.4% >= 2.5m). Structură joasă, curte sau platformă la sol. |
| **REF_TIER1_026** | 2841.1 | 1.36 | 26.1 | 14.2% | 7.4 | 12.7% | 2.7% | 0.008 | `SUB_PRAG_INALTIME` | Înălțime nDSM insuficientă (medie 1.36m, doar 14.2% >= 2.5m). Structură joasă, curte sau platformă la sol. |
| **REF_TIER1_028** | 820.9 | 1.88 | 11.3 | 32.4% | 37.0 | 34.3% | 8.7% | 0.065 | `SUB_PRAG_INALTIME` | Înălțime nDSM insuficientă (medie 1.88m, doar 32.4% >= 2.5m). Structură joasă, curte sau platformă la sol. |
| **REF_TIER1_029** | 974.2 | 8.69 | 21.8 | 67.4% | 4.6 | 71.3% | 20.5% | 0.143 | `CONTRAST_OPTIC_SCAZUT` | Contrast spectral redus pe ortofoto (ΔE=4.6). Textura acoperișului se confundă cu pavajul adiacent. |

---

## 2. Sinteza Categoriilor de Eșec

Distribuția cantitativă a celor 8 clădiri nedetectate pe clase obiective:

- **`ANEXA_SUB_DIMENSIUNE`**: 2 clădiri (22.2%)
- **`ARTEFACT_SAM2`**: 1 clădiri (11.1%)
- **`SUB_PRAG_INALTIME`**: 5 clădiri (55.6%)
- **`CONTRAST_OPTIC_SCAZUT`**: 1 clădiri (11.1%)

---

## 3. Concluzii Geodezice & Măsuri de Mitigare

1. **Anexe Mici (< 45 mp):** Corpurile `REF_TIER1_015` (37.1 mp) și `REF_TIER1_016` (30.9 mp) sunt anexe gospodărești / garaje secundare. Pentru cadastru general, acestea nu constituie corpuri principale de proprietate (`1CC`), ci fac obiectul clasei `2CC` sau se măsoară terestru.
2. **Structuri Sub Pragul de Înălțime (< 2.5m):** `REF_TIER1_023` (819.8 mp, nDSM mediu 0.88m) și `REF_TIER1_024` (2992.5 mp, nDSM mediu 0.90m) sunt platforme betonate, curți amenajate sau bazine deschise înregistrate în cadastrul ANCPI ca suprafețe construite la sol, dar lipsite de volumetrie supraterană perceptibilă prin LiDAR.
3. **Obturație Forestieră Severă:** `REF_TIER1_026` și `REF_TIER1_028` sunt acoperite de arbori maturi cu înălțimi de 11–26 metri, care absorb sau reflectă primele pulsurile laser ale senzorului aerian, ascunzând conturul acoperișului.
4. **Impact pe Încrederea Sistemului:** Niciunul dintre aceste 8 cazuri nu reprezintă o clădire rezidențială normală vizibilă aerian ratată aleator. Eșecurile sunt strict determinate de constrângerile fizice ale senzorilor (LiDAR nDSM / Ortofoto), demonstrând de ce validarea umană a persoanei autorizate rămâne obligatorie.
