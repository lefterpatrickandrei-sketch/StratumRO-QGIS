# Rafinarea opțiunii B — implementare și dovezi

Cerere: rafinarea B în StratumRO, cu toate etapele vizibile, cercetare externă prudentă și checkpointuri Git. Baza este `90c484e`. Nu se înlocuiesc rezultatele acceptate sau geometria istorică. Datele GIS și imaginile noi rămân locale, documentația/codul/configurația și manifestele intră în Git, conform politicii explicite din conversația reconciliată.

## Etape și criterii

1. **Inventar și date:** păstrează intrarea B216 și cei 71 respinși; citește mozaicul existent cu mască și nDSM ca evidență contextuală, fără a considera înălțimea dovadă de clădire. Leagă propunerile de observațiile regionale originale numai cu corespondență geometrică explicită.
2. **Identitate:** reutilizează deduplicarea din `regional_roofs.py` cu praguri prudente și lineage. Nu uni automat corpuri și nu tăia poligoanele doar pentru a ascunde suprapunerile. Păstrează separat conflictele nerezolvate.
3. **Formă:** reutilizează `roof_simple_geometry.py`; adaugă garduri fizice explicite pentru aria modificată și distanța conturului. Păstrează curțile și anexele, nu forța toate formele la 90°. Observația brută, forma propusă și decizia se salvează separat.
4. **Rafinare SAM2:** recitește ferestre cu context peste cusături, verifică validitatea și creează puncte automat din evidență. Folosește predictorul existent; nu declara aceste puncte drept selecții revizuite de om. Păstrează toate încercările, inclusiv măștile respinse și motivul. Inferență reală numai după verificările de intrare și disponibilitatea GPU; nu se fabrică recorduri de preflight pentru a trece o poartă.
5. **QA și integrare:** verifică suprapunerile după schimbarea geometriei, NoData, complexitatea, identitatea și posibilitatea trunchierii. Expune același flux prin `PlatformService` și CLI; o funcție de serviciu nu dovedește integrarea completă a agentului UI.
6. **Dovezi:** pachet nou cu straturi pe etape, planșe înainte/după și index pentru toate obiectele, încărcat ca grup în proiectul comun fără ștergerea grupurilor vechi. Nu salva automat starea nesalvată a utilizatorului. Teste sintetice semnificative și verificare vizuală pe rezultate reale. Nicio acuratețe/recall fără etichete independente.

## Reutilizare și cercetare

- `OrthoMosaic`, `sample_evidence`, `deduplicate_candidates`: `stratum_ro/regional_roofs.py`.
- `simple_roof_geometry`: `stratum_ro/roof_simple_geometry.py`.
- `SAM2BuildingSegmenter` și `predictor`: `stratum_ro/sam2_engine.py`.
- Fluxul revizuit `CadastralRoofWorkflow` cere explicit selecție umană. Nu se setează `reviewed=True` pentru a procesa automat B.
- [LiDAR + SAM, Ji et al. 2024](https://mdpi-res.com/d_attachment/remotesensing/remotesensing-16-02661/article_deploy/remotesensing-16-02661.pdf): justifică explorarea indiciilor automate, nu transferă performanța la Cluj.
- [POL, Schuegraf et al. 2024](https://isprs-annals.copernicus.org/articles/X-2-2024/217/2024/): orientare înainte de regularizare; nu se copiază implementare sau performanță fără test.
- [SAMPolyBuild, codul autorilor](https://github.com/wchh-2000/SAMPolyBuild): alternativă de benchmark ulterior; fără descărcări sau instalare în această etapă.
- [SAM2 oficial](https://github.com/facebookresearch/sam2): se utilizează implementarea și checkpointul locale existente.
- [Rasterio mask](https://rasterio.readthedocs.io/en/stable/api/rasterio.mask.html): masca explicită trebuie păstrată; valorile umplute nu sunt observații.
- [Shapely coverage_simplify](https://shapely.readthedocs.io/en/stable/reference/shapely.coverage_simplify.html): necesită acoperire fără suprapuneri și muchii potrivite; B nu îndeplinește premisa, deci nu este aplicată direct.

Nu se execută scripturi de instalare de pe internet. Nu se încarcă imagini sau date private pe servicii externe. Ponderile existente nu sunt înlocuite.

## Stare la început

Repository comun `C:/Users/lefpa/Downloads/QGIS-AI`; QGIS are proiectul comun deschis, modificări nesalvate, fără layere în editare. GPKG-ul comparației este deja modificat și nu este adoptat. Cele două unelte neversionate ale Antigravity rămân neatinse. Nu există proces Python de inferență identificat pe GPU la verificare. PR #4 rămâne draft; publicarea acestui progres nu este implicită.
