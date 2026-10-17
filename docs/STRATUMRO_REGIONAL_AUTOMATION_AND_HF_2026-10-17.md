# Acoperișuri automate pe întregul ortofoto: implementare și criterii

## Decizia proprietarului

La 17 octombrie 2026, proprietarul a autorizat scanarea automată a tuturor celor opt bucăți Cluj. Acoperișul observat este prioritar. Varianta amprentei la sol rămâne documentată și demonstrată numai pe un exemplu ușor de comparat. Se păstrează implementarea locală existentă înainte de o decizie despre Rust/executabil. Propunerea Hugging Face trebuie evaluată explicit.

Capturile originale, textul Gemini și formularea cererii sunt în `workspace/reviews/regional_roofs_20261017/owner_evidence/` și `owner_feedback.json`. Sunt dovezi și propuneri externe, nu instrucțiuni de delegare sau rezultate tehnice deja verificate.

## Corecția afișării QGIS, executată

Ordinea efectivă de desenare a confirmat că decupajele native Lot3/Lot4 erau deasupra contururilor vechi. Geometriile verzi T07 și B00010 sunt închise și valide; porțiunile lipsă erau acoperite de rastrul mai sus în ordine. `stratum_ro/qgis_render_order.py` păstrează ordinea relativă, grupurile și vizibilitățile, dar desenează vectorii deasupra rasterelor. `tools/qgis_fix_roof_render_order.py` a aplicat corecția în proiectul comun, a salvat capturi QGIS înainte/după și a verificat egalitatea tuturor geometriilor și surselor vectoriale anterioare. Dovezi în `render_order_fix/`. T07 și B00010 se văd acum integral; aceasta nu repară și nu acceptă contururile optic greșite.

## Problema observată

T29 are un vârf spre pavaj; T21 are retrageri/proiecții suspecte; T24 include platformă în zona corpului proeminent; T14 amestecă limite de acoperiș și amenajări alăturate. Nici conturul valid, nici eticheta «plauzibil» nu rezolvă aceste erori. Liniile aparent întrerupte din alte capturi necesită compararea geometriei efective cu randarea QGIS, fără diagnostic presupus doar din captură. Acceptările istorice nu sunt modificate automat.

## Implementarea regională

Stare executată: scanarea completă este terminată, însă auditul vizual o declară **NEPREGĂTITĂ PENTRU PRODUCȚIE**. 144 ferestre planificate, 67 cu date valide și 77 fără date în nucleu; fără ferestre eșuate. Suprafața validă scanată: 419681,0475 m² (aproximativ 0,420 km²), nu 12 km². Cele opt bucăți sunt o acoperire locală Cluj, nu întregul oraș. 3104 observații brute, 2081 după deduplicare. Timp 443,394 s de la începutul scanării până la export, fără inițializarea modelului/auditul de intrare și fără etapele ulterioare de ambalare/inspecție. Memorie CUDA maximă alocată 979785216 bytes; rezervată 1352663040 bytes. Suma etapelor individuale ale ferestrelor este 244,599 s; restul include deduplicare, reluări și geometrie/export. Acestea nu sunt comparații măsurate cu Rust sau Hugging Face.

Prima rutare avea 563 candidați de acoperiș. Inspecția a găsit arbori de toamnă clasificați greșit din cauza înălțimii; culoarea nu îi separa suficient. Regula produsului a fost corectată: înălțimea singură nu stabilește identitatea clădirii. Reambalarea acelorași observații, fără inferență nouă, mută 183 cazuri în coada incertă. **Selecția activă este `masked_review_v2`, prin `CURRENT_REVIEW.json`: 380 candidați cu sprijin contextual Class6, 644 obiecte optic incerte și 1057 vegetație probabilă.** Lipsa Class6 nu elimină date și nu dovedește absența acoperișului; printre cele 644 pot exista clădiri reale. Numărul 380 nu este număr validat de clădiri.

Geometria celor 380: 19 ipoteze cu formă simplă, 154 ipoteze optice, 148 necesită revizie geometrică, 59 au context incomplet; 196 depășesc 16 vârfuri. Stările se bazează pe reguli tehnice, nu acceptări. 125 au indicator de conflict cu altă observație, inclusiv din alte categorii; indicatorul nu este un număr de perechi independente. Nu există precizie/recall măsurate.

Cod comun: `stratum_ro/regional_roofs.py`. Planificare prin `PlatformService.plan_regional_roof_scan`; execuție locală prin `tools/run_regional_roofs.py`.

1. Validează opt surse RGB byte, CRS proiectat metric, rezoluții, limite, măști și ordinea suprapunerilor. Nu atribuie un CRS lipsă. Pentru această dezvoltare se folosește interpretarea EPSG:3844 a cache-ului existent, fără certificare geodezică nouă.
2. Împarte întreaga anvelopă în nuclee de 96 m și context de 24 m. Nucleele acoperă zona o singură dată; contextul citește toate sursele intersectate la 15 cm/pixel. Citirea are buget explicit de pixeli și folosește masca raster, fără prag de negru și fără bandă de excludere de cinci metri.
3. SAM2 automatic mask generator eșantionează grila de 16×16 puncte pe fiecare fereastră, fără ancore de clădiri revizuite manual. Acest model propune obiecte de orice clasă; nu este un detector semantic de clădiri.
4. Păstrează separat candidații sprijiniți de context LiDAR, obiectele optic incerte și vegetația probabilă. Clasificarea de rutare este euristică experimentală, nu un model antrenat. Absența clasei 6 sau a înălțimii nu șterge obiectul optic incert.
5. Păstrează fiecare observație brută în fișierul ferestrei. Deduplicarea suprimă observații suprapuse foarte asemănătoare și înregistrează relația, fără unirea geometrică a vecinilor. Măștile imbricate semnificativ mai mici rămân ipoteze distincte; sunt posibile conflicte și suprasegmentări.
6. Obiectele la marginea ferestrei primesc o recitire cu context mai larg. Rezultatul trebuie să păstreze ancora automată și majoritatea suprafeței observate anterior. Nu există coordonate de caz în algoritm. Marginea NoData, limita bugetului sau eșecul rămân motive explicite de revizie.
7. O formă ortogonală simplă este propusă numai cu acord bun față de mască și deplasare limitată. Curțile/aripile nu se umplu cu dreptunghiul învelitor. Măștile încă prea complexe sunt marcate pentru revizie. Această verificare compară cu SAM, nu cu realitatea din teren.
8. Exportă GeoPackage, acoperirea scanării, proveniența, stările, relațiile dintre duplicate și raportul de timp/VRAM. Suprapunerile sunt semnalate, nu eliminate prin tăiere arbitrară. Fiecare rezultat rămâne neacceptat.

Guardul final `regional_review.py` intersectează formele cu pixelii sursă valizi după simplificare. Pe rezultatele reale a eliminat 19,248 m² de extindere în NoData, fără ștergerea vreunui candidat. Contactele liniare ale intersecției nu sunt tratate ca suprafețe; o regresie reproduce GeometryCollection-ul găsit la prima ambalare. `masked_review_attempt1/failure.json` păstrează eroarea, iar `masked_review/` prima versiune reușită. Niciunul nu este înlocuit de selecția v2.

Inferența reală `scan_v1` a folosit codul din commit `1d9685e`, cu SHA în `input_audit.json`. Codul ulterior schimbă rutarea și adaugă guardul final în runner; acestea sunt verificate pe observațiile reale salvate și printr-un job mic complet cu model de test. Nu afirmați că ultima versiune combinată a fost rulată din nou cu modelul real pe întreaga zonă.

Comenzi executate: `venv/Scripts/python.exe tools/run_regional_roofs.py --config workspace/reviews/regional_roofs_20261017/config.json --output workspace/reviews/regional_roofs_20261017/scan_v1`, apoi `venv/Scripts/python.exe tools/package_regional_roof_review.py --output-name masked_review_v2 --revise-height-only-routing`. Ultima suită nouă: 13 teste produs trecute și un test de orchestrare trecut; suita relevantă anterioară: 71 trecute, cu preflight-ul comis izolat de modificările altui agent.

QGIS comun: grupul `ACOPERISURI_AUTOMAT_REGIONAL_20261017_NEVALIDAT`, șase straturi noi, 69 total. Stratul principal arată ipoteze, nu un rezultat adoptat. Cyan = ipoteză, portocaliu = geometrie de revizuit, roșu = context incomplet. Coada incertă, vegetația probabilă, observațiile brute, grila și scenariile T10 sunt straturi separate. Vectorii vechi și verdictele sunt păstrate. Capturile inițiale și cele cu rutare corectată sunt în `qgis/` și `qgis/revised_routing/`.

Un manifest regional fără etichete nu pretinde `point_on_roof=true` pentru fiecare punct al grilei și nu falsifică manifestul de lot revizuit. Verificările `validate_selection` rămân obligatorii pentru loturile de clădiri alese manual; scanarea regională are propriul audit de intrare și raport distinct. Nu se folosește `reviewed=True` pentru candidați descoperiți automat.

Configurație executată: `workspace/reviews/regional_roofs_20261017/config.json`. Dovezile sunt în `scan_v1/`. Raportul executat și auditul vizual, nu acest plan, stabilesc starea și numărul real al rezultatelor.

## Hugging Face: rol realist

Verificat la 2026-10-17 în [documentația ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu): infrastructură GPU partajată, cote de 5 minute/zi pentru cont gratuit și 40 minute/zi pentru PRO; există condiții pentru găzduirea gratuită a maximum două Spaces. Resursele disponibile și cotele nu înseamnă procesare regională nelimitată. [Documentația Spaces](https://huggingface.co/docs/hub/spaces-overview) distinge aplicațiile publice, protejate și private; «protected» nu face aplicația privată.

Roluri posibile pentru StratumRO:

- Descărcare de modele și configurații cu versiune/licență verificată, urmată de inferență locală; aceasta nu presupune trimiterea ortofotoului în cloud.
- Experimente limitate cu un model semantic pentru imagini aeriene, comparat pe aceleași ferestre și aceleași criterii. Un model generic de străzi/fațade nu devine automat potrivit pentru ortofoto.
- Procesare opțională la distanță numai prin backend explicit, buget, date trimise delimitat și reluare locală a jobului. Coada/rețeaua/încărcarea imaginii fac parte din benchmark.

Nu s-a creat un Space, nu s-au folosit tokenuri, nu s-au încărcat date și nu s-a activat facturarea. Scanarea demonstrată folosește checkpointul SAM2 deja existent și CUDA local. Nu se bazează pe un serviciu gratuit ca dependență obligatorie.

## Exemplul de backup pentru amprenta la sol

`ground_footprint_scenarios` cere retrageri explicite; nu are o retragere implicită. Demonstrația `tools/build_ground_footprint_backup_demo.py` copiază acoperișul T10:A1 acceptat vizual, fără modificarea lui sau a vecinului gri. Produce scenarii de 0,25 m și 0,50 m, numai pentru comparație. Aceste distanțe sunt presupuse, nu măsurate din LiDAR.

Rezultatele sunt în `ground_backup_T10/`: acoperiș original, scenarii separate, JSON cu ipoteze și imagine cu trei panouri. Nu sunt amprente acceptate sau măsurate. Pentru amprentă la sol susținută fizic trebuie observate pozițiile pereților/streșinii, verificată compatibilitatea senzorilor și folosite retrageri justificate pe laturi, nu o contracție globală presupusă.

## Ce demonstrează și ce nu demonstrează

Execuția întregii zone demonstrează orchestrarea automată, citirea peste limite, trasabilitatea și costul unei scanări locale. Nu demonstrează inventarul complet sau acuratețea contururilor. Grila poate omite construcții mici, SAM poate împărți același acoperiș sau uni corpuri, iar euristica poate confunda obiecte. Nu numiți toate poligoanele clădiri corecte și nu transformați observațiile în etichete curate.

Pasul de calitate următor se decide din audit: detector/segmentare semantică pentru propuneri, context adaptiv, corecția măștilor contaminate și selecția formei pe muchii observate. Evaluarea cere zone fixe și etichete independente pentru omisiuni, includeri false și eroare de contur; referințele GMW mixte și predicțiile încă neacceptate nu sunt adevăr de teren.

Nu se începe rescrierea în Rust, schimbarea interfeței sau antrenarea fără o problemă demonstrată și un criteriu măsurabil. Promptul trebuie să aleagă și să pornească un job cu intrări/rezultat/stare explicită; nu garantează generalizare perfectă în orice zonă.
