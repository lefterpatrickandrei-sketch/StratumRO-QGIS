# StratumRO — Pachet de Cercetare & Sinteză Tehnică pentru Gemini Notebook / NotebookLM

## 1. Identitate & Viziune Proiect
**StratumRO** este o platformă industrială de geomatică și MLOps orientată către fluxurile de lucru românești de **pre-cadastru asistat (Human-in-the-Loop)**.
- **Scop:** Accelerarea digitizării manuale cu ~89% prin detecție semiautomată, regularizare geometrică la 90° și generare de livrabile compatibile cu specificațiile ANCPI și TopoLT.
- **Poziționare Legală:** StratumRO nu înlocuiește persoana autorizată ANCPI. Orice înregistrare cadastrală oficială necesită verificarea și semnătura unui inginer geodez autorizat.

---

## 2. Standarde Juridice & Geodezice Românești

### 2.1 ANCPI Ordinul nr. 600/2023 & Convenții CAD TopoLT
Platforma exportă fișiere DXF structurate pe straturi standardizate:
- `1CC`: Conturul construcțiilor principale (clădiri de locuit, birouri, etc.).
- `2CC`: Construcții anexe (garaje, magazii, dependințe).
- `CP`: Limita corpurilor de proprietate / parcelelor cadastrale.
- `VARFURI`: Punctele de inflexiune / colțurile poligoanelor înregistrate ca entități punctiforme.
- `NUMERE_PCT`: Textele ce conțin numerotarea canonică a punctelor pe contur (sens orar).

### 2.2 Proiecția Națională Stereo 70 (EPSG:3844)
- Toate calculele geometrice (coordonate $X, Y$, suprafețe, perimetre) rulează pe motoare deterministe (PROJ, GDAL, GEOS, Shapely).
- **Regulă Zero-Hallucination:** Niciun model de limbaj (LLM) nu are permisiunea să modifice sau să inventeze coordonate metrice. Modelele LLM se ocupă exclusiv de raționament, clasificare și audit.

### 2.3 Tabelul de Coordonate PAD & Fișierele de Schimb `.CP`
- Generare automată a tabelului de coordonate pentru Planul de Amplasament și Delimitare (PAD).
- Generarea fișierelor de schimb `.CP` recunoscute de software-ul cadastral românesc.

---

## 3. Arhitectura de Inteligență Artificială & Hardware Local

### 3.1 Hardware Detectat
- **GPU:** NVIDIA GeForce RTX 4050 Laptop (6 GB VRAM, arhitectură Ada Lovelace, Compute 8.9).
- **CUDA Runtime:** 12.4 (integrat în PyTorch `2.6.0+cu124`).

### 3.2 Modele Locale Active
1. **Meta SAM 2 (Segment Anything Model 2 - Hiera Tiny):**
   - Checkpoint local: `models/sam2/sam2_hiera_tiny.pt` (149 MB).
   - Execuție directă pe GPU RTX 4050 prin PyTorch CUDA.
   - Rol: Delineare optică a contururilor acoperișurilor pornind de la casete de delimitare (bounding boxes) și puncte interioare.
2. **Fuziune Hibridă LiDAR nDSM + Optică SAM 2:**
   - Pre-filtrare pe baza datelor LiDAR clasificate (ASPRS Clasa 6 - Clădiri).
   - Verificare dublă:
     - Înălțime certă: $H_{mean} \ge 2.5\text{ m}$ și $H_{max} \ge 3.0\text{ m}$.
     - Scadere optică de încredere SAM 2: scor $\ge 0.60$.
3. **Modele VLM Locale (Ollama):**
   - `minicpm-v:8b` (5.5 GB): VLM modern pentru evaluarea vizuală a ortofotourilor și verificarea integrității acoperișurilor.
   - `llava:13b` (8.0 GB): Model vision de rezoluție înaltă pentru auditul vizual al geometriei.
4. **Modele LLM Locale de Raționament (Ollama):**
   - `qwen3-agent:8b` (5.2 GB): Model agentic pentru planificare, task graphs și orchestrare pași.

---

## 4. Date Geospatiale Deschise & Catalogul Național

Sistemul integrează date oficiale românești prin servicii WMS/WFS și fișiere vectoriale:
1. **ANCPI (Agenția Națională de Cadastru și Publicitate Imobiliară):**
   - Limite administrative UAT.
   - Nomenclatorul stradal RENNS (adrese și numere poștale).
2. **APIA (Agenția de Plăți și Intervenție pentru Agricultură):**
   - LPIS 2025: Blocurile fizice agricole.
3. **ANAR (Apele Române):**
   - Hărți de hazard și risc la inundații (scenariul T100).
4. **Ministerul Mediului & EEA (European Environment Agency):**
   - Natura 2000: Arii de Protecție Specială Avifaunistică (SPA) și Situri de Importanță Comunitară (SCI).
5. **cIMeC / Institutul Național al Patrimoniului:**
   - Repertoriul Arheologic Național (RAN) și zone de protecție a monumentelor.
6. **Infrastructură de Transport:**
   - CNAIR (drumuri naționale și autostrăzi) & CFR (rețeaua feroviară).

---

## 5. Ghid de Cercetare & Întrebări pentru NotebookLM

Când interoghezi NotebookLM pe baza acestui document, iată principalele teme pe care le poți analiza:

1. **Optimizarea fluxului de digitizare:**
   - *„Cum reduce fuziunea dintre LiDAR nDSM și SAM2 rata de fals-pozitive la detectarea clădirilor?”*
2. **Conformitatea cu Ordinul 600/2023:**
   - *„Care sunt atributele și convențiile CAD cerute de TopoLT pentru stratul 1CC vs 2CC?”*
3. **Evaluarea constrângerilor de urbanism (PUG / RLU):**
   - *„Cum pot fi corelate parcelele pre-cadastrale cu zonele de hazard la inundații ANAR sau ariile protejate Natura 2000?”*
4. **Gestiunea resurselor locale:**
   - *„Care este rolul modelului MiniCPM-V 8B în comparație cu inferența SAM2 Tiny pe un GPU de 6 GB VRAM?”*
