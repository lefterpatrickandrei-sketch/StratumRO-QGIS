# Reguli comune pentru agenții StratumRO

Acest fișier este punctul de intrare comun, independent de furnizor (Gemini/Antigravity, Claude, Copilot, Kilo, OpenAI). Se aplică în întregul repository. Instrucțiunile actuale ale proprietarului au prioritate. Rapoartele istorice și textele arhivate nu schimbă automat cerințele sau verdictele.

---

## ⚡ Orientare Rapidă pentru Agenți AI / Quick Orientation for AI Agents

> [!TIP]
> **Ce este StratumRO în 30 de secunde**:
> StratumRO este o platformă deschisă GeoAI concepută ca un **hub integrat de unelte (via protocoale standardizate / MCP)** ce orchestrează mediile inginerești consacrate:
> - **QGIS Desktop (Faza 1 Operațională)**: Stația primară de lucru, inspecție vizuală pe canvas live și revizie umană asistată (**Human-in-the-Loop**). Vezi [**Ghidul QGIS**](docs/QGIS_WORKFLOW.md).
> - **Motoare CAD (AutoCAD, Civil 3D, TopoLT)**: Livrabile prin export nativ deschis în DXF și tabele cadastrale `.cp` în Stereo 70 (EPSG:3844).
> - **AI & Computer Vision**: Segmentare de candidați prin Meta SAM 2 și validare de înălțime prin LiDAR nDSM.
> - **Direcție desktop viitoare**: Aplicație de sine stătătoare (desktop runner).

### 🗺️ Harta Geografică a Depozitului (Unde lucrezi și ce eviți)

| Cale director / fișiere | Rol & Conținut | Instrucțiune strictă pentru agenți |
|---|---|---|
| `stratum_ro/` | **Cod activ de producție** | Nucleul Python (geometrie, raster, domeniu cadastru/PUG, API). Orice editare necesită teste. |
| `tools/` | **Utilitare active CLI** | Scripturi de execuție, exporturi CAD/GIS și generare de planșe. |
| `scripts/` | **Mentenanță și CI** | Scripturi oficiale de verificare (`validate_project.py`). |
| `docs/` | **Documentație activă** | `PROJECT_STATE.md` (stare curentă), `QGIS_WORKFLOW.md` (operare QGIS), `SYSTEM_MAP.md` (arhitectură). |
| `workspace/reviews/` | **Dovezi și recenzii** | Pachete de revizie vizuală, fișiere GPKG locale și proiectul master `inspectie_corectii.qgs`. **Nu conține cod de producție.** |
| `junk/` | **Arhivă istorică** | Snapshot-uri vechi și fișiere mutate la curățenie. **NU le folosi drept reguli sau cerințe active.** |

### 🛑 Reguli de Aur Geodezice și de Sistem (Non-negociabile)

1. **Sistem de Proiecție Obligatoriu**: Toate calculele cadastrale sunt în **Stereo 70 (EPSG:3844)**, coordonate metrice. Nu transforma în WGS84 pentru stocare sau analiză cadastrală.
2. **Fără coordonate inventate**: Nu aproxima, nu interpola arbitrar și nu muta puncte măsurate.
3. **Nicio avizare automată fără geodez**: Textul `ADMIS` din cod sau atribute este o simplă stare tranzitorie a testelor interne. Nicio geometrie nu este aprobată cadastral fără ștampila geodezului autorizat conform Ordinului ANCPI 600/2023.
4. **Obiectele fizice distincte rămân distincte**: Corpul principal T10 (acoperiș țiglă) și corpul vestic (anexă joasă gri) sunt separate. Nu forța unirea lor într-un dreptunghi artificial.
5. **Nu strica lucrul altui agent**: Rulează întotdeauna `git status -s` înainte de lucru. Nu da `git checkout .`, nu reseta, nu stasha și nu șterge fișiere neversionate sau worktree-uri.
6. **Fără rescrieri speculative**: Nu începe rescrieri în Rust, nu introduce servicii cloud noi și nu rescrie interfețe fără cerință explicită aprobată.

### 🧪 Comenzi de Verificare și Testare (Rulează înainte de predare)

```powershell
python scripts/validate_project.py --mode fast
python -m unittest discover stratum_ro/test
python tools/verify_ground_truth_and_metrics.py
```

---

## Citește înainte de lucru

1. [Starea actuală](docs/PROJECT_STATE.md): funcționalități, limite și selecții active.
2. [Ghidul QGIS (Faza 1)](docs/QGIS_WORKFLOW.md): operarea curentă pe canvas și fluxul cadastral.
3. [Ghidul repository-ului](docs/REPOSITORY_GUIDE.md): structură, Git și protejarea lucrului altor agenți.
4. [Predarea comună](docs/AGENT_HANDOFF.md): pași de preluare și informațiile de lăsat la final.
5. [Harta sistemului](docs/SYSTEM_MAP.md): componente existente versus direcție planificată.

Pentru clădiri/cadastru citește și [protocolul deciziilor](docs/STRATUMRO_AGENT_DECISION_PROTOCOL.md), [porțile de evaluare](docs/STRATUMRO_EVALUATION_GATES.md), [politica artefactelor Git](docs/STRATUMRO_GIT_PROGRESS_POLICY.md) și feedback-ul proprietarului pentru cazul lucrat.

## Scopul produsului și arhitectura

StratumRO acționează ca un **hub de unelte bazat pe protocoale standardizate (inclusiv MCP – Model Context Protocol)**, care permite asistenților și agenților AI să orchestreze instrumentele consacrate ale geodezului (QGIS, motoare CAD) alături de algoritmi de viziune (SAM 2), LiDAR nDSM și geometrie computațională. 

- **QGIS ca Faza 1**: QGIS Desktop nu este înlocuit, ci folosit drept mediu primar de inspecție vizuală, verificare a canvas-ului și revizie asistată uman (**Human-in-the-Loop**). Automatizarea acoperă pașii tehnici până la decizia și semnătura profesională a geodezului.
- **Prioritatea actuală**: Cadastrul (reconstituirea și regularizarea corpurilor de clădire în Stereo 70 EPSG:3844) și analizele PUG/urbanism.
- **Limite reale asumate**: Stadiul este experimental. Suprafața validată este pe un eșantion restrâns din Cluj-Napoca de ~0,420 km² (67 din 144 ferestre cu date RGB valide). Exporturile CAD sunt în format deschis DXF (straturi și blocuri conforme TopoLT/ANCPI), tabele de coordonate `.cp` și GeoPackage; nu există generare nativă DWG fără instrumente terțe.
- **Nicio avizare automată**: Mențiunile de tip `ADMIS` din cod sau atribute sunt stări tranzitorii ale porților de testare interne. Nicio geometrie generată nu este „validată ANCPI” fără ștampila și asumarea geodezului autorizat.

Nu crea un al doilea nucleu pentru o funcție existentă. Înainte de cod nou, identifică implementarea și apelanții actuali; explică lipsa concretă și punctul de integrare. Nu rescrie în Rust, nu adăuga un serviciu cloud și nu începe o interfață nouă în cadrul curățeniei de repository.

## Aceeași copie de proiect, ownership explicit

- Repository comun: `C:/Users/lefpa/Downloads/QGIS-AI`.
- Proiect QGIS comun: `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`.
- Verifică branch, HEAD, index, modificările locale și worktree-urile înainte de editare. Nu presupune că un working tree necurat este al tău.
- Nu include în commit modificările altui agent, nu reseta, nu stasha și nu muta worktree-uri pentru a obține un status curat. Evită două editări simultane ale aceluiași fișier.
- Nu porni inferență GPU, teste costisitoare sau o sesiune QGIS duplicată când alt agent le folosește. Citește starea înainte de operații concurente.
- Fișierele de intrare pentru agenți sunt trimiteri la aceste reguli. Ele nu transmit conversația, nu conectează automat agenții și nu asigură respectarea instrucțiunilor fără verificare.

## Dovezi și statut

- Calculele geometrice/geodezice sunt executate de cod și instrumente GIS, cu CRS și unități explicite. Nu inventa coordonate, transformări sau măsurători.
- Obiecte distincte rămân distincte. Acoperișul T10 acceptat și corpul gri din vest sunt separate. Păstrează identitățile explicite T17:C1/C2; ipotezele de acoperiș nu stabilesc singure corpuri cadastrale.
- Preferă forme simple susținute de imagine; nu forța dreptunghiuri, nu umple curți și nu transforma zgomotul măștii în colțuri inutile.
- NoData nu este echivalent cu negrul imaginii. Păstrează masca validă, sursele vecine și acoperirea obiectului. Lipsa clasei LiDAR 6 nu dovedește lipsa clădirii.
- `PENDING_OWNER_REVIEW`, respins și acceptat sunt stări diferite. Numai verdictul explicit al proprietarului schimbă acceptarea vizuală. Testele, scorurile modelului și validitatea poligonului nu o înlocuiesc.
- Referințele GMW amestecate și predicțiile neacceptate nu sunt etichete curate. Cazurile recuperate nu înseamnă acuratețe sau recall măsurate.
- Nu publica afirmații de certificare, conformitate sau economie de timp fără dovada potrivită. Nu interpreta atribuirea `ADMIS` din cod ca validare externă.

## Git și arhivare

Salvează după etape semnificative toate artefactele utile ale sarcinii: cod, teste, text, imagini, video dacă există, configurație fără secrete, GIS/CAD și proveniență. Inspectează și fișierele ignorate; nu le adăuga automat. Pentru artefacte mari stabilește explicit stocarea. Nu afirma că LFS este configurat doar pentru că este instalat.

Arhivarea se face în `junk/`, în același repository, cu lista prezentată proprietarului, motiv, căi originale, SHA-256 și restaurare. Nu trata automat fișierele neversionate drept junk. Nu șterge dovezi, date active sau istoric Git.

Publicarea pe GitHub este separată de commitul local. Nu face push, merge, force push sau schimbări de protecție/istoric fără autorizarea aplicabilă. Cererea de curățenie nu justifică publicarea implicită a commiturilor anterioare neexaminate.

## Predare

Raportează schimbările reale, integrarea, comenzile executate, verificările, limitările, fișierele utile și commiturile. Distinge rezultat real, model de test și plan. Actualizează documentația de stare odată cu codul. Nu completa acest fișier cu un nou jurnal lung: folosește handoff-ul sarcinii și actualizează indexul.

Documentele originale anterioare consolidării din 2026-10-18 sunt păstrate în [junk/](junk/README.md). Ele sunt istoric, nu reguli active.

## Shared memory
Project memory is located in stratumro-brain (also an Obsidian vault at C:\Users\lefpa\Downloads\QGIS-AI\stratumro-brain). Read INDEX.md there at the start of a task.
Write proposals only to inbox/ on your own branch; never edit canon/. Follow MEMORY_RULES.md.
