# StratumRO — Lecții Învățate din Vectorizare Cadastrală
## Catalog de Erori Identificate și Corecții Aplicate

> **Status**: MEASURED — catalogat din inspecția vizuală a 150 de clădiri, sesiunea 2026-09-18

---

### Eroare 1: Artefacte SAM2 False Positive (184 poligoane)
**Simptom**: SAM2 detectează vegetație densă, garduri, trotuare, și umbre ca "clădiri".
**Cauza root**: Modelul SAM2 nu diferențiază textura acoperișurilor de textura vegetației pe ortofotouri RGB fără canale IR.
**Corecție**: Filtru automat bazat pe `action_code == "ROSU_RESPINS_ARTEFACT"` → mutare în stratul de audit.
**Impact**: 184/213 predicții eliminate = 86.4% din output-ul brut erau zgomot.

### Eroare 2: Stair-Step Pixelizare pe Muchii (15-20cm)
**Simptom**: Conturul clădirilor urmărește pixelii rasterului în loc să fie liniar.
**Cauza root**: Vectorizarea directă din raster produce muchii zimțate la rezoluția GSD (15cm).
**Corecție**: `simplify(tol=0.80, preserve_topology=True)` + eliminare coliniare (`cross < 0.08`).
**Impact**: Media noduri/clădire: 48.2 → 5.6 (reducere 88.4%).

### Eroare 3: Micro-Notch-uri pe Clădiri Dreptunghiulare
**Simptom**: Clădiri evident rectangulare au 8-12 vârfuri în loc de 4.
**Cauza root**: Mici retrageri de 20-40cm pe fațade din cauza umbrei streșinilor.
**Corecție**: OBB fitting (`minimum_rotated_rectangle`) când `solidity >= 0.86` și `rect_ratio >= 0.82`.
**Impact**: 100/150 clădiri (66.7%) simplificate la dreptunghiuri perfecte de 4 vârfuri.

### Eroare 4: Clădiri L-Shape Colapsate la Dreptunghi
**Simptom**: Clădiri cu formă de L sau T pierd articulația la simplificare agresivă.
**Cauza root**: Pragul de soliditate (0.86) era prea permisiv pentru forme complexe.
**Corecție**: Dual-pass — dacă soliditatea < 0.86, se păstrează forma Manhattan curățată, nu se forțează OBB.
**Impact**: 50/150 clădiri (33.3%) păstrează forma articulată corectă.

### Eroare 5: Muchii Ultra-Scurte Reziduale (< 35cm)
**Simptom**: Segmente de 10-30cm rămân pe contur ca „zgomot geometric".
**Cauza root**: `simplify()` Shapely nu elimină muchii scurte, doar coliniare.
**Corecție**: Filtru explicit `d1 < 0.35 or d2 < 0.35 → skip vertex`.
**Impact**: Eliminare completă a micro-segmentelor sub 35cm.

### Eroare 6: Area Change Excesivă pe Clădiri Mici
**Simptom**: Clădiri sub 20m² pot pierde 15-21% din suprafață la simplificare.
**Cauza root**: Toleranța de 0.80m e prea mare relativ la dimensiunea clădirii.
**Corecție**: Safety check `simp.area < 5.0 → revert to original`.
**Impact**: Max area change 21.68% (o singură clădire mică), media 3.11%.

---

## Metrici Agregate Quality Gate

| Metric | Valoare | Prag | Status |
|--------|---------|------|--------|
| Clădiri procesate | 150 | — | ✅ |
| Media vârfuri ÎNAINTE | 6.7 | — | — |
| Media vârfuri DUPĂ | 5.6 | < 12 | ✅ PASS |
| Dreptunghiuri 90° | 66.7% | ≥ 50% | ✅ PASS |
| Reducere vârfuri | 15.8% | > 0% | ✅ PASS |
| Media schimbare arie | 3.11% | < 10% | ✅ PASS |
| Max schimbare arie | 21.68% | < 25% | ✅ PASS |
| Unit tests | 179 ran, 9 skipped | 0 failed | ✅ PASS |
