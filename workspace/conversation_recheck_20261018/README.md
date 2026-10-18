# Reverificarea conversației Antigravity și a rezultatelor curente

Data: 2026-10-18. Conversație: `80fa85ac-8b08-481d-a858-2210a8757155`. Bază de cod inspectată: `4448f030165805f266da7680c277de08d82ab24d`. Cerință: citirea atentă a conversației și reconcilierea afirmațiilor despre workspace, Lot4, full-auto și lotul ulterior.

**Verdict: agenții au lucrat în aceeași copie StratumRO. Antigravity a produs reparații reale pentru Lot4/T22 și apoi alte rezultate automate, inclusiv Lot5. Aceste rezultate sunt distincte și nu toate sunt corecte sau acceptate.** Auditul anterior rămâne relevant pentru erorile măsurate, dar explicația politicii Git și inventarul Lot4 trebuie actualizate.

## Surse și procedură

Au fost citite cererile utilizatorului și răspunsurile publice din jurnalul conversației: 31 cereri și 39 răspunsuri publice. Au fost verificate argumentele comenzilor și rapoartele Markdown despre Lot4, T22, full-auto, comparația A/B și auditul ulterior al eșecului B. Nu se publică transcrierea integrală sau raționament intern. [Index, evenimente selectate, hash sursă și măsurători](recheck.json); [script de citire și calcul](recheck.py).

Au fost recitite cinci seturi GIS, în EPSG:3844, și randate separat toate cele 10 cazuri Lot4 și toate cele 10 Lot5. Nu s-a pornit inferență și nu s-au editat geometriile. [Scriptul de randare](render_current_lots.py), [manifestul celor 20 imagini locale](visual_manifest.json), [starea proiectului live](live_sources.json).

Imaginile se află local în `workspace/reviews/conversation_recheck_20261018/`. Nu sunt adăugate în Git, conform cerinței de publicare cod/documentație din conversația verificată. Manifestul păstrează căile și hash-urile; pentru reproducere sunt necesare datele locale. Lot4 folosește detaliile disponibile și ortofotourile de bază, Lot5 ortofotourile Cluj încărcate; nu atribuim tuturor capturilor rezoluția de 5 cm.

## 1. Workspace și nucleu

- Cele 310 comenzi cu director de lucru înregistrat indică `C:/Users/lefpa/Downloads/QGIS-AI`, aceeași copie folosită în verificarea Codex.
- Pluginul din profilul QGIS este o legătură simbolică spre `QGIS-AI/stratum_ro`. Calea AppData afișată de QGIS nu este o a doua copie a implementării.
- Scripturile `tools/run_stratumro_full_auto.py` și `tools/run_comparison_a_vs_b.py` importă `stratum_ro.core.geometry.regularizer` din acest repository.
- Calea `src/stratum_ro/core/geometry/regularizer.py`, menționată în unele răspunsuri, nu există. Este o trimitere greșită; nu demonstrează folosirea altui workspace.
- Existența acestor importuri nu dovedește integrarea întregului experiment în toate comenzile aplicației. De exemplu, unealta AI din `stratum_ro/ai/tools/vector_tools.py` importă încă `stratum_ro.vectorizer.CadastralVectorizer`. Nu afirmăm că orice prompt din aplicație execută automat scriptul de comparație.

[Verificări reproductibile și hash-uri ale codului](provenance.json), [script de proveniență](check_provenance.py).

## 2. Ordinea reală a etapelor

Orele de mai jos sunt locale, Europe/Bucharest, la 2026-10-18. Numerele de pas permit identificarea mesajelor în jurnalul local.

| Etapă | Dovezi / rezultat |
|---|---|
| Cerințe Git, pașii 41 și 55, aproximativ 14:31 și 15:26 | Proprietarul cere explicit cod/documentație în GitHub și păstrarea locală a GPKG, DXF, QGS, TIFF și capturilor workspace. |
| Regularizare Lot4 și recuperare T22, pașii 356 și 635 | Lot4 pleacă de la nouă ipoteze; T22 este recuperat ulterior. Fișierul v4 curent are 10 acoperișuri. |
| Full-auto, cererea 768, aproximativ 17:37 | Set separat de 264 propuneri, folosind măști și candidați existenți din două surse. |
| Comparație A/B, cererile 831 și 843, aproximativ 18:28–18:30 | Lot5/A are T31–T40 (10); B are 216 propuneri și 71 candidați respinși. |
| Răspunsul 902, aproximativ 18:36 | Agentul prezintă A drept perfect și estimează circa 2% fals pozitive B, fără evaluare independentă care să susțină aceste procente. |
| Obiecția proprietarului 903 și auditul 920, aproximativ 18:51–18:53 | Agentul recunoaște ulterior erori serioase în B. Raportul inițial nu mai poate fi tratat ca verdict final favorabil B. |
| Cererea finală 1001 și răspunsul 1020, aproximativ 19:10–19:11 | Proprietarul spune că rezultatul este incorect și întreabă dacă totul este salvat. Nu există execuție Lot6 în această conversație. |

## 3. Lot4: progres real, finisare incompletă

Sursa curentă: `workspace/reviews/lot4_20261017/selected_v4_orthogonal/lot4_orthogonal.gpkg`, strat `ROOF_HYPOTHESES_ORTHO90`, 10 obiecte. Selecția veche din `CURRENT_SELECTION.json` descrie încă nouă obiecte; aceasta explică parțial contradicția documentară despre T22.

| Caz | Noduri înainte → după | Observație vizuală a agentului, fără acceptare în numele proprietarului |
|---|---:|---|
| T21 | 20 → 66 | Acoperirea generală este îmbunătățită față de conturul anterior, dar rămân mici trepte și colțuri inutile. |
| T22 | 358 → 80 | Recuperare reală a acoperișului în U; latura lungă nordică este îndreptată și curtea este în mare parte exclusă. Marginea estică sub vegetație și complexitatea cer revizie. |
| T23 | 11 → 30 | Trepte artificiale pe muchii; regularizarea unghiurilor nu a produs o formă suficient de simplă. |
| T24 | 22 → 52 | Conturul urmărește mare parte din acoperiș, dar păstrează neregularități și trepte nejustificate vizual. |
| T25 | 4 → 4 | Formă simplă plauzibilă, fără schimbarea geometriei în această etapă. |
| T26 | 6 → 6 | Formă simplă plauzibilă, fără schimbarea geometriei în această etapă. |
| T27 | 8 → 32 | Complexitate crescută și trepte artificiale; necesită simplificare cu suport optic. |
| T28 | 4 → 4 | Formă simplă plauzibilă, fără schimbarea geometriei în această etapă. |
| T29 | 18 → 42 | Îmbunătățire generală față de masca zimțată, dar mici joguri și margini necesită finisare. |
| T30 | 4 → 4 | Formă simplă plauzibilă, fără schimbarea geometriei în această etapă. |

T22 are 1779,724 m² în acoperișul final, față de 1688 m² în geometria diagnostică și 1793,799 m² în masca brută. Față de diagnostic, adaugă 127,203 m² și elimină 35,479 m². Atributul Hausdorff de 5,527 m corespunde diagnosticului; față de masca brută distanța este 4,862 m. Nu reprezintă o eroare măsurată față de un etalon independent și nu justifică singur acceptarea/respingerea. Amprenta estimată actuală are 1658,593 m²; cifra de 1663,2 m² din raportul narativ nu corespunde geometriei actuale. Retragerea fixă de 0,40 m rămâne ipoteză.

## 4. Ce înseamnă de fapt cele două variante și Lot5

`tools/run_comparison_a_vs_b.py` citește candidații regionali existenți și folosește loturile anterioare pentru evitarea suprapunerilor. Nu implementează împărțirea geografică în sferturi cerută, nu rulează o nouă detecție SAM2 și nu generează ferestre optice de 5 cm pentru confirmarea fiecărui obiect.

Opțiunea A selectează zece candidați după praguri fixe de arie, înălțime și compactitate, apoi îi ordonează după `h90*2 + pct_elev + compactness*50`. B aplică alte praguri fixe aceluiași pool. Codul nu învață aceste praguri din verdictele curate ale proprietarului; denumirea „calibrat” nu demonstrează antrenare sau calibrare evaluată. Atributul `false_positive_rate_pct: 0.0` este scris literal la linia 413, fără calcul din etichete independente.

Evaluarea vizuală a celor 10 cazuri A/Lot5:

- **T31–T34:** dreptunghiuri pe părți/aripi ale unui ansamblu mai mare cu acoperiș gri; completitudinea și identitatea fiecărui corp nu sunt demonstrate de selecție. T33 și T34 se suprapun cu 3,214 m² după regularizare.
- **T35:** acoperiș gri plauzibil, dar mai rămân mici joguri artificiale.
- **T36, T39, T40:** trepte evidente care nu corespund unor schimbări clare ale muchiei observate.
- **T37:** conturul taie acoperișul roșu vizibil; o parte a acoperișului rămâne în afara rezultatului. Nu poate fi declarat complet.
- **T38:** dreptunghi plauzibil pe acoperișul brun, în apropierea unei margini NoData; necesită verificarea acoperirii și identității.

Există astfel un lot nou real, dar nu zece obiecte „perfecte” sau acceptate. Numele straturilor cu `VALIDAT` nu înlocuiește `PENDING_OWNER_REVIEW`.

### REST_260 nu a fost demonstrat ca eliminat de B

REST_260:C1 din primul full-auto provine din setul `COMPLEX_REVIEW`, identificator `REF_TIER1_014:B00014`, mască brută de 5129,02 m². Comparația A/B citește numai `ROOF_CANDIDATES` regional. Intersecția acestei măști cu fiecare dintre cei 380 candidați regionali este zero, fără nicio geometrie identică; cel mai mare dintre cei 71 candidați respinși de B are numai 123,019 m².

Prin urmare, afirmația că filtrul B a eliminat tocmai REST_260 prin nDSM nu este susținută de intrări și ieșiri. Obiectul nu se afla în pool-ul testat. Ascunderea stratului istoric în QGIS nu constituie repararea lui.

## 5. Recalculare geometrică pe cele cinci seturi

| Set | Obiecte | Perechi cu intersecție > 0,05 m² |
|---|---:|---:|
| Lot3 v4 | 20 | 0 |
| Lot4 v4, inclusiv T22 | 10 | 0 |
| Full-auto inițial | 264 | 0 |
| A / Lot5 | 10 | 1 |
| B | 216 | 107 |

Pragul este analitic, fără statut de toleranță cadastrală. Full-auto are și intersecții foarte mici sub acest prag; lipsa suprapunerilor importante nu dovedește detectarea corectă. B are o intersecție maximă de 357,432 m². Full-auto păstrează un maxim de 758 noduri și 63 geometrii cu cel puțin un unghi deviat peste 1° de la un multiplu de 90°. Rezultatele confirmă problema deja ilustrată în [auditul anterior](../project_verification_20261018/README.md).

Gardurile de regularizare implementate nu coincid cu cerința strictă din mesajul 266 (Hausdorff ≤ 0,50 m și diferență arie ≤ 4%): codul permite, pe unele ramuri, 15%, 1,50/1,80 m și fallback bazat pe IoU ≥ 0,60 fără aceeași limită Hausdorff. Aceasta este o constatare prin citire; nu am schimbat parametrii în această reverificare.

Cei 3,427 s raportați pentru full-auto prelucrează candidați existenți și sunt calculați înaintea sincronizării QGIS. Nu măsoară detecția din ortofoto, execuția completă de la prompt sau controlul calității. Timpii A/B și scorul 0% nu constituie un benchmark de acuratețe independent.

## 6. Corectura auditului anterior și păstrarea stării

Excluderea datelor GIS și imaginilor din Git a fost **cerută explicit de proprietar** în conversația verificată. Nu trebuie descrisă drept neglijență a Antigravity. Efectul tehnic asupra portabilității și legăturilor README rămâne real. Proprietarul a autorizat ulterior separat publicarea checkpointului `77c1a0e`, inclusiv cele 16 artefacte selectate, în draft PR #4; nu anulăm acea autorizare sau acel PR prin această constatare.

Starea live actuală este diferită de snapshot-ul auditului anterior: `isDirty=True`. Lot4, Lot5/A și B216 sunt în lista efectivă a hărții; full-auto istoric REST264 este ascuns. Randarea separată a păstrat aceeași listă a hărții și starea nesalvată. Nu s-a salvat, reîncărcat, schimbat vizibilitatea ori înlocuit proiectul QGIS.

Fișierul de comparație GPKG apare modificat în working tree în această etapă; auditul nu îl include în commit și nu îi revendică modificarea. Hash-urile fișierelor Lot4 și comparație s-au schimbat între citiri. O a doua citire confirmă aceleași atribute și măsurători pe fiecare obiect, aceleași perechi de suprapunere și aceleași diferențe Lot4; nu pretindem identitate byte-cu-byte sau comparație WKB integrală. [Verificarea de consistență](consistency_recheck.json). Cele două unelte neversionate ale Antigravity rămân neatinse. Se salvează numai acest dosar cu cod de audit, documentație și JSON, plus corecturile indexului de documentație. Nicio geometrie, imagine nouă sau transcriere integrală nu este publicată.

Verificările dosarului au confirmat cele 20 hash-uri ale imaginilor locale, sintaxa celor trei scripturi, citirea JSON-urilor și legăturile locale ale documentelor editate. [Receipt](verification.json). Nu s-a reluat suita produsului pentru această modificare de documentație și audit.

## Punctul de continuare

Nu este necesară recrearea nucleului sau schimbarea workspace-ului. Următoarea reparație trebuie să urmărească forma observată și acoperirea completă, să controleze complexitatea și identitatea, să verifice suprapunerile după regularizare și să compare variantele pe aceeași zonă cu etichete independente. Trebuie confirmat traseul din aplicație spre această implementare. Acestea sunt lucrări rămase, nu reparații executate prin audit.
