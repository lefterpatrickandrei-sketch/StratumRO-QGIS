# Audit Algoritmi & Plan de Implementare — 30 Iulie 2026

## Partea 1 — Audit Algoritmi Aleși vs. Alternative 2026

### 🧠 1. Meta SAM 2 (Segmentare Clădiri)

| Criteriu | SAM 2 (ales) | SAM 3 (alternativă) |
|----------|-------------|---------------------|
| **Paradigmă** | Prompt-based (puncte, box-uri) | Concept-based (text, exemplare, multimodal) |
| **Precizie clădiri** | ✅ Excelentă — pixel-accurate cu box prompts | 🟡 Bună — dar optimizată pt batch, nu precizie |
| **Integrare LiDAR** | ✅ Prompt spatial din nDSM → box prompts | ⚠️ Text prompts, nu utilizează direct nDSM |
| **Rulare locală** | ✅ Ollama/CUDA, stabil | 🟡 Mai nou, suport local mai slab |
| **Workflow cadastral** | ✅ Human-in-the-loop refinement | 🟡 Batch discovery, mai puțin control |

> **Verdict SAM 2: ✅ ALEGERE CORECTĂ** pentru StratumRO. SAM 2 este superior pentru precizie pixel-level cu prompt-uri spațiale din LiDAR (nDSM → bounding box). SAM 3 ar fi util ca pre-procesare batch, dar nu ca nucleu principal.
>
> **Recomandare hibridă**: Menționați în documentație posibilitatea unui pipeline SAM 3 → SAM 2 (SAM 3 pentru discovery automat, SAM 2 pentru refinement precis).

---

### 🤖 2. NVIDIA Nemotron-3 (LLM Orchestrator)

| Criteriu | Nemotron-3 (ales) | Llama 4 (alternativă) |
|----------|-------------------|----------------------|
| **Raționament agentic** | ✅ Superior — hybrid latent MoE, anti-goal-drift | 🟡 Bun, dar mai puțin stabil pe loops lungi |
| **Context window** | 1M tokens | 1M (Maverick) – 10M (Scout) |
| **Multimodal** | ⚠️ Text-only | ✅ Nativ multimodal (viziune + text) |
| **Rulare Ollama** | ✅ Suportat (Super 120B MoE) | ✅ Suportat nativ |
| **Orchestrare MCP** | ✅ Optimizat pt tool calling precis | 🟡 Bun, dar mai puțin specializat |

> **Verdict Nemotron-3: ✅ ALEGERE CORECTĂ** pentru orchestrarea MCP a pipeline-ului. Raționamentul multi-step precis este critic pentru coordonarea segmentare → curățare → validare.
>
> **Recomandare**: Adăugați Llama 4 Scout (10M context) ca opțiune viitoare dacă agenții vor trebui să ingestioneze documentații ANCPI masive.

---

### 📐 3. Ortogonalizare Colțuri Clădiri (Post-procesare)

| Criteriu | Douglas-Peucker (simplu) | Ortogonalizare 90° (ales în readme §5.3) | Frame Field Learning (nou 2025-2026) |
|----------|--------------------------|------------------------------------------|--------------------------------------|
| **Calitate colțuri** | ❌ Zigzag, nu forțează 90° | ✅ Forțează unghiuri de 90° | ✅✅ Învață orientarea dominantă, adaptiv |
| **Clădiri complexe** | ❌ | ⚠️ Probleme cu forme C/Y/circulare | ✅ Gestionează forme neregulate |
| **Implementare** | Trivială (QGIS nativ) | Moderată (`native:orthogonalize`) | Complexă (necesită antrenare model) |
| **Cadastru ANCPI** | ❌ Insuficient | ✅ Suficient pt clădiri standard | ✅✅ Ideal dar overkill acum |

> **Verdict Ortogonalizare §5.3: ✅ ALEGERE CORECTĂ** pentru stadiul actual. Algoritmul de minimizare unghiulară descris în readme este solid matematic. Frame Field Learning ar fi un upgrade viitor.

---

### 🏔️ 4. Depth Anything V2 (Estimare Monoculară — Etapa 88 Experimentală)

| Criteriu | Depth Anything V2 (ales) | Metric3D (alternativă) |
|----------|-------------------------|----------------------|
| **Tip output** | Adâncime relativă (nu metrică!) | ✅ Adâncime metrică zero-shot |
| **Detaliu vizual** | ✅✅ Excelent — fine-grained | 🟡 Bun, dar mai puțin detaliat |
| **Acuratețe înălțime clădiri** | ⚠️ Necesită calibrare externă | ✅ Mai bun pt valori absolute |
| **Uz cadastral** | ⚠️ Erori >1.5m (experimental) | 🟡 Erori ~0.5-1.0m (tot experimental) |

> **Verdict Depth Anything V2: ⚠️ PARȚIAL CORECT**. Pentru uz cadastral, Metric3D este superior deoarece oferă adâncime metrică (nu relativă). Depth Anything V2 este excelent vizual dar necesită calibrare cu LiDAR real — ceea ce face LiDAR-ul deja obligatoriu, deci monocularul devine redundant.
>
> **Recomandare**: Documentați clar în readme că Etapa 88 este **experimental** și că sursa principală de altimetrie rămâne **LiDAR LAKI** (Etapa 89). Dacă se adaugă monocular, folosiți **Metric3D** nu Depth Anything V2 pentru valori absolute.

---

### 📡 5. PDAL + laspy (Procesare LiDAR — Faza E)

| Criteriu | PDAL (ales) | laspy (ales) |
|----------|-------------|-------------|
| **Rol** | Pipeline procesare: filtrare, clasificare, reproiecție | Acces date: citire/scriere LAS/LAZ, NumPy |
| **Ground filtering** | ✅ SMRF, CSF built-in | ❌ Nu are filtre |
| **Scalabilitate** | ✅ Out-of-core, paralelizat | ⚠️ Memory-bound |
| **Complementare** | ✅ | ✅ |

> **Verdict PDAL + laspy: ✅ ALEGERE PERFECTĂ**. Sunt complementare, nu concurente. PDAL pt pipeline automat, laspy pt acces granular.

---

## Partea 2 — Rezumat Audituri & Decizii de Proiect

| # | Componentă | Ales | Verdict | Status Implementare |
|---|-----------|------|---------|---------------------|
| 1 | Segmentare | Meta SAM 2 | ✅ Corect | Documentat în readme & architecture.md |
| 2 | LLM Orchestrator | NVIDIA Nemotron-3 | ✅ Corect | Documentat în readme & architecture.md |
| 3 | Ortogonalizare | Minimizare unghiulară 90° | ✅ Corect | Documentat în readme §5.3 |
| 4 | Estimare Monoculară | Depth Anything V2 → Metric3D | ⚠️ Metric3D recomandat | Actualizat în Etapa 88 (Experimental) |
| 5 | Procesare LiDAR | PDAL + laspy | ✅ Perfect | Documentat în architecture.md |

---

## Partea 3 — Cele 7 Funcționalități Noi Identificate din Proiecte Similare

| Nr. | Funcționalitate | Etapă asociată | Descriere |
|---|----------------|---------------|-----------|
| 1 | **Regularizare contururi clădiri** | Etapa 72 | Ortogonalizare unghiuri la 90° și simplificare poligoane |
| 2 | **Validare topologică automată** | Etapa 74 | Eliminare suprapuneri și goluri conform standardelor ANCPI |
| 3 | **Bară de progres vizuală QProgressBar** | Extensie Etapa 40 | Progres real 0-100% în UI conectat la polling async |
| 4 | **Selecție AOI multi-metodă** | Extensie Etapa 34 | Suport poligon liber + selecție din strat vectorial existent |
| 5 | **Preview rezultat în dockwidget** | Extensie Etapa 36 | Thumbnail vizual al segmentării în interfața plugin-ului |
| 6 | **Selecție model AI din UI** | Extensie Etapa 66 | Dropdown model + prag confidență configurabil din interfață |
| 7 | **Istoric procesări / Session Log** | Funcționalitate nouă | Jurnal JSON/CSV persistent cu istoricul procesărilor per proiect |
