# Preluare și predare comună între agenți

## La preluare

Deschide aceeași copie de repository și citește [AGENTS.md](../AGENTS.md), [PROJECT_STATE.md](PROJECT_STATE.md), [SYSTEM_MAP.md](SYSTEM_MAP.md) și documentul specializat al sarcinii. Confirmă local branch-ul, HEAD și modificările existente; nu te baza doar pe GitHub sau pe o conversație copiată.

Pentru rezultate GIS urmărește fișierul `CURRENT_SELECTION.json` ori `CURRENT_REVIEW.json` indicat în starea proiectului. Verifică sursa, hash-ul și verdictul, nu alege directorul cu nume cel mai optimist. Nu schimba acceptarea unui caz prin actualizarea unui raport de arhitectură.

Înainte de cod nou, caută simbolul, implementările similare, importurile și testele. Notează pe scurt: funcția deja existentă, lipsa observată și locul în care se integrează schimbarea. Dacă există două implementări, stabilește apelanții; nu construi o a treia pentru a ocoli consolidarea.

Un agent poate citi fișierele accesibile din proiect. Nu poate presupune acces la această conversație sau la istoricul privat al altor aplicații. Intrările CLAUDE/GEMINI/Kilo trimit la același contract; descoperirea și respectarea lui trebuie confirmate în fiecare client.

## În timpul lucrului

- Identifică fișierele proprii și evită editarea simultană a acelorași căi cu alt agent.
- Folosește capabilitățile existente QGIS, GDAL și bibliotecile proiectului înainte să reinventezi operația.
- Verifică resursele ocupate înainte de inferență sau teste costisitoare.
- Păstrează intrările, încercările nereușite utile și proveniența. Nu transforma lipsa datelor în dovadă negativă.
- Rulează verificările potrivite schimbării. Pentru documentație verifică legături, căi, hash-uri și diff; pentru cod verifică comportamentul și integrarea. Nu executa o inferență doar pentru o reorganizare de Markdown.
- Fă checkpoint după schimbările semnificative, cu toate artefactele utile proprii și fără secrete.

## La predare

Lasă un document datat în folderul dovezilor sarcinii și actualizează starea/indexul relevant. Predarea trebuie să răspundă la:

| Câmp | Conținut necesar |
|---|---|
| Cerință | Ce a autorizat proprietarul și ce rămâne de decis. |
| Integrare | Componenta existentă extinsă, apelantul și fișierele modificate. |
| Date | Surse, CRS, rezoluție, NoData, versiuni și hash-uri potrivite. |
| Execuție | Comenzi și parametri real executați; distinge model real, simulare și model de test. |
| Verificări | Rezultate exacte, dovezi vizuale dacă sunt relevante și limitele verificării. |
| Statut | Acceptat de proprietar, ipoteză, respins sau nerezolvat, explicit pentru cazurile vizate. |
| Git | Commituri locale, artefacte utile neincluse dacă există, publicare efectivă sau în așteptare. |
| Continuare | Probleme rămase și următorul pas concret, fără a pretinde că un plan este implementare. |

Nu copia întreaga conversație sau raționament intern în MD. Păstrează cerințele, criteriile observabile, deciziile și dovezile utile.

## Punctul de reluare după reorganizarea din 2026-10-18

Prima etapă arhivează 13 rapoarte, păstrează exact vechile intrări și unifică ghidurile. Codul produsului, proiectele QGIS, rezultatele și cele 16 modificări urmărite preexistente sunt protejate. [Dosarul etapei](../workspace/repository_cleanup_20261018/README.md) include inventarul și verificarea finală, când aceasta este încheiată.

Nu adopta automat cele 936 fișiere neversionate inventariate. Materialele arhitecturale locale și datele altor agenți necesită confirmarea provenienței și a stării înainte de consolidare. Proprietarul a aprobat ulterior publicarea progresului local în [draft PR #3](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/pull/3), fără merge; [rezultatul](../workspace/repository_cleanup_20261018/publication_result.json) și [inventarul rămas](../workspace/repository_cleanup_20261018/remaining_inventory.json) sunt versionate. Aceasta a fost aprobarea inițială. Proprietarul a autorizat ulterior explicit integrarea PR #3 în main după completarea și verificarea README-ului; [dosarul curent](../workspace/readme_publication_20261018/README.md) păstrează această autorizare. Nu extinde aprobarea la fișierele necomise ale altor agenți sau la modificarea istoricului. Urmează rezultatele CI și decizia asupra intervențiilor de cod, cu impactul prezentat proprietarului.

Continuarea CI a fost autorizată și implementată separat: vezi [dosarul CI](../workspace/ci_repair_20261018/README.md). Commitul `85a51ef` a trecut toate cele patru joburi, cu 459 teste fiecare și hash-urile originale păstrate. Jurnalele complete sunt versionate. Inițial versiunea nouă a fost publicată numai pe branch-ul `chore/stratumro-shared-checkpoint-20261018`. Integrarea este acum autorizată după verificări; verifică starea efectivă a PR #3 și remote main înainte de lucru, fără să tratezi snapshot-ul inițial drept stare live. Agenții locali trebuie să deschidă copia comună și să verifice HEAD, nu un worktree vechi.

## Ultimul checkpoint B, 2026-10-19

Cititi [predarea corectiilor locale](../workspace/option_b_repair_20261019/README.md) si selectorul comun CURRENT.json. In QGIS folositi B_CORECTII_20261019; nu confundati cele 152 propuneri cu rezultate acceptate. Cele 64 diagnostice sunt pastrate, nu reparate. Codul comun contine regulile, dar rutarea cazurilor din audit este o intrare manuala explicita.

## Ultimul checkpoint: Inspecție Fotogrammetrică 1:150 și Remediere Balansată (2026-10-19)

- **Audit & Verificare Sesiune Anterioară (`073958fc-f6cd-404a-b651-d8da605d64a6`)**:
  - A fost auditată și verificată rescrierea trilingvă a documentației (`README.md` în engleză, `README.ro.md` în română, `README.es.md` în spaniolă).
  - Ghidul operațional QGIS Desktop (`docs/QGIS_WORKFLOW.md`) a fost verificat și completat: clarifică rolul QGIS ca Faza 1 activă de inspecție vizuală și cockpit Human-in-the-Loop, integrat cu puntea MCP pe portul 9876 și exporturile CAD conforme ANCPI Ordinul 600/2023.
  - S-a verificat integritatea a peste 163 de legături locale Markdown: **0 legături rupte**.
  - `AGENTS.md` a fost consolidat cu secțiunea „Orientare Rapidă pentru Agenți AI”, harta directoarelor și regulile de aur geodezice (Stereo 70 EPSG:3844, fără coordonate inventate, fără auto-declarare ADMIS).

- **Inovație Geometrică & Geodezică (Sesiunea `dcb45b25-1f51-4e7a-886e-31b74fb30717`)**:
  - **Unelte create și active**:
    - `tools/simulate_drone_photogrammetry_flight.py`: Zbor fotogrammetric grilă 5×5 (25 stații foto acoperind 100% perimetrul de 1.05 km × 1.05 km).
    - `tools/capture_scale_150_remediated_frames.py`: Captură cadru QGIS la scară cadastrală 1:150 (fereastră 44 m × 25 m, rezoluție 1 px = 3.9 cm).
    - `tools/remediate_full_map_precision_first.py`: Remediere cadastrală balansată: **195 clădiri validate 1CC**, **75 de corpuri articulate L/U/T păstrate la 90°**, **119 dreptunghiuri pure**, **19 dubluri suprimate față de Lot 1–5**, **0 spike-uri**.
  - **Straturi active**:
    - GeoPackage: `workspace/option_b_validation_20261019/b_proposals_cleaned.gpkg` (straturi `B_ROOF_PROPOSALS` și `B_FOOTPRINT_1CC`).
    - Proiect QGIS comun: `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`.
  - **Rapoarte și galerii locale (Server HTTP Port 8769)**:
    - `http://127.0.0.1:8769/scara_150_ultra_detaliu/index.html` (Galerie comparativă 1:150 Înainte vs După)
    - `http://127.0.0.1:8769/scara_150_ultra_detaliu/charts.html` (Dashboard interactiv de grafice Chart.js)
    - `http://127.0.0.1:8769/drone_flight_strips/index.html` (Zbor fotogrammetric 25 benzi)
  - **Verificări automate**:
    - `python scripts/validate_project.py --mode fast`: 17 teste Golden Geometry trecute în 2.67s.
    - `python -m unittest discover stratum_ro/test`: 536 teste trecute (0 eșecuri, 0 erori, 9 omise pentru context GUI QGIS).


## Ultimul checkpoint: Orchestrare Laya, HITL 1-Click & Sincronizare 242 Clădiri (2026-10-26)

- **Integrare Model Decizie Laya (ModernBERT 421M)**: Rulat prin `tools/laya_building_evaluator.py` pe toate cele 242 de clădiri, livrat în `workspace/reviews/laya_decisions_20261026.json` (99 Admis, 93 Ajustare Contur, 3 Mutilate, 47 Rebut).
- **Set de date verificat de proprietar**: `workspace/reviews/user_verified_feedback_20261026.json` integrat și versionat oficial în repository.
- **Interfață HITL 1-Click Triage**: Salvare automată fără buton secundar în `workspace/reviews/catalog_cladiri_ortofoto.html`, cu suport complet pentru Dublă Verificare.
- **Raport interactiv de sincronizare**: `workspace/reviews/raport_sincronizare_laya.html` afișează comparația binară/multiclase Laya vs Uman cu suport pentru sincronizare live cross-tab.
- **Publicare completă**: Ambele branch-uri `main` și `feat/hybrid-dev-workflow` sunt sincronizate la zi cu GitHub și GitHub Pages (fără cache).
