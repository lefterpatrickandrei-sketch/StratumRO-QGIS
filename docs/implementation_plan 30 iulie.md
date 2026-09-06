# Audit Algoritmi & Prompt de Actualizare Documentație

## Partea 1 — Audit Algoritmi Aleși vs. Alternative 2026

### 🧠 1. Meta SAM 2 (Segmentare Clădiri)

| Criteriu | SAM 2 (ales) | SAM 3 (alternativă) |
|----------|-------------|---------------------|
| **Paradigmă** | Prompt-based (puncte, box-uri) | Concept-based (text, exemplare, multimodal) |
| **Precizie clădiri** | ✅ Excelentă — pixel-accurate cu box prompts | 🟡 Bună — dar optimizată pt batch, nu precizie |
| **Integrare LiDAR** | ✅ Prompt spatial din nDSM → box prompts | ⚠️ Text prompts, nu utilizează direct nDSM |
| **Rulare locală** | ✅ Ollama/CUDA, stabil | 🟡 Mai nou, suport local mai slab |
| **Workflow cadastral** | ✅ Human-in-the-loop refinement | 🟡 Batch discovery, mai puțin control |

> [!TIP]
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

> [!TIP]
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

> [!TIP]
> **Verdict Ortogonalizare §5.3: ✅ ALEGERE CORECTĂ** pentru stadiul actual. Algoritmul de minimizare unghiulară descris în readme este solid matematic. Frame Field Learning ar fi un upgrade viitor.

---

### 🏔️ 4. Depth Anything V2 (Estimare Monoculară — Etapa 88 Experimentală)

| Criteriu | Depth Anything V2 (ales) | Metric3D (alternativă) |
|----------|-------------------------|----------------------|
| **Tip output** | Adâncime relativă (nu metrică!) | ✅ Adâncime metrică zero-shot |
| **Detaliu vizual** | ✅✅ Excelent — fine-grained | 🟡 Bun, dar mai puțin detaliat |
| **Acuratețe înălțime clădiri** | ⚠️ Necesită calibrare externă | ✅ Mai bun pt valori absolute |
| **Uz cadastral** | ⚠️ Erori >1.5m (experimental) | 🟡 Erori ~0.5-1.0m (tot experimental) |

> [!WARNING]
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

> [!TIP]
> **Verdict PDAL + laspy: ✅ ALEGERE PERFECTĂ**. Sunt complementare, nu concurente. PDAL pt pipeline automat, laspy pt acces granular.

---

## Partea 2 — Rezumat Audituri

| # | Componentă | Ales | Verdict |
|---|-----------|------|---------|
| 1 | Segmentare | Meta SAM 2 | ✅ Corect |
| 2 | LLM Orchestrator | NVIDIA Nemotron-3 | ✅ Corect |
| 3 | Ortogonalizare | Minimizare unghiulară 90° | ✅ Corect |
| 4 | Estimare monoculară | Depth Anything V2 | ⚠️ Schimbați cu Metric3D sau păstrați ca experimental |
| 5 | Procesare LiDAR | PDAL + laspy | ✅ Perfect |

---

## Partea 3 — Prompt de Execuție pentru Actualizare Documentație

> [!IMPORTANT]
> Copiază prompt-ul de mai jos și trimite-l agentului de execuție. Acesta va actualiza `readme.md` și `architecture.md` cu cele 7 funcționalități noi + recomandările de algoritmi.

```
Ești un inginer de documentație tehnică GIS care actualizează proiectul StratumRO-QGIS.

## Context
Proiectul StratumRO are 100 de etape (Fazele A-K). Fazele A-C (Etapele 1-40) sunt finalizate. Am făcut un audit comparativ cu proiecte similare (Geo-SAM, Deepness, AI Segmentation, Mapflow, Regularize Building Footprints) și un audit al algoritmilor aleși. Trebuie să actualizez documentația cu concluziile.

## Sarcini

### Sarcina 1: Actualizare `docs/readme.md`

**1A. Secțiunea §5.1 (linia ~534) — Actualizare titlu Stereo 70**
- Schimbă `(Stereo 70 / EPSG:31700)` → `(Stereo 70 / EPSG:3844 ANCPI & EPSG:31700 Legacy)`

**1B. Secțiunea §1.1 (linia ~47-49) — Adaugă mențiunea SAM 3 hibrid**
- La sfârșitul paragrafului care menționează "Meta SAM2", adaugă o propoziție:
  "Pipeline-ul suportă opțional un flux hibrid SAM 3 → SAM 2 (SAM 3 pentru descoperirea automată a clădirilor, SAM 2 pentru rafinarea pixel-level a contururilor)."

**1C. Etapa 88 (linia ~924) — Actualizare model experimental**
- Schimbă descrierea din `Depth Anything V2` → `Metric3D (sau Depth Anything V2 ca alternativă)`
- Asigură-te că menține statusul `🧪 Cercetare / Experimental`

**1D. După Faza C (după linia 841) — Adaugă notă nouă**
Adaugă un bloc text între Faza C și Faza D:

```markdown
> **📌 Notă Audit Comparativ (Iulie 2026):** Din analiza proiectelor similare (Geo-SAM, Deepness, Mapflow, AI Segmentation TerraLab), au fost identificate următoarele funcționalități suplimentare necesare pe partea de client QGIS (Membru 1):
> 1. **Regularizare contururi clădiri** (ortogonalizare colțuri 90° — se integrează la Etapa 72)
> 2. **Validare topologică automată** (eliminare suprapuneri/goluri — se integrează la Etapa 74)
> 3. **Bară de progres vizuală QProgressBar** (conectată la polling — extensie Etapa 40)
> 4. **Selecție AOI multi-metodă** (poligon liber + selecție feature — extensie Etapa 34)
> 5. **Preview rezultat în dockwidget** (thumbnail segmentare — extensie Etapa 36)
> 6. **Selecție model AI din UI** (dropdown model + prag confidență — extensie Etapa 66)
> 7. **Istoric procesări / Session Log** (jurnal JSON persistent — funcționalitate nouă)
```

### Sarcina 2: Actualizare `docs/architecture.md`

**2A. Adaugă secțiune nouă la final:**

```markdown
---

## 3. Algoritmi & Modele AI Validate

| Componentă | Model Ales | Alternativă Evaluată | Verdict |
|------------|-----------|---------------------|---------|
| Segmentare Clădiri | Meta SAM 2 | SAM 3 (batch discovery) | ✅ SAM 2 — precizie pixel cu prompt spatial LiDAR |
| Orchestrator LLM | NVIDIA Nemotron-3 (Ollama) | Llama 4 Maverick/Scout | ✅ Nemotron-3 — raționament agentic superior |
| Ortogonalizare | Minimizare unghiulară 90° | Frame Field Learning | ✅ Suficient pt clădiri standard ANCPI |
| Estimare Monoculară | Depth Anything V2 | Metric3D | ⚠️ Metric3D recomandat — oferă adâncime metrică |
| Procesare LiDAR | PDAL + laspy | - | ✅ Complementare — PDAL pipeline + laspy acces date |
```

**2B. Actualizare descriere secțiunea 1 (linia ~10):**
Asigură-te că textul introductiv menționează dual CRS (EPSG:3844 / EPSG:31700) și Marea Neagră 1975 (EPSG:5781).

### Reguli
- Păstrează TOATE comentariile și textele existente neschimbate (nu șterge nimic)
- Doar ADAUGĂ sau MODIFICĂ textele specificate
- Nu modifica structura Mermaid diagrams
- Raportează un rezumat al tuturor modificărilor la final
```

---

## Partea 4 — Ce Feedback Așteptăm

După executarea promptului, verifică:
1. ✅ / ❌ pentru fiecare din cele 5 sarcini (1A, 1B, 1C, 1D, 2A, 2B)
2. Readme-ul compilează corect (fără Markdown broken)
3. Tabelul de algoritmi din architecture.md se afișează corect
