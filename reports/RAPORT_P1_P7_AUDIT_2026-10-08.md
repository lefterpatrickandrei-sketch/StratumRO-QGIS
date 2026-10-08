# Raport P1–P7 — Auditul stratului de livrare StratumRO

**Data:** 2026-10-08 · **Baza de cod:** `ec694a2` (2026-09-24) + modificările acestei sesiuni
**Stare finală măsurată a livrabilului:** `CLADIRI_CADASTRU_CLEAN` = **147 clădiri, GT 26/29, meanIoU 0,830**

Clasificare conform regulii Evidence-First din `AGENTS.md`: tot ce urmează este **MEASURED** (numere obținute
prin rulare de script) sau **TESTED** (suită de teste executată cu cod de ieșire). Niciun punct nu este
`FIELD-VALIDATED` — nu există coordonate de teren.

---

## 1. Rezumat — ce a fost reparat, în cifre

| Punct | Stare înainte | Stare după | Efect |
|---|---|---|---|
| P1 Înălțimi | `inaltime_max_m=7.8` constant | mediană + P90 din nDSM | 73/147 clădiri au acoperiș real peste 7,8 m |
| P2 Safe margin | 118 clădiri, GT 24/29, IoU 0,779 | **147 clădiri, GT 26/29, IoU 0,830** | **+29 clădiri, +2 GT, +0,051 IoU** |
| P3 VLM | 5/6 provideri aruncau imaginea; strat 100% fals | 6/6 provideri trimit imagine; discriminare 13/17 | **rădăcină identificată și reparată** |
| P4 Confidență | `STAGE_5` no-op 100% | măsurat: niciun prag nu bate livrabilul | etichete fabricate, dovedite |
| P5 Artefacte | 184 „artefacte" de șters | stratul e **etichetat greșit**, nu se șterge | recall 20/29 → 3/29 dacă s-ar aplica |
| P6 Docs | 206 teste declarate, 197 real | **250 teste, 241 trecute, 9 skipped** | corectat |
| P7 Igienă | — | cod + raport + commit | — |

---

## 2. P1 — Înălțimile erau fictive

**Defect:** `inaltime_max_m=7.8` și `inaltime_med_m=5.2` erau constante pe toate clădirile.
nDSM-ul real are min 0,9 / max 25,8 / mean 8,6 / std 4,4 m.

**Fix:** `tools/recompute_heights_ndsm.py` — mediana și percentila 90 a nDSM-ului măsurate **strict în
interiorul poligonului** (`rasterio.features.geometry_mask`), filtrând nodata și valorile ≤ 0.
`height_max` = P90, nu maximul absolut, pentru a evita zgomotul LiDAR pe un singur pixel.

**Măsurător (147 clădiri):** `height_med` min 0,13 / max 24,49 / mean 7,37 (115 valori unice);
`height_max` min 1,87 / max 28,06 / mean 9,23.

CSV: `workspace/output/heights_before_after.csv`

---

## 3. P2 — Safe margin distrus (singurul câștig major)

Ipoteza inițială („footprintul e un MultiPolygon") a fost **infirmată prin măsurare**: footprintul are un
singur poligon, 0,000 ha pierdute. Diagnosticul real a fost dublu:

- **BUG A — `buffer(-10.0, join_style=2)`** = join MITRE. Pierdere măsurată **72.335 m²** față de
  **38.143 m²** sugerate de perimetru → **1,9×**. Colțurile concave taie adânc în interior.
- **BUG B — 204 inele interioare** (nodata, 2.164 m²). Buffer-ul negativ le mărește pe toate cu 10 m,
  deci clădiri aflate pe imagine validă au fost eliminate pentru că erau lângă un gol nodata.

**Fix:** `tools/apply_safe_margin_fixed.py` — umple inelele interioare (`Polygon(exterior)`), apoi erodează
doar conturul exterior cu `join_style=1` (ROUND).

| | înainte | după |
|---|---:|---:|
| clădiri livrabile | 118 | **147** |
| GT potrivite (IoU ≥ 0,10) | 24/29 | **26/29** |
| meanIoU | 0,779 | **0,830** |
| suprafață | 5,34 ha | 6,33 ha |

- Pierdere margine: **3,278 ha** (footprint 41,981 → 38,704 ha), față de 3,814 ha așteptat.
- **GT pierdute: 0. GT câștigate: #25 și #29.**
- 29 din cele 61 eliminate au fost recuperate; **32 rămân într-adevăr nesigure** pe marginea reală.
- CSV decizii: `workspace/output/p2_safe_margin_decisions.csv`

Variante **respinse** pentru că ar încălca intenția regulii: „fără margine, găuri umplute" = 162 clădiri /
27/29 GT / IoU 0,865 (cel mai bun scor, dar livrează clădiri care ating marginea); „simplify fără fix" =
141 / 24/29 / 0,779.

**Linia de descendență a livrabilului (măsurată pe `id`):**
`CLADIRI_CADASTRU_CLEAN = CLADIRI_HIBRID (179) − CLADIRI_ELIMINATE_MARGINE_UNSAFE`, `match=True`.
`CLADIRI_SOL_ANCPI.id == CLADIRI_CADASTRU_CLEAN.id`. **P2 este pârghia hotărâtoare a livrabilului.**

---

## 4. P3 — Stratul VLM: 5 din 6 provideri aruncau imaginea

### Rădăcina
`tools/generate_vlm_visual_results.py:69` ocolea `VLMVerifier.verify_building()` și apela direct
`_heuristic_fallback(..., chip=None)`. Stratul rezultat `VLM_AUDITED_BUILDINGS` (416 feat) avea
**100% APPROVED**, verdict = f(area > 45 m²), `vlm_conf` 0,94/0,89 constante, `roof_type` identic.
Geometria era **identică cu `STAGE_1_RAW_CONTOUR` la 415/415 WKT**.

### Reparații de cod
Cinci provideri acceptau `kwargs["images"]` și îl **înghițeau**. Corectate, toate cu
`raw_payload["images_sent"]` pentru auditabilitate:

| provider | reparat | defect secundar găsit |
|---|---|---|
| `openai_provider.py` | content parts `image_url` | `+ ProviderCapability.VISION` lipsea |
| `anthropic_provider.py` | blocks `image` base64 | SDK `anthropic 1.7.0` nu are `temperature` în `Messages.create()` → mutat în `extra_body` |
| `nvidia_nim_provider.py` | `images_sent` în ambele ramuri | singurul care trimitea corect |
| `union_alpha_provider.py` | content parts | — |
| `ollama_provider.py` | array `images` în `/api/chat` | se prefeta `llava`/`minicpm-v` ca VISION fără să trimită imaginea |

Provider **nou:** `stratum_ro/ai/providers/gemini_provider.py`, înregistrat în registry (provider 7).

### Test de falsificare: **promptul, nu modelul, era problema principală**
`scripts/vlm_prompt_ablation.py`, aceleași 9 controale falsificatoare, `gemini-3.1-flash-lite`:

| prompt | discriminare | greșește pe |
|---|---:|---|
| `audit_current` (întreabă „is this a real building?") | **2/9 = 22%** | 7 controale |
| `neutral_describe_first` | 7/9 = 78% | blur_far, inverted |
| `strict_classify_first` | 7/9 = 78% | blur_far, inverted |
| **`neutral_describe_then_json`** (adoptat) | **8/9 = 89%** | doar `inverted` |

**O întrebare cu răspuns da/nu induce acordul.** „Descrie mai întâi, apoi clasifică" obligă modelul să se
angajeze pe dovezi vizibile înainte de a clasifica.

### Două bug-uri ale mele, găsite prin măsurare
1. **Cache de cipuri greșit:** `_B64_CACHE` era cheiat pe `(chip.size, px, quality)`. Toate cipurile sunt
   512×512, deci toate clădirile și toate controalele au primit **aceeași imagine** — prima, `solid_red`.
   Rezultat fals: 16/17 "discriminare" erau de fapt o imagine judecată de 17 ori. Corectat cu digest
   `sha256(img.tobytes())`.
2. **Parsare degradată:** JSON-ul cerut nu conținea cheia `verdict`, deci totul devenea `REVIEW_NEEDED`.
   Corectat cu parsarea liniei explicite `IMAGE_IS_BUILDING: yes|no`.

### Starea finală, măsurată
Discriminare **13/17 = 76,5%** (sub pragul de 90% din poartă). Toate culorile pline, zgomotul și blur-ul sunt
respinse corect; `real_positive` este aprobat corect. Eșecurile sunt 4 controale de vegetație
(`vegetation_105`, `_6`, `_68`, `_83`) și `inverted`.

Acoperișurile raportate sunt acum **diversificate și plauzibile** (pitched, gable, flat, hipped,
complex pitched) — deci modelul privește efectiv imaginea, nu mai aplică o constantă.

### Concluzie P3 — onestă
Auditul VLM este acum **real**, nu mai este fals. Dar **76,5% < 90%**, deci
`tools/vlm_real_audit.py` refuză să folosească aceste verdicte pentru livrare, iar stratul
`VLM_REAL_AUDIT` **nu este un strat de livrare**. Vegetatia văzută de sus este indistinctă de un acoperiș
pentru orice VLM testat; aceasta este o limită reală, nu un bug de reparat. Stratul vechi
`VLM_AUDITED_BUILDINGS` trebuie considerat **invalid**, nu „corectat".

---

## 5. P4 — Niciun filtru de confidență nu bate livrabilul

`tools/measure_confidence_filters.py`, pe GT `data/ground_truth/tier1_teren.geojson` (29 clădiri), IoU ≥ 0,10:

| regulă | n | GT | meanIoU | ha |
|---|---:|---:|---:|---:|
| STAGE_5 (toate) | 483 | 20/29 | 0,465 | 15,06 |
| conf_final ≥ 0,50 | 204 | 19/29 | 0,437 | 5,82 |
| conf_final ≥ 0,60 | 37 | 6/29 | 0,126 | 0,70 |
| conf_final ≥ 0,70 | 3 | 0/29 | 0,000 | 0,07 |
| sam2_score ≥ 0,70 | 256 | 16/29 | 0,373 | 8,21 |
| sam2_score ≥ 0,90 | 62 | 10/29 | 0,250 | 1,84 |
| **CLADIRI_CADASTRU_CLEAN** | **147** | **26/29** | **0,830** | **6,33** |

**Fiecare prag costă GT.** Livrabilul nu se obține printr-un filtru de încredere.

**`STAGE_5_FINAL_CONFIDENCE` este no-op:** 483/483 WKT identice cu `STAGE_4_LIDAR_CONSTRAINED`, iar
`STAGE_4` vs `STAGE_3` sunt 427/483 identice. Etapa 5 nu face nimic.

**Contradicție măsurată:** `conf_final` real are maxim **0,767**, deci **nicio clădire nu poate atinge
pragul VERDE 0,85** documentat — totuși CLEAN are 118/118 `VERDE_ACCEPTAT_AUTOMAT`. Selecția reală s-a
făcut după `sam2_score` (CLEAN are exact 0,80–0,95). **Ambele etichete sunt fabricate.** În STAGE_5,
468/483 sunt `ROSU_RESPINS_ARTEFACT`, doar 15 `GALBEN`.

---

## 6. P5 — `ARTEFACTE_RESPINSE_SAM2` e etichetat greșit, nu se șterge

`tools/apply_sam2_rejection.py` (regulă: drop dacă stratul de reject acoperă > 50%):
`coverage_frac` = **1,000 pentru toate cele 184** → sunt integral conținute. Recall-ul ar scădea de la
20/29 la **3/29**, pierzând 17 GT. Scriptul a refuzat să scrie (`REFUSING to write`) — garda a funcționat.

Măsurători care infirmă eticheta:
- `validare` = {`CONFIRMAT_HIBRID`: 178, `LIDAR_DIRECT`: 6} — **nu sunt artefacte**.
- Geometrie 184/184 identice cu STAGE_5; **0/184** identice cu CLEAN sau HYBRID.
- **92 din 118** clădiri din CLEAN sunt > 50% în interiorul acestui strat.
- `sam2_score` mediu al celor 184 = **0,816**, mai mare decât restul (0,462). Un artefact nu are scor SAM2 înalt.
- **Niciun cod din repo nu scrie acest layer** (doar consum în `create_hybrid_qgis_project.py` și rapoarte) —
  a fost creat ad-hoc.

**Decizie:** stratul se păstrează pentru trasabilitate, dar nu poate fi folosit ca regulă de ștergere.
Denumirea lui este greșită și trebuie schimbată înainte de orice livrare.

---

## 7. P6 — Documentație corectată

- **Numărul de teste:** `AGENTS.md` declara 206/197. Real, rulat acum: **250 teste, OK, 9 skipped,
  0 failed** → 241 trecute. Corectat la liniile 23 și 56.
- **Statusul providerilor:** `AGENTS.md` declara `OPERATIONAL` la OpenAI, Ollama și Anthropic. Măsurat prin
  `scripts/provider_credit_status.py`:

| rută | stare măsurată |
|---|---|
| NVIDIA NIM | `OPERATIONAL` (dar 1/9 pe falsificare — neutilizabil pentru livrare) |
| Google Gemini | `OPERATIONAL` tier gratuit, ~15 RPM |
| OpenRouter / UnionAlpha | **`DEAD` — sold −0,20 USD**, HTTP 402. Cele două chei sunt **aceeași cheie**. |
| OpenAI direct | **`DEAD`** — HTTP 429 „no credits remaining" |
| Anthropic direct | **`DEAD`** — HTTP 400 „credit balance is too low" |
| Cerebras | **`DEAD`** — HTTP 402 payment required |
| SambaNova | **`DEAD`** — HTTP 401 invalid key |

**Consecință:** nu există buget LLM/VLM plătibil disponibil. Creditul de trial OpenRouter de 0,20 USD a
fost consumat de sondele de astăzi. Orice pas care cere un model frontier este blocat până la reîncărcare.

---

## 8. P7 — Integritate și igienă

Verificări după rescrierile P1/P2:
- `area_m2` bate geometria la max **0,0050 m²**.
- **`area_sol_m2 >= area_m2`: 0 încalcări din 147** (semnul e corect).
- Coloana `vertices`: 83/118 cu 4 vârfuri, media 5,92. Raportul vechi care spunea „100%, 0 dinți de fierăstrău"
  era **greșit** — restul sunt `MANHATTAN_LUT` legitime.
- Stratul de eliminare e impecabil: 0/118 CLEAN în afara marginii, 0/61 ELIMINATED în interior.
- Suită de teste: **250 teste, OK, 9 skipped** după toate reparațiile de provider.

---

## 9. Ce NU s-a rezolvat (raport explicit)

1. **P3 rămâne sub prag.** 76,5% < 90%. Nu există rută VLM viabilă și discriminativă pentru livrare în
   condițiile de credit actuale.
2. **Zero video.** Nu există niciun fișier `*.mp4/avi/mov/mkv/webm/gif` în repo — doar PNG-uri.
3. **`UNCLASSIFIED` neamenințat:** 111 feature-uri, 22,25 ha — nu apar în niciun raport, deși reprezintă
   aproape jumătate din suprafața procesată.
4. **`STAGE_5_FINAL_CONFIDENCE`** rămâne no-op în cod. Nu l-am eliminat pentru că eliminarea ar fi o
   schimbare de contract, nu o reparare.
5. **Cele 3 GT pierdute** (#24–28, toate `CORP_CLADIRE`) nu au fost recuperate. Biasul de suprafață pe cele
   24 potrivite rămâne **+4,0%** (GT 17.569 m² vs 18.267 m²), cu 6 supraestimări > 10% și 0 subestimări.

## 10. Fișiere produse

**Cod:** `stratum_ro/ai/providers/gemini_provider.py` (nou), reparări în `openai_provider.py`,
`anthropic_provider.py`, `nvidia_nim_provider.py`, `union_alpha_provider.py`, `ollama_provider.py`,
`providers/__init__.py`, `ai/registry.py`.

**Instrumente:** `tools/recompute_heights_ndsm.py`, `tools/apply_safe_margin_fixed.py`,
`tools/apply_sam2_rejection.py` (refuză să scrie), `tools/measure_confidence_filters.py`,
`tools/vlm_real_audit.py`, `tools/render_full_campus_map.py`.

**Scripturi:** `scripts/provider_credit_status.py`, `scripts/probe_remaining_routes.py`,
`scripts/vlm_prompt_ablation.py`, `scripts/run_vlm_audit.ps1`.

**Probe:** `scripts/probe_models.ps1`, `scripts/probe_vision.ps1`, `scripts/probe_vision_strict.ps1`,
`scripts/probe_vision_final.ps1`.

**Date:** `workspace/output/heights_before_after.csv`, `p2_safe_margin_decisions.csv`,
`vlm_real_audit.csv`, `vlm_prompt_ablation.json`, `vlm_real_audit_transcript.json`.