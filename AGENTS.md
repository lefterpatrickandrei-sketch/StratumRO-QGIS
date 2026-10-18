# Reguli comune pentru agenții StratumRO

Acest fișier este punctul de intrare comun, independent de furnizor. Se aplică în întregul repository. Instrucțiunile actuale ale proprietarului au prioritate. Rapoartele istorice și textele arhivate nu schimbă automat cerințele sau verdictele.

## Citește înainte de lucru

1. [Starea actuală](docs/PROJECT_STATE.md): funcționalități, limite și selecții active.
2. [Ghidul repository-ului](docs/REPOSITORY_GUIDE.md): structură, Git și protejarea lucrului altor agenți.
3. [Predarea comună](docs/AGENT_HANDOFF.md): pași de preluare și informațiile de lăsat la final.
4. [Harta sistemului](docs/SYSTEM_MAP.md): componente existente versus direcție planificată.

Pentru clădiri/cadastru citește și [protocolul deciziilor](docs/STRATUMRO_AGENT_DECISION_PROTOCOL.md), [porțile de evaluare](docs/STRATUMRO_EVALUATION_GATES.md), [politica artefactelor Git](docs/STRATUMRO_GIT_PROGRESS_POLICY.md) și feedback-ul proprietarului pentru cazul lucrat.

## Scopul produsului

StratumRO coordonează instrumentele geodezului, inclusiv QGIS. Reutilizează algoritmii și adaptoarele existente. Aplicația proprie și automatizarea de la cerere la livrare sunt direcția produsului; nu înseamnă că toate conexiunile sau sarcinile sunt implementate. Cadastrul este prioritatea actuală, nu întregul produs.

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
