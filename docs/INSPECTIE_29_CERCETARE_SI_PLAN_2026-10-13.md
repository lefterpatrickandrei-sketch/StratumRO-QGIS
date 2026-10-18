# Inspecția celor 29 de clădiri — cercetare, audit și plan de implementare

Data: 13 octombrie 2026. Coordonare: Codex. Audit delegat: Antigravity CLI, două sarcini delimitate, fără modificarea datelor. Acest document este planul rezultat din inspecția codului, recalcularea fișierelor curente și verificarea unor surse metodologice primare.

## Decizia de lucru

Păstrăm galeria și cele 29 de planșe existente ca versiune istorică. Construim următoarea versiune ca dosar de inspecție verificabil, pornind de la identitate, proveniență și evaluare corectă. Îmbunătățirea desenului HTML vine după aceste condiții. Nu relansăm întregul pipeline și nu schimbăm modelul înainte de a localiza etapa care produce erorile.

Scopul utilizatorului: să poată examina fiecare clădire din mai multe perspective, să înțeleagă de ce rezultatul este problematic, să înregistreze o decizie și să reia inspecția după o întrerupere. Cele 29 de referințe constituie acum un set de diagnostic/dezvoltare; nu le prezentăm drept set independent de test după ajustări făcute pe aceleași exemple.

## Ce există și ce s-a verificat

- `StratumRO_29_Cladiri_Screenshots/INDEX_29_CLADIRI.html`: 29 de carduri; toate cele 29 de imagini referite există. Planșele au fost generate pe 12 octombrie 2026, aproximativ 15:47–15:48, ora locală.
- `tools/export_29_building_screenshots.py`: exportorul existent, inclus în checkpoint-ul `08524df`; pagina este statică, cu imagini care se deschid separat.
- `tools/generate_visual_validation_pack.py`: există generatoare pentru hartă de confuzie, zoomuri, săgeți, coridor de toleranță și desen CAD. Existența lor nu demonstrează consistența metodologică a figurilor.
- `tools/hitl_feedback_bridge.py`: execută modificări în GeoPackage și sincronizează separat QGIS. Integrarea de editare necesită verificarea identității și recuperării înainte de conectarea la inspector.
- Checkout: `C:\Users\lefpa\Downloads\QGIS-AI`, HEAD `02ae56771795f4ab9991c00477ef98596fca122e`. Există modificări locale anterioare auditului; nu au fost resetate sau comise.

Auditul numeric a citit toate cele 29 de referințe și toate cele 150 de predicții din stratul CLEAN. Inspecția vizuală în detaliu a acoperit planșele 4, 14 și 29. Nu pretindem examinare vizuală profesională a tuturor celor 29. Deschiderea paginii prin browserul automat a fost blocată pentru URL-ul local `file:`; fluxurile de browser, tastatură și persistență nu au fost testate. Nu s-a ocolit restricția.

Fișierele de dovezi sunt în `workspace/reviews/inspection29_20261013/`: `audit_current.json`, `all_29_buildings.csv`, `validation_checks.json`, `README.md`. Manifestul include hash-uri SHA256 pentru referință, GeoPackage, VRT și indexul HTML. Hash-ul VRT nu certifică singur toate rasterele sursă ale mozaicului; includerea acestora este parte din prima etapă a planului.

## Constatări prioritare și limitele lor

### P0 — Rapoartele curente și istorice nu au aceeași bază

**MEASURED:** 29 de referințe, 150 de predicții CLEAN. Asociere unu-la-unu, maximizând întâi numărul de perechi peste prag și apoi suma IoU:

| Prag IoU | Perechi peste prag | Referințe neasociate | Predicții neasociate |
| --- | ---: | ---: | ---: |
| 0,30 | 9 | 20 | 141 |
| 0,40 | 7 | 22 | 143 |
| 0,50 | 5 | 24 | 145 |

La 0,50, triada este **5 / 29 / 150**. Acesta este un rezultat de asociere geometrică pe fișierele curente. Nu dovedește validarea clădirilor sau calitatea referințelor. Pentru aceste referințe, fracția asociată este 17,24%. Precizia globală nu este calculată: exhaustivitatea referinței pe întregul AOI nu a fost stabilită. Cele 145 de predicții neasociate nu sunt automat artefacte; au nevoie de inspecție și/sau referințe suplimentare.

Raportul istoric `reports/tier1_cadastre/tier1_29bldg_summary.json` are timestamp intern 2026-09-11, 137 de predicții, prag 0,30, 20 TP și 8 FN. Nu se poate compara direct cu pragul 0,50 sau cu setul curent. Chiar intern, 20+8 nu conservă cele 29 de referințe. Nu numim diferența o regresie de model până când nu reproducem configurațiile și datele ambelor rulări.

### P0 — Evaluatorul permite două erori de numărare

**TESTED pe contraexemple sintetice:** în `engine/evaluation.py`, un candidat sub prag poate rămâne `matched=True`, fiind exclus atât din TP, cât și din FN. `used_preds` este utilizat la numărarea predicțiilor rămase, dar nu împiedică reutilizarea unui candidat la altă referință.

- O referință și un candidat cu IoU sub 0,30 produc TP=0, FN=0, FP=0.
- Două referințe și o singură predicție care le acoperă produc TP=2 pentru o singură predicție.

Rezultatele exacte sunt în `validation_checks.json`. Aceste teste demonstrează defecte de contabilizare pe fixture-uri; nu măsoară performanța din teren. În auditul curent, candidații 19 și 70 sunt fiecare alegerea independentă pentru câte două referințe; la pragul 0,50 nu umflă numărul de cinci perechi, fiind sub prag. Riscul general rămâne real.

### P0 — Identitatea stratului pentru sol este duplicată

**MEASURED:** `CLADIRI_SOL_ANCPI` are 300 de rânduri, 150 de ID-uri distincte și 150 de geometrii distincte. Straturile CLEAN și HIBRID au câte 150 de rânduri și ID-uri unice. Nu am atribuit o cauză de scriere fără o reproducere controlată.

Exportorul alege independent cel mai bun acoperiș și cel mai bun poligon pentru sol. Acest lucru nu garantează că provin din aceeași entitate. În audit, referința 1 are un candidat de acoperiș cu suprapunere foarte mică, dar niciun candidat de sol cu suprapunere; nu este demonstrată o asociere între două ID-uri diferite. În noua versiune, acoperișul și solul trebuie legate prin identitate și proveniență, nu prin două optimizări independente.

### P0 — „VALIDAT” contrazice dovezile afișate

**MEASURED + comportament inspectat:** cele cinci perechi cu IoU ≥0,50 sunt referințele 5, 6, 8, 20 și 21. Toți cei cinci candidați au `action_code=ROSU_RESPINS_ARTEFACT` în sursă. Marcajul automat de respingere poate fi greșit; nu este adevăr de teren. Inspectorul trebuie să arate ambele informații și să ceară o decizie motivată, nu să le rezolve prin culoarea verde.

Pentru cele cinci perechi, RMSE simetric al conturului calculat independent la pas de cel mult 0,25 m este aproximativ 7,140; 3,231; 4,764; 4,217; 0,848 m. O suprapunere mare poate coexista cu erori locale mari. Aceste valori sunt diagnostice față de referința disponibilă, cu proveniență de teren încă neverificată.

`generate_visual_validation_pack.py` folosește 0,40 în asociere, dar scrie 0,50 în legendă. Generatorul galeriei calculează media numai pe valori IoU pozitive, excluzând omisiunile. Auditul independent obține media celui mai bun IoU pe toate cele 29, inclusiv zero: **22,23%**. Aceasta nu trebuie confundată cu media pe perechi acceptate la un prag.

### P0 — Proveniența referinței trebuie verificată înaintea corecțiilor

**MEASURED:** cele 29 de geometrii sunt valide topologic și au ID-uri unice. Atributele curente nu includ data măsurătorii, echipamentul, jurnalul de teren sau streașina măsurată. Valoarea `survey_source` nu înlocuiește documentele de proveniență. Auditul nu stabilește că aceste documente lipsesc din toate locațiile; ele nu sunt legate de entitățile inspectate.

**Observație vizuală:** referința 29 are un contur neobișnuit față de clădirea vizibilă în ortofotografie. Trebuie verificată semantica obiectului — clădire, corp, parcelă sau altă geometrie — și extragerea lui.

**Risc de cod, nu cauză demonstrată:** `extract_gmw_cadastre.py` și `extract_all_imobile.py` scanează perechi de double din payload-ul GMW și formează poligoane, fără decodificare structurală completă a obiectelor/inelelor. Nu am demonstrat că unul dintre ele a produs exact fișierul actual. Se verifică exportul nativ din GIS, obiectele și ID-urile originale; nu se relansează aceste scripturi peste etalon.

**Risc separat de contaminare a evaluării:** `tools/generate_clean_cadastral_deliverables.py` construiește geometrii CLEAN direct din referințe și atribuie scoruri/înălțimi constante. Un asemenea rezultat trebuie marcat `REFERENCE_DERIVED`, separat de extracția independentă. Codul există; nu am stabilit că stratul curent de 150 de predicții provine din acea cale. Nu folosim această comandă pentru a „repara” benchmark-ul.

### P1 — Contextul raster și diagnosticele sunt insuficiente pentru decizie

**MEASURED:** ortofoto VRT este EPSG:3844, cu pas de pixel 0,15×0,15 m; nDSM este EPSG:3844, cu pas 1×1 m. Niciunul nu declară `nodata` la nivelul citit. Pagina și imaginile declară GSD 12 cm. Pasul unui raster reproiectat nu stabilește GSD-ul nativ al achiziției; afișăm separat ce este măsurat și ce rămâne necunoscut.

`from_bounds()` și `read(window=...)` nu substituie verificarea extentului efectiv, a transformării ferestrei, a măștilor și a compatibilității CRS. Nu am demonstrat o deplasare globală a rasterului; aceasta este o ipoteză pentru experiment. Pixelii negri nu sunt clasificați automat ca nodata.

## Cercetarea care ghidează implementarea

1. [SpaceNet — metoda de evaluare](https://github.com/SpaceNetChallenge/utilities#evaluation-metric) folosește IoU pentru detecție, cu cel mult un TP pentru o referință. [SpaceNet 6](https://spacenet.ai/sn6-challenge/) documentează pragul 0,50. Aceste surse justifică separarea detecției de calitatea conturului. Asocierea de diagnostic folosită aici nu este declarată reproducere exactă a evaluatorului oficial SpaceNet.
2. [ISPRS — rezultate de detecție și calitate geometrică](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/results/area2_detection/CAL_13_buildings/index.html) prezintă separat evaluarea per obiect/per pixel și distribuțiile RMS ale contururilor. Consecință: pagina are nevoie de mai multe perspective, nu de un singur scor.
3. [Rasterio — citirea pe ferestre și transformarea ferestrei](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html) susține reconstruirea corectă a coordonatelor cropului. Metadatele afișate trebuie să provină din surse și transformări reale.

Aceste surse sunt metodologice. Nu folosim o bandă de 10 cm sau pragurile din configurația proiectului drept certificat de conformitate ANCPI. Cerințele legale exacte și aplicabilitatea lor nu au fost auditate în această sarcină.

## Experimente cauzale, în ordinea costului și a dependențelor

| Experiment | Întrebarea | Ce rămâne fix | Ce se compară | Rezultatul util |
| --- | --- | --- | --- | --- |
| E0 — Referință și identitate | Comparăm același tip de obiect, din aceeași epocă? | Copia originală a referinței și imaginile | Export nativ GMW/GIS, schemă, obiecte și jurnal de proveniență | Confirmare/contestare per referință; fără ajustarea adevărului pentru a crește scorul |
| E1 — Evaluator | Rapoartele sunt aritmetic consistente? | Aceleași geometrii și aceleași praguri | Evaluator existent vs. asociere unu-la-unu | Conservarea numărului de referințe și predicții; manifest unic |
| E2 — Etape | Unde se pierde clădirea sau apare geometria prea mare? | Aceleași intrări, model, prompturi și AOI | Masca brută → poligon → regularizare → filtru → retragere | Prima etapă care înrăutățește conturul sau elimină candidatul |
| E3 — Georeferențiere | Există o deplasare comună sau erori locale? | Geometrii originale, surse și setul de evaluare | Distribuții ΔE/ΔN pe obiecte confirmate, puncte de control independente | Estimare robustă cu incertitudine; calibrare și evaluare pe obiecte separate |
| E4 — Streașină | Retragerea uniformă de 0,40 m este justificată? | Identitatea perechii și geometria acoperișului | Fără retragere / retragere existentă / măsurare independentă | Diagnosticul efectului; ajustările pe cele 29 sunt exploratorii, nu validare independentă |
| E5 — Respingere și vegetație | Regulile elimină clădiri sau păstrează arbori? | Setul curent și etichete umane pe cazuri concrete | Motivele `action_code`, ortofoto, nDSM, profile și măști | Cazuri confirmate, neclare sau respinse; ablație a unei singure reguli |

E2 trebuie să examineze și candidații respinși înainte de stratul CLEAN. Faptul că șapte referințe nu au candidat intersectant în CLEAN nu dovedește că SAM2 nu le-a segmentat vreodată. E3 nu poate fi decis doar din centroidul a cinci poligoane cu forme diferite. E5 nu poate fi decis doar din înălțime sau dintr-un verdict VLM.

## Plan de implementare delegabil

### T0 — Îngheață intrările și clarifică referința (P0)

Antigravity produce un manifest versionat în `workspace/reviews/inspection29_v2/<run_id>/`, cu SHA256 pentru geometrii, model/prompt/config folosite dacă sunt cunoscute, VRT și rasterele dependente, metadate CRS, transformări, tipul obiectului, data sursei, legătura spre sursa nativă și starea dovezii. Necunoscut rămâne explicit necunoscut. Extrage o copie de diagnostic deduplicată; originalul rămâne intact. Documentează referințele contestate și originea artefactelor `REFERENCE_DERIVED`.

**Acceptare:** 29 de referințe și ID-uri unice; fiecare derivat are o sursă și o stare de proveniență; duplicatele identice se disting de același ID cu geometrii conflictuale; repetarea exportului nu dublează rândurile. Orice benchmark cu referință contestată este etichetat provizoriu.

### T1 — Repară contabilizarea și schema evaluării (P0)

Fișiere vizate: `engine/evaluation.py`, teste în `stratum_ro/test/`, un singur modul comun pentru asociere și schema manifestului, reutilizat de generator. Se păstrează compatibilitatea rapoartelor vechi prin versiunea schemei; evităm un al doilea evaluator divergent numit doar „v2”.

Separăm `diagnostic_best_candidate` de `assigned_match`. Stabilim clar politica unu-la-unu și pragul; păstrăm relațiile unu-la-mai-mulți pentru diagnostic, nu pentru umflarea TP. O referință sub prag devine neasociată la acel prag. Predicțiile fără referință sunt `UNRESOLVED_WITHOUT_REFERENCE` până la certificarea acoperirii referinței. Valorile absente sunt `null` cu motiv, nu zero.

**Acceptare:** contraexemplele din audit devin teste de regresie; TP+referințe neasociate=29 și TP+predicții neasociate=150; niciun ID de predicție nu apare în două asocieri; pragurile exact egale sunt tratate consecvent; rezultate stabile la permutarea intrărilor; statisticile declară denominatorul și populația; golurile și multipart sunt acoperite explicit. Se rulează suita cerută de AGENTS.md.

### T2 — Produce dosarul multifactorial pentru toate cele 29 (P1)

Fișiere vizate: `tools/export_29_building_screenshots.py`, funcții de randare reutilizate și teste cu cropuri/fixture-uri mici. Ieșire nouă versionată; fără suprascrierea planșelor istorice.

Pentru fiecare clădire:

- Ortofoto fără contur și aceeași fereastră cu suprapuneri activabile: referință, mască brută, acoperiș, sol asociat prin ID. Un candidat sub prag este marcat ca ipoteză, nu pereche confirmată.
- Exces și lipsă de suprafață prin diferențe geometrice, cu legendă explicită. Contururi interioare și multipart vizibile. Niciun nod nu dispare în exportul detaliat; etichetele pot fi ascunse în imaginea de ansamblu.
- Hartă nDSM și profile doar când sursa, masca, rezoluția și unitățile sunt cunoscute. Când lipsesc, panoul spune ce lipsește.
- Compararea etapelor înainte/după regularizare și filtrare, cu aceeași scară și același extent. Legătura între etape se demonstrează prin identitate/lineage, nu prin ordinea rândurilor.
- IoU, diferență de arie și perimetru, RMSE simetric, P95 al distanțelor, Hausdorff densificat cu metoda declarată, ΔE/ΔN, validitate, număr de componente/goluri, unghiuri și motivele respingerii. Distanțele la cel mai apropiat contur nu sunt prezentate ca potriviri de colțuri omoloage.
- Sursa și starea referinței, pasul rasterului, hash-ul rulării, candidații alternativi și toate avertismentele. O bandă de toleranță este un instrument tehnic configurabil, fără etichetă de conformitate legală.

**Acceptare:** manifestul are exact cele 29 de ID-uri; toate imaginile există; cropurile nu sunt întinse pentru a umple o fereastră; testele sintetice cu un raster georeferențiat cunoscut verifică alinierea; lipsa nDSM/mască nu produce date inventate; metadatele vin din manifest; pentru cazurile 4, 14, 20 și 29 se face inspecție vizuală explicită și se păstrează dovezile.

### T3 — Inspector HTML cu decizii recuperabile (P1)

Păstrăm HTML/CSS/JS local, fără backend sau framework nou pentru această etapă. Flux: lista celor 29 → filtre după problemă/stare → dosar clădire → comparație → notă și decizie → următoarea clădire → export jurnal. Panoul separat de candidați neasociați se poate extinde fără a numi automat acești candidați artefacte.

Stări: `NEINSPECTAT`, `DATE_INSUFICIENTE`, `NECESITA_CORECTIE`, `CANDIDAT_RESPINS`, `PREGATIT_PENTRU_VERIFICARE_PROFESIONALA`. O stare este însoțită de motiv, autor, timp, ID referință/candidat și hash-ul datasetului. Acceptarea geometrică, examinarea vizuală și semnarea profesională sunt câmpuri separate. Nu există un buton care declară validare de teren fără dovezi.

Persistență locală pentru reluare, cu semnal explicit când stocarea nu este disponibilă. Export/import JSON verificat și versionat; `localStorage` nu este singurul exemplar al jurnalului. Importul unei rulări incompatibile afișează conflictul, fără aplicare automată. Export CSV pentru triere și legătură către QGIS după referință/ID stabil.

**Acceptare:** toate 29 sunt accesibile; filtrarea nu pierde selecția/nota; căutarea, navigarea, zoomul și comutarea straturilor funcționează la tastatură; reluarea păstrează deciziile; export→import reproduce jurnalul; dataset incompatibil, imagine lipsă și stocare blocată au stări clare; test desktop și viewport îngust. Abia atunci poate fi declarat testat fluxul HTML.

### T4 — Cercetare și corecții țintite în pipeline (P1/P2)

După T0/T1 și primele dosare, Antigravity execută E2–E5 pe cazuri reprezentative, câte o variabilă schimbată. Fiecare rezultat are diff, parametri, input/output hashes, imagini înainte/după și toate cele trei denominatoare. Pentru referințele 7/14 și 9/10 se verifică relațiile comune de candidat; pentru 11/12/13/18/19/22/27 se urmărește etapa dispariției; pentru 5/6/8/20/21 se investighează contradicția dintre suprapunere și respingere. Referința 29 are verificarea sursei înainte de reglarea segmentării.

**Acceptare:** cauza este susținută de o comparație controlată; testul de regresie reproduce eroarea relevantă; câștigul pe cazurile selectate nu ascunde rezultatul pe toate 29; setul independent de evaluare este stabilit înainte de afirmații de generalizare.

### T5 — Editare QGIS și export, după stabilizarea inspecției (P2)

Integrarea cu `hitl_feedback_bridge.py` vine după identitate stabilă, scriere tranzacțională/recuperare, gestionarea lock-urilor QGIS, păstrarea celorlalte straturi și comportament explicit la sincronizare parțială. Se testează pe GeoPackage temporar, nu pe livrabilul activ.

**Acceptare:** delete/merge/regularize/set_offset afectează numai entitățile intenționate; eșec simulat nu lasă rezultat parțial; redeschiderea QGIS și a fișierului arată aceeași geometrie; jurnalul identifică toate operațiile. Livrarea profesională rămâne o decizie separată, cu dovezi corespunzătoare.

## Modul de colaborare și buget

Codex definește sarcina și criteriile; Antigravity scrie și verifică un singur lot delimitat; Codex revizuiește diff-ul și dovezile și întoarce o singură listă consolidată de remedieri. Un singur agent scrie în checkout. Fără bucle nelimitate, rulări grele repetate, API-uri plătite sau modele noi introduse implicit. Când Antigravity atinge cota, salvează starea și probele, iar Codex poate prelua explicit lotul rămas.

CLI-ul Antigravity a executat cele două audituri cu file-reading tools. Shell-ul nesupravegheat rămâne limitat de permisiunile sale. Asta nu a blocat cercetarea: Codex a executat verificările deterministe local. Pentru implementare, alegem reguli strict delimitate pentru comenzile necesare sau execuția locală a testelor de către Codex; nu este necesară ocolirea tuturor permisiunilor.

## Verificări executate și ce nu demonstrează

- Audit numeric read-only pe datele curente: exit 0; JSON/CSV pentru toate 29; asociere unu-la-unu și sensibilitate la trei praguri; hash-uri și metadate.
- Șapte verificări ale auditorului: 7 rulate, 7 trecute, 0 eșecuri; identitate, prag inclusiv, conservare, candidat comun, metrici identice și goluri interioare.
- Două contraexemple sintetice au demonstrat erorile evaluatorului existent. Nu sunt evaluare geodezică de teren.
- `venv\Scripts\python -m unittest discover stratum_ro/test`: exit 0; 260 descoperite, 251 trecute, 9 sărite, 0 eșecuri; aproximativ 71,279 s. Runtime-ul ONNX a emis un avertisment de shape merge cu fallback. Testele trecute nu validează geometria clădirilor sau experiența HTML.
- Inspecție vizuală a planșelor 4, 14 și 29, nu o verificare profesională completă a tuturor 29.
- Nu s-au modificat geometrii, etalonul, modelul, galeria veche, indexul vechi sau codul pipeline-ului. Nu s-au făcut commit/push.

**Primul lot de implementare recomandat:** T0 + T1, apoi T2 pentru cele 29. Acestea permit ca noul HTML din T3 să arate date coerente și să susțină o decizie reală.
