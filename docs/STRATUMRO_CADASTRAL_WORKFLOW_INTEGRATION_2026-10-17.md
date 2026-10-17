# Continuare cadastrală: flux reutilizabil și limite de integrare

## Stare curentă

Identitatea platformei și direcția desktop au fost salvate în commit `b3896e8`. Lucrul curent rămâne cadastral; nu a fost începută o interfață nouă.

Implementare nouă: `stratum_ro/cadastral_roof_workflow.py`, expusă prin `PlatformService.create_cadastral_roof_workflow()` în `stratum_ro/api/service.py`. Este o intrare explicită, reutilizabilă de clienți CLI/API/desktop, fără importuri din scripturile de demonstrație sau dependență de o sesiune QGIS.

Acest flux este opt-in și lucrează pe candidați revizuiți. Nu schimbă ruta implicită a runnerului regional și nu introduce un detector RGB autonom. Nu validează automat georeferențierea norului; caller-ul declară compatibilitatea, iar proveniența rămâne în rezultat.

## Comportament implementat

- Scenă RGB, CRS proiectat verificat, transformare și mască de validitate explicită.
- Verificarea obiectului, ancorei, limitelor și contextului înainte de inferență; lipsa contextului și NoData blochează cazul.
- Date LiDAR opționale, toate grilele aliniate explicit; fără LiDAR se păstrează ruta optică.
- Promptul LiDAR este limitat la regiunea de căutare, fără salt într-o componentă îndepărtată.
- Encodează o dată per scenă; ID-urile corpurilor rămân distincte.
- Masca trebuie să acopere și ancora optică revizuită, nu doar seed-ul mutat de LiDAR.
- Rafinare și regularizare susținută. Parametrul exterior `max_vertices` este configurabil (20 în fluxul nou, 12 implicit în helperul istoric); se preferă în continuare forma cu cele mai puține noduri care trece verificările, fără forțarea unui dreptunghi pentru un corp complex.
- Acoperișurile întunecate cu suport Clasa 6 și înălțime nu sunt eliminate numai pentru că nu trec filtrul de culoare neutral/red.
- Scor redus, geometrie nerezolvată și atingerea marginii ferestrei sunt motive explicite de revizie.
- Rolul rezultatului: `OBSERVED_ROOF_HYPOTHESIS`. `ground_footprint=None` și `ground_status=NOT_MEASURED`. Nu se aplică automat retragerea de 0,4 m a streșinii în această rută.
- Verdictul rămâne `PENDING_OWNER_REVIEW`. Scorul SAM2 nu este acuratețe cadastrală.

## Execuție reală și reproducere

CLI: `tools/run_cadastral_roof_review.py`. Primește manifest și director nou, rezolvă sursele explicit, citește ferestre care acoperă complet contextul (floor pe început, ceil pe capăt), păstrează masca în GeoTIFF și exportă GPKG + JSON cu hash-uri pentru surse, manifest și model.

```powershell
venv/Scripts/python.exe tools/run_cadastral_roof_review.py --manifest workspace/reviews/fusion_complete_20261017/workflow_inputs_v2.json --output-dir workspace/reviews/UN_DIRECTOR_NOU --compare-to workspace/reviews/fusion_complete_20261017/fusion_complete.gpkg
```

Opțiunea `--compare-to` este numai control ulterior al diferențelor față de ipotezele precedente. Contururile precedente nu sunt input pentru model, nu sunt ground truth, iar comparația nu permite adoptare automată.

Au fost păstrate rulările `cadastral_workflow_20261017`, `cadastral_workflow_crops_20261017`, `cadastral_workflow_v2_20261017`, `cadastral_workflow_v3_20261017`, `cadastral_workflow_v4_20261017`. Primele rulări au demonstrat sensibilitatea SAM2 la context și pierderea unor detalii când regularizarea este prea restrictivă.

Ancora gri T17 din manifestul inițial era aproape de marginea nordică. Verificarea strictă de corespondență a respins-o; `workflow_inputs_v2.json` o mută în interiorul aceluiași acoperiș, păstrând ID-ul, obiectul și anvelopa. Manifestul inițial rămâne neschimbat.

Ultimul pachet: `workspace/reviews/cadastral_workflow_v4_20261017/`. Proiect separat de comparație: `StratumRO_flux_cadastral_comparatie.qgz`. Cyan = demonstrație precedentă, portocaliu = flux nou; ambele rămân neacceptate. Proiectul este construit și randat cu QGIS standalone prin `tools/build_cadastral_review_project.py`; nicio fereastră/proiect QGIS existent nu este modificat.

## Verdict vizual tehnic, fără acceptare în numele proprietarului

- T17:C1: contur ortogonal, dar curtea apare conectată cu exteriorul printr-o întrerupere a unei legături de acoperiș. Diferă de demonstrația cu curte închisă. Nu se promovează în locul ei.
- T17:C2: corpul gri rămâne separat și reține proeminențe; marginile necesită verificare.
- T18:C1: sunt recuperate mai multe aripi decât în demonstrația simplificată; identitatea anexelor și limitele necesită revizie, iar scorul optic este sub prag.
- T20:C1: contur optic disponibil fără LiDAR; accesul/scările și zona echipamentelor rămân ambigue.

Nu au fost create amprente la sol. Nu au fost schimbate acceptările loturilor 1/2 sau ale proprietarului. Nu declarați închisă problema topologiei T17 numai pentru că testele trec.

## Verificări și următoarea intervenție

41 teste relevante au trecut: 10 pentru workflow, 6 pentru ghidare, 7 pentru rafinare și 18 existente pentru simplificare/separare. Testele acoperă NoData înainte de model, pixeli negri valizi, lipsa LiDAR, corespondența obiectului, identități, encoding reutilizat, scor redus și acoperiș întunecat.

Următoarea corecție cadastrală trebuie să stabilizeze topologia și anexele între ferestre, apoi să demonstreze regresiile pe loturile acceptate înainte de schimbarea fluxului implicit. Uniformizarea generală SID/VRT/GeoTIFF și citirea adaptivă din sursa nativă rămân sarcini distincte, nefinalizate prin acest commit.
