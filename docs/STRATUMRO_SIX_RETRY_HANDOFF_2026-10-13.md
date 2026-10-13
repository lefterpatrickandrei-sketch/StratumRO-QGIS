# StratumRO — reluarea celor șase cazuri respinse

> Verdict uman ulterior, identificat explicit de proprietar ca `six_before_after.png`: **T05/T06/T07 acceptate; T08/T09 respinse; T10 parțial executat, neacceptat ca rezultat final**. Stările PENDING din artefactele de inferență sunt istorice; sidecarul `owner_feedback.json` este autoritativ pentru verdict. Progresul este inclus în checkpointul Git descris în [STRATUMRO_GIT_CHECKPOINT_2026-10-13.md](STRATUMRO_GIT_CHECKPOINT_2026-10-13.md).

## Verdictul proprietarului și directorul curent

Proprietarul a confirmat **8/8 imagini acceptate în primul lot**, inclusiv B00005 separat în două corpuri. Din cele10 imagini suplimentare, **T01–T04 sunt acceptate; T05–T10 sunt respinse**. Acestea sunt verdicte vizuale de dezvoltare, nu măsurători de precizie. Feedbackul actualizat se află în `workspace/reviews/retry_six_release_20261013/owner_feedback.json`. Nu păstrați vechiul7/8 ca verdict curent și nu declarați noile reluări acceptate fără feedback nou.

Director autoritativ pentru noile reluări: **`workspace/reviews/retry_six_release_20261013/`**. Celelalte directoare `retry_six*20261013` sunt experimente intermediare. Loturile acceptate anterior sunt păstrate în directoarele originale.

**Actualizare afișare QGIS:** proiectul `inspectie_completa_8_orto_loturi.qgs` înlocuiește copia limitată la3 rasters pentru inspecție. Sunt încărcate toate8 tile-urile native disponibile, grupate `ORTOFOTO COMPLETE - 8 tile-uri`, cu etichete `Lot1` și `T01–T10` pe straturile de rezultate. `lot2_case_correspondence.json` verifică identitatea surselor înainte/după: lista cazurilor T01–T10 nu a fost schimbată. Fundal complet nu înseamnă rulare nouă de extracție pe întreaga zonă. `full_ortho_readback.json` confirmă8 rasters valide și redeschiderea proiectului cu17 straturi.

## Defectul identificat și rectificarea reală

Mai multe rezultate vectorizate distincte moșteneau același `raw_id` și același punct al unei măști părinte mari. Pentru T05–T10, punctul moștenit era aproximativ `(391151.04,585646.157)`, în afara contururilor copiilor. De exemplu T05 este între x390850.54..390887.5; SAM2 era ghidat către altă zonă, apoi diagnosticul anterior revenea la conturul LiDAR zimțat. Unele contururi erau și parțial în afara tile-ului ales după regiunea părinte. Acestea sunt defecte de reluare/lineage, nu o dovadă că SAM2 nu poate delimita acele acoperișuri.

Corecția generează puncte **în interiorul fiecărui corp**, cu suport RGB, nDSM și class6; verifică acoperirea imaginii și alege în script tile-ul nativ care acoperă integral obiectul plus context. Noul modul generic este folosit atât de experiment, cât și de pipeline-ul StratumRO.

Un al doilea defect: media de înălțime a unui component amesteca acoperișuri joase și înalte. La T05, componenta medie era aproximativ8.64m, dar în jurul punctului de pe anexa albă mediana nDSM era aproximativ4.76m. Filtrarea după media părintelui elimina anexa. Codul folosește înălțimea locală pentru amestecuri, iar pentru componente coerente păstrează media robustă a componentei. Nu confundă această segmentare cu identitatea cadastrală a construcțiilor.

## Rezultatele reluării

- **T05:** corpul principal gri primește o formă simplă în L; anexa joasă albă este recuperată separat. Ambele ipoteze rămân în export și în pipeline, cu lineage către părinte și către măștile noi.
- **T06:** acoperișul roșu este recuperat separat; banda de teren/vegetație a măștii părinte nu mai intră în conturul propus.
- **T07:** forma în U păstrează golul deschis dintre aripi. Primul experiment cu dreptunghi umplea curtea și a fost respins de Codex. Variantele finale trebuie inspectate în `six_before_after.png`.
- **T10:** acoperișul este resegmentat dintr-un punct propriu. Geometria exactă și numărul de noduri sunt consemnate în GPKG/manifest; verificarea proprietarului este încă în așteptare.
- **T08/T09:** `NO_SUPPORTED_ROOF_SEED`. Nu există contur nou susținut în această reluare. Măștile vechi includ predominant teren/vegetație și sunt retrase din stratul propus, păstrate pentru revizie. **Acest rezultat nu demonstrează absența oricărei construcții în vecinătate**; inclusiv mica structură de la marginea T08 rămâne nerecuperată. Nu inventați un dreptunghi și nu numărați aceste două cazuri drept clădiri rectificate.

Noile geometrii sunt **IMPLEMENTATE / TESTATE / MĂSURATE și inspectate vizual**, nu aprobate de proprietar și nu validate terestru. Compararea este cu ortofoto, fără desenarea după referințele GMW.

## Implementarea salvată în repository

- `stratum_ro/roof_retry.py`: `roof_retry_prompts`, `trim_retry_roof_surface`, `retry_roof_geometry`. Module locale deterministe, segmenterul este primit ca argument. Nu citesc referințe, ID-uri de caz sau coordonate hardcodate.
- Semințe: pixeli RGB neutri sau roșii/maronii, elevare>=2m, suport class6, excluderea culorilor de vegetație. Componente de semințe>=8m2, maximum4 puncte/componente, fiecare punct verificat în poligonul copil și în imagine.
- Segmentare nouă pe fiecare sămânță, decupare pe înălțime și culoare; părțile gri ale unui acoperiș colorat sunt păstrate când class6 și înălțimea le susțin. Golurile spectrale<=2m2 pot fi închise; golurile mai mari se păstrează pentru verificare. Acestea sunt praguri de dezvoltare, nu toleranțe cadastrale.
- Forme simple din `roof_simple_geometry.py`; candidații recuperați trebuie să aibă suport optic, fracție RGB de vegetație<.35 și fracție de returns class6>.15. Aceste praguri sunt rutare de ipoteze, nu aprobare. Se păstrează toate încercările, inclusiv cele nereușite.
- `stratum_ro/roof_body_recovery.py`: reluare pentru copii cu punct moștenit în afară, `NEEDS_REVIEW` sau `LIDAR_DIRECT`, în modul `simple_edges=True`. Păstrează `raw_id` părinte, `retry_raw_id` nou, punctul nou, scorul măștii noi, `sam2_score_scope=LOCAL_CHILD_MASK`. Recalculează geometria/solul estimat/QA inclusiv când forma rămâne aceeași, dar scorul se schimbă. Rutarea folosește masca nouă, nu masca veche a părintelui.
- Toți corpurile distincte recuperate sunt păstrate, nu doar cel mai mare. Pentru multiple corpuri, `body_count`, `body_index` și revizia identității sunt obligatorii. Testul de integrare verifică explicit păstrarea ambelor corpuri.
- Modul CLI existent: `--proposal-policy roof_bodies --simple-roof-edges`. Implicit rămâne `legacy`. Nu s-a executat o rulare completă a celor8 tile-uri cu acest mod final.
- `scripts/recover_six_rejected_roofs.py`: runner reproductibil pentru lotul respins, alegerea tile-ului după acoperire completă, SAM2 nou, exportul tuturor încercărilor, imagini.

## Artefacte și reluare

În directorul curent: `retry_six.gpkg` (`CORPURI_RECTIFICATE`, `TOATE_INCERCARILE`, `RESPINSE_ANTERIOR`), `retry_report.json`, `six_before_after.png`, `T05.png`..`T10.png`, `inspectie_rectificari_sase.qgs`, `qgis_canvas.png`, `qgis_readback.json`, `owner_feedback.json`, `verification_manifest.json`, `unit_tests_final.log`. GPKG conține ipoteze de acoperiș, nu contururi la sol măsurate.

Din `C:\Users\lefpa\Downloads\QGIS-AI`, folosiți un director nou:

```powershell
venv\Scripts\python.exe scripts/recover_six_rejected_roofs.py --output-dir workspace/reviews/retry_six_next_run
venv\Scripts\python.exe -m unittest discover stratum_ro/test
```

Testele acoperă semințe proprii în copil, acoperiș neutru/roșu, excludere vegetație/teren, lipsă acoperire imagine, imutabilitate, curte mare păstrată, goluri spectrale mici, forma în U cu parte gri susținută, separarea anexei joase de acoperișul înalt, punct local cu valoare de înălțime atipică, înlocuirea lineage-ului optic și păstrarea tuturor corpurilor recuperate. **Numerele finale și timpul exact sunt autoritative în `verification_manifest.json` și `unit_tests_final.log`.**

## Git și continuarea de către alți agenți

Codul, testele, MD-urile și dovezile sunt în repository-ul StratumRO. Git a fost inspectat; checkout-ul conține și modificări anterioare, inclusiv livrabile active mari. Nu resetați checkout-ul și nu atribuiți întregul diff acestui lot. `implementation_checkpoint.patch` păstrează pentru revizuire diferențele surselor relevante și fișierele noi; nu este un commit și nu trebuie aplicat peste checkout-ul curent care conține deja modificările. Nu s-a făcut push.

Referințele înghețate GMW și fișierele active `workspace/output/cladiri_stereo70.gpkg`, `workspace/output/cadastru_ancpi.dxf` rămân intacte în acest lot (hashuri în manifest). Proiectul QGIS a fost salvat ca o copie nouă, fără suprascrierea proiectului inițial cu stare nesalvată.

Următorul agent: citiți acest MD, manifestul, feedbackul și inspectați imaginile; obțineți verdictul pentru reluări; tratați separat omisiunea structurii mici T08; verificați modul complet pe AOI separat înainte de schimbarea implicitului. Nu repetați vechiul diagnostic cu punctele moștenite din afara copiilor. Nu prezentați retragerea presupusă de0.4m a streșinii ca măsurătoare la sol.

Antigravity a scris cele8 teste ale semințelor în conversația `4f6cd8a9-eb2b-458d-af48-629b0c3004ee`,SUCCESS,36.97s. Codex a implementat și integrat reluarea, a executat testele și inferențele reale și a inspectat imaginile. Workerul este terminat; nicio automatizare nu rămâne în execuție.
