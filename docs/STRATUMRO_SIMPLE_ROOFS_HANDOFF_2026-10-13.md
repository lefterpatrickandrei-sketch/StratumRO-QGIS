# StratumRO — rectificare simplă a contururilor și predare pentru agenți

> Continuare după verdictul proprietarului: [STRATUMRO_REVIEW18_HANDOFF_2026-10-13.md](STRATUMRO_REVIEW18_HANDOFF_2026-10-13.md). Lotul de mai jos a primit7/8 trecute; B00005 respins pentru două clădiri unite. Noul lot separă B00005 și include încă10 teste reale. Indicația istorică de păstrare a B00005 nu mai este valabilă.

Data: 2026-10-13. Cererea proprietarului: eliminarea treptelor și pintenilor, forme simple potrivite pentru lucru cadastral, cod reutilizabil și documentație persistentă. Acesta este punctul de intrare curent pentru continuare.

## Rezultatul și limitele sale

**IMPLEMENTAT / TESTAT / MĂSURAT pe candidații de dezvoltare.** Din cele 8 contururi inspectate în region21, șase au fost rectificate. Cinci au 4 colțuri, unul are 6 colțuri pentru acoperișul în L. B00005 și B00010 au fost păstrate conform inspecției precedente. Fișierul rezultat conține 12 candidați: cei 8 din region21 și cei 4 păstrați din celelalte două regiuni. Nu reprezintă toate clădirile din AOI și nu este evaluarea tuturor celor 29 de referințe.

| ID local în region21 | Noduri mască înainte de simplificare | Noduri rezultat | Rezultat geometric |
|---|---:|---:|---|
| B00006 | 42 | 4 | Dreptunghi pe nucleul optic, fără terasa inferioară |
| B00008 | 26 | 4 | Dreptunghi care păstrează eliminarea terasei |
| B00009 | 48 | 6 | Formă în L; extensia acoperișului păstrată |
| B00014 | 33 | 4 | Dreptunghi fără pintenul superior |
| B00018 | 4 | 4 | Sera mare: noua orientare optică păstrată |
| B00030 | 85 | 4 | Sera lungă: margini drepte, prelungirea eliminată |

Numerele sunt citite din `rectification_report.json`. Nu există comparație cu măsurători terestre independente. Contururile GMW ale proprietarului sunt referințe de dezvoltare cu obiecte mixte; nu au fost folosite pentru desenarea noilor contururi.

**Distincție necesară pentru continuare:** `ACOPERISURI_SIMPLE` descrie marginea vizibilă a acoperișului. `SOL_ESTIMAT_NEVERIFICAT` este o ipoteză separată, cu retragere presupusă de 0.4m, nu o amprentă la sol măsurată. Toate înregistrările au `validare=IPOTEZA_NEVERIFICATA`, `qa_status=NECESITA_VERIFICARE`, `action_code=REVIZUIRE_MANUALA`. Clasele constructive moștenite sunt marcate `semantic_status=TIP_CONSTRUCTIE_MOSTENIT_NEVERIFICAT`. Formele simple nu dovedesc precizia pozițională sau valabilitatea cadastrală.

## Unde se află livrabilele

Director autoritativ: `workspace/reviews/simple_roofs_rectified_20261013/`.

- `simple_roofs.gpkg`: `ACOPERISURI_SIMPLE` (12), `IPOTEZE_OPTICE_INTRARE` (12), `CONTURURI_ANTERIOARE` (12), `SOL_ESTIMAT_NEVERIFICAT` (12).
- `inspectie_forme_simple.qgs`: proiect QGIS cu ortofoto native, contururi noi verzi, stratul estimat la sol ascuns. Proiectul inițial nu a fost suprascris; în sesiunea deschisă s-au repunctat doar straturile derivate, iar starea proiectului a rămas nesalvată.
- `comparison.png`: 8 detalii pe ortofoto; magenta=anterior, verde=rectificat. `qgis_canvas.png`: captură efectivă din QGIS Desktop.
- `rectification_report.json`: proveniență, noduri, arii, suport/acoperire, atribute istorice.
- `qgis_readback.json`: redeschidere confirmată, 8 straturi în proiect, stratul nou valid EPSG:3844.
- `unit_tests.log`: 346 descoperite, 337 trecute, 9 omise, 0 eșecuri, 33.609s, exit0.
- `scripts/`: copiile experimentelor de segmentare și pregătire a ipotezelor, arhivate pentru reluare. Acestea folosesc căile locale ale acestei mașini și nu trebuie confundate cu API-ul generic.

Directoarele `simple_roofs_20261013/` și `simple_roofs_final_20261013/` sunt **iterații intermediare depășite**. Nu folosiți metadatele lor în locul variantei `simple_roofs_rectified_20261013/`.

## Codul reutilizabil

- `stratum_ro/roof_refinement_prompts.py`: puncte SAM2 pentru acoperișuri roșii; modul inițial scris de Antigravity, corectat/optimizat ulterior de Codex. Punctele singure nu au eliminat suficient terasele.
- `stratum_ro/optical_roof_edges.py`: decupare pe RGB și nDSM relativ; roșu cu suport class6/înălțime sau sticlă teal. Culorile necunoscute păstrează intrarea. Nu este un clasificator universal.
- `stratum_ro/roof_simple_geometry.py`: dreptunghiuri și poligoane ortogonale; axă principală, simplificare 0.35–2.5m, reconstruire de laturi H/V, dreptunghiuri din cuantile de ocupare 1/2.5/4%. La eșec, caută orientări locale ±4° fără a relaxa pragurile. Preferă numărul minim de colțuri și apoi IoU maxim.
- Praguri de dezvoltare: >=92% din forma propusă trebuie să fie în masca observată; >=90% din mască trebuie păstrată; maximum12 noduri; minimum0.8m per latură. Nu sunt toleranțe cadastrale. Dacă nu există o formă susținută, păstrează masca cu `NEEDS_REVIEW`, fără aprobare sau ștergere.
- `stratum_ro/roof_body_recovery.py`: integrarea opțională a decupării și simplificării înaintea revizuirii senzorilor. Păstrează măștile brute; recalculează geometria și atributele; eșecurile de simplificare merg în `REVIZUIRE_COMPLEXA`.
- `run_hybrid_full_aoi.py`: flag nou `--simple-roof-edges`, permis numai împreună cu `--proposal-policy roof_bodies`. Implicit rămâne `legacy`.
- `scripts/rectify_roof_candidates.py`: reluarea lotului de candidați deja segmentați. Nu suprascrie rezultate existente. Recalculează aria, perimetrul, nodurile, centrul, ipoteza la sol, înălțimile nDSM, fracția RGB de vegetație, suportul și QA. Folosește scorurile din noua mască SAM2 pentru cele șase modificări, nu scorurile istorice. Atributele istorice rămân în raport.
- `scripts/render_simple_roof_comparison.py`: randare reproductibilă a comparației native.

## Comenzi de reluare

Rulați din `C:\Users\lefpa\Downloads\QGIS-AI`, cu un director de ieșire NOU:

```powershell
venv\Scripts\python.exe scripts/rectify_roof_candidates.py `
  --input workspace/reviews/edge_recovery_20261013/edge_candidates.gpkg `
  --prior workspace/reviews/body_recovery_20261013/roof_recovery.gpkg `
  --sam-masks workspace/reviews/edge_recovery_20261013/prompt_refinement_tight.gpkg `
  --ortho workspace/output/ortofoto_cluj_usamv_rgb.vrt `
  --laz "C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz" `
  --dtm "C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif" `
  --output-dir workspace/reviews/simple_roofs_next_run

venv\Scripts\python.exe scripts/render_simple_roof_comparison.py `
  --gpkg workspace/reviews/simple_roofs_next_run/simple_roofs.gpkg `
  --ortho workspace/output/ortofoto_cluj_usamv_rgb.vrt `
  --region REF_TIER1_021 `
  --output workspace/reviews/simple_roofs_next_run/comparison.png

venv\Scripts\python.exe -m unittest discover stratum_ro/test
```

Integrarea completă este **IMPLEMENTATĂ, dar NU A FOST RULATĂ pe toate cele 8 tile-uri** cu noua opțiune:

```powershell
venv\Scripts\python.exe run_hybrid_full_aoi.py --proposal-policy roof_bodies --simple-roof-edges --output-dir workspace/reviews/full_simple_roofs_next_run
```

Nu prezentați această comandă ca experiment deja executat. Inspectați rezultatele complete, inclusiv formele complexe și clădirile omise, înainte de schimbarea modului implicit.

## Verificări și probleme deschise

Testele includ acoperiș rotit, eliminare trepte fără recrearea terasei, L cu șase colțuri, triunghi care nu trebuie forțat în dreptunghi, păstrarea curților interioare în revizie, ortogonalitate, imutabilitate, decupare roșu/teal și păstrarea părților gri susținute de LiDAR. Testul vechi de suprafață pentru puncte negative a fost adaptat: fundalul de excludere este acum la4m, peste pragul relativ roof-minus2m; un test separat verifică explicit diferența2m/3m față de acoperișul de4m.

Inspecția vizuală Codex: cele șase forme noi nu mai au treptele măștilor; B00008 elimină terasa; B00009 păstrează L; B00018 corectează orientarea; B00030 elimină pintenul și regularizează marginile. La B00006 marginea superioară/anexa rămâne sensibilă la separarea corpurilor. La sere, marginea foto trebuie verificată față de fațadă/sol; nu presupuneți că glass/class6 sunt perfecte. B00005, păstrat cu10 noduri, poate primi ulterior o simplificare separată numai cu verificarea anexei; nu a fost unul dintre cele șase contururi greșite din auditul autorizat.

Pașii următori pentru agent: (1) citiți acest fișier și raportul JSON; (2) inspectați QGIS/imagini; (3) verificați integrarea pe un lot nou și apoi pe cele8 tile-uri într-un director separat; (4) păstrați și raportați eșecurile `NEEDS_REVIEW`; (5) pentru afirmații de precizie/generalizare, obțineți date independente adecvate. Nu desenați predicții după referințe. Nu declarați întregul StratumRO reparat pe baza acestor șase cazuri.

## Antigravity, trasabilitate și fișiere protejate

Antigravity a produs modulul inițial pentru puncte în conversația `fbb88596-3eb6-48c7-918c-bbff3e84a0fa`, statusSUCCESS,80.27s, și revizia/documentarea în conversația `487c8428-6e2f-4806-aa07-a30e08c45df7`, statusSUCCESS,112.12s. Revizia este în `docs/STRATUMRO_SIMPLE_ROOFS_AGENT_REVIEW_2026-10-13.md`; snapshot anterior ultimelor schimbări, cu actualizarea Codex în antet. Codex a executat testele, a rectificat geometriile, a verificat imaginile și a salvat proiectul.

În acest lot nu au fost suprascrise `workspace/output/cladiri_stereo70.gpkg`, `workspace/output/cadastru_ancpi.dxf` sau `data/ground_truth/tier1_teren.geojson`; SHA256 corespunde stării precedente (manifestul lotului consemnează valorile). Nu există commit/push pentru acest lot; checkout-ul conține multe modificări anterioare. Nu le resetați și nu atribuiți întregul `git diff` acestei rectificări. Niciun worker Antigravity nu rămâne în execuție după finalizarea acestui lot.
