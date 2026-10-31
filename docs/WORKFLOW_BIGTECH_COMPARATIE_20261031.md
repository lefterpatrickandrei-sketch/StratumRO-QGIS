# Workflow actual versus workflow cu modele big tech pe Colab A100 (2026-10-31)

Scop: ce putem rula pe A100 (40 GB VRAM) din ofertele Meta, Google, Microsoft, IBM, NVIDIA și Alibaba. Comparația se face cu antrenările deja făcute în acest proiect. Câștigurile propuse sunt **ipoteze**: se acceptă numai după ce sunt măsurate pe aceeași validare și verificate în QGIS.

## Workflow-ul actual și ce au arătat antrenările

| Etapă | Ce folosim | Unde rulează | Rezultat măsurat |
|---|---|---|---|
| Etichete | 137 ADMIS, 29 ELIMINAT, 12 negative, copaci din LiDAR (doar pentru antrenare) | local | 93 de clădiri de antrenare; aici e strangularea |
| Segmentare | UNet ResNet-34 (ImageNet), 3 ieșiri: acoperiș, margine, colț; ansamblu de 3 rulări | A100, ~6 min per rulare | IoU val 0,71 pe poligon, 0,83 pe pixel; 26 % din clădiri cu IoU ≥ 0,9 |
| Backbone mai mare | ConvNeXt-Small (ImageNet) | A100 | 0,22, apoi 0,42 după negativele de copac: mai slab |
| Rafinare cu SAM | SAM 2.1 Large, fără antrenare | local | +0,008 |
| Verdict și tip | Qwen3-VL-8B, zero-shot, apoi LoRA | A100, 4–10 min | Acord cu tine 0,57–0,61 (a răspunde mereu ADMIS ar da 0,76); recunoaște 95 % din copaci |
| Contur | Reguli: 90°, ocluzie cu LiDAR (înălțime + suprafață netedă), lipire pe streașină | local, 25 s | 91 % din vârfuri la 45°/90°, 0 suprapuneri |

Ce am învățat:
1. Cu puține etichete, un backbone generalist mai mare (ConvNeXt) a pierdut în fața ResNet.
2. SAM 2.1 folosit fără antrenare a adus aproape nimic.
3. VLM-ul învață copacii, dar nu distincția fină ADMIS/AJUSTARE din 31 de exemple.
4. Cele mai mari câștiguri au venit din regulile de contur și din etichetele corecte, nu din modele mai mari.

## Ce oferă big tech și se potrivește la 0,15 m

| Companie | Model sau unealtă | Pentru ce | De ce ar ajuta aici | Risc sau limită |
|---|---|---|---|---|
| Meta | **DINOv3 ViT-L/16 SAT-493M** (300M parametri; există și 7B) | backbone pentru segmentare | e preantrenat pe 493 milioane de imagini Maxar ortorectificate, deci cunoaște deja acoperișuri și copaci de sus; răspunde direct la lecția 1 | rezoluție de antrenare 0,6 m față de 0,15 m la noi (trebuie testat la 0,3–0,6 m); licență cu acces aprobat |
| Meta + WRI | **High-res canopy height** (DINOv2 + decodor, versiuni pentru aerian) | înălțimea copacilor doar din RGB | înlocuiește LiDAR la ocluzia de copac, deci merge în orice UAT fără LiDAR (scopul Fazei 1) | eroarea pe Cluj necunoscută; trebuie comparat cu nDSM-ul nostru |
| Meta | **SAM 3** (text: „building roof”) | a doua sursă de detecție | verifică clădirile ratate de UNet | fără dovezi pe aerian; aceeași lecție ca la SAM 2.1 |
| Meta | SAM 2.1 cu fine-tuning (LoRA) | rafinarea conturului | un studiu pe ortofoto coreean raportează o îmbunătățire clară după fine-tuning | doar dacă DINOv3 nu ajunge |
| IBM + ESA | TerraMind + **TerraTorch** | metodă de fine-tuning din configurație | antrenare reproductibilă | preantrenat pe Sentinel (10 m), nepotrivit la 0,15 m; un adaptor pentru clădiri NYC are IoU ~0,35 |
| Microsoft | **TorchGeo** | eșantionare spațială, benchmark | metodă standard de date și evaluare | ponderile sunt pentru NAIP (0,6–1 m), nu pentru 0,15 m |
| Microsoft | Florence-2 | VLM mic, ușor de antrenat | alternativă ieftină la Qwen pentru verdict | nu există fine-tuning pe clădiri; doar detecție orientată pe DOTA |
| Microsoft | Global ML Building Footprints | referință | verificare de completitudine | măsurat aici: IoU 0,30 |
| Google | Open Buildings, Earth AI | referință, model în cloud | – | Open Buildings nu acoperă Europa; Earth AI fără ponderi publice confirmate; cloud cere aprobarea ta (AGENTS.md) |
| NVIDIA | SegFormer (MiT-B5), C-RADIO, TAO | backbone alternativ, metodă de antrenare | SegFormer B5: 94 % IoU pe WHU într-un studiu | modelele TAO sunt pentru stradă, nu aerian; C-RADIO neverificat pe aerian |
| Alibaba | Qwen3-VL-8B | verdict, tip acoperiș | îl folosim deja | vezi lecția 3 |

## Workflow-ul propus pe A100 și comparația etapă cu etapă

| Etapă | Acum (antrenat, măsurat) | Propus (big tech) | Câștig așteptat (ipoteză) | VRAM / timp pe A100 |
|---|---|---|---|---|
| Etichete | 93 ADMIS de antrenare + negative | + cele 29 ELIMINAT ale tale + verdictele viitoare din QGIS | mai puține fals-pozitive | – |
| Segmentare | ResNet-34 ImageNet, IoU 0,71 | **DINOv3-SAT ViT-L înghețat** + capul nostru cu 3 ieșiri | ținta e IoU ≥ 0,78 și mai multe la ≥ 0,9 | ~20 GB, ~15 min |
| Copaci / ocluzie | nDSM LiDAR (doar Cluj) | **Meta canopy height din RGB**, LiDAR doar ca verificare | aceeași calitate fără LiDAR, deci generalizare | ~10 GB, ~5 min pentru AOI |
| Clădiri ratate | candidați LiDAR + VLM | **SAM 3 cu text** + verificare OSM/Microsoft | recall mai bun | ~15 GB, ~10 min |
| Contur | reguli (91 % la 90°) | păstrăm regulile | – | CPU |
| Verdict | Qwen3-VL LoRA (adaptorul pierdut) | Qwen3-VL LoRA cu adaptorul salvat; Florence-2 doar ca test | mai multe ELIMINAT recunoscute | ~25 GB, ~10 min |
| Tip acoperiș | profil LiDAR + VLM | același, plus clasificator mic pe DINOv3 după ce validezi tipuri | mai puține „o apă” greșite | mic |

Ordinea testelor, fiecare pe aceeași validare (31 ADMIS din nord + cele 29 ELIMINAT ale tale) și fiecare încheiat cu verificare în QGIS:
1. DINOv3-SAT / Meta SSL ViT-H/16 SAT (`SSLhuge_satellite.pth`).
2. Canopy height (`HighResCanopyHeight` sat & aerial).
3. SAM 3.
4. Fine-tuning SAM 2.1, doar dacă 1 nu atinge ținta.

Un model se păstrează numai dacă bate ansamblul actual.

## Rezultate măsurate pe Colab A100 (2026-10-31)

### Test 1: Meta SSL ViT-H/16 Satellite (`meta_sat_vith`, `SSLhuge_satellite.pth` înghețat + decodor UNet + stem CNN)
Raport complet: `workspace/colab_runs/run_metasat/loop_convergence_report.json` (20 epoci × 1280 cropuri, 6,3 min pe A100):

| Metrică (același split: 31 ADMIS val, 93 train) | Ansamblu ResNet-34 (actual) | ConvNeXt-Small | Meta SSL ViT-H/16 SAT (`meta_sat_vith`) | Verdict |
|---|---|---|---|---|
| **IoU pe pixel (val), model singur** | 0,78–0,82 (4 rulări ResNet-34) | 0,685 | 0,806 | la nivelul ResNet-34 |
| **IoU mediu pe poligon (`admis_iou_val`, n=31)** | model singur 0,58–0,73; ansamblu **0,71** | 0,42 | **0,5254** (median 0,5295) | pierde conturul fin la 0,15 m (patch 16 la 0,30 m = 4,8 m/token) |
| **Clădiri val cu IoU ≥ 0,90** | 13–23 % singur, 26 % ansamblu | 0 % | 6,45 % | sub ResNet-34 |
| **Clădiri val detectate (IoU ≥ 0,50)** | 65–84 % singur | 35,5 % | 54,84 % | sub ResNet-34 |
| **90°/45° (`ortho_45_90_share`)** | **91 %** | – | 78,76 % | – |
| **Negative grele atinse (`hard_negatives_hit`)** | **1–3** | – | 6 | – |

**Concluzie Test 1:** Preantrenarea pe satelit (Maxar 0,5 m) a ajutat clar față de ConvNeXt-Small ImageNet (`0,53` vs `0,42` IoU poligon val; `0,806` vs `0,68` IoU pixel), însă token-urile ViT-H/16 rămân prea grosiere pentru marginile de streașină la 0,15 m. **Nu bate ansamblul ResNet-34 (0,71 IoU poligon val) -> nu înlocuiește segmentatorul actual.**

### Test 2: Meta + WRI High-Resolution Canopy Height din RGB vs LiDAR nDSM Cluj
Raport complet: `workspace/colab_runs/run_canopy/canopy_report.json` (evaluat față de `cluj_ndsm_1m.tif` pe întregul AOI):

| Variantă model & GSD | MAE pe copaci (m) | Bias pe copaci (m) | Corelație Pearson `r` | Înălțime medie pe sol / pe acoperiș ADMIS (m) | Mască vegetație înaltă (`CHM ≥ 2,5 m`) vs LiDAR: Precizie / Recall / IoU | Baseline doar culoare (fără CHM): Precizie / Recall / IoU | Timp AOI |
|---|---|---|---|---|---|---|---|
| `sat_0.50m` (GPU) | 6,95 m | -4,47 m | 0,461 | 0,15 m / 0,06 m | **P = 0,753** / R = 0,492 / **IoU = 0,423** | P = 0,399 / R = 1,000 / IoU = 0,399 | 3,3 s |
| `aerial_0.50m` + RNet (CPU int8) | 7,00 m | -6,52 m | **0,540** | 0,07 m / **0,02 m** | **P = 0,790** / R = 0,472 / IoU = 0,419 | P = 0,399 / R = 1,000 / IoU = 0,399 | 26,5 s |
| `sat_0.30m` (GPU) | 7,75 m | -2,39 m | 0,415 | 0,22 m / 0,05 m | P = 0,742 / **R = 0,529** / **IoU = 0,447** | P = 0,381 / R = 1,000 / IoU = 0,381 | 6,6 s |
| `aerial_0.30m` + RNet (CPU int8) | 6,83 m | -5,42 m | 0,419 | 0,08 m / **0,02 m** | P = 0,750 / R = 0,518 / IoU = 0,442 | P = 0,381 / R = 1,000 / IoU = 0,381 | 62,2 s |

**Concluzie Test 2:**
- **Punct tare critic:** Modelul dă aproape **zero fals-pozitive pe acoperișurile ADMIS** (`owner_roof_mean_chm_m = 0,02–0,06 m`) și pe sol (`0,07–0,22 m`), și dublează precizia măștii de copac față de simpla culoare verde (`0,75–0,79` vs `0,38–0,40`), separând iarba joasă de coroanele de copaci.
- **Limită:** Subestimează sistematic înălțimea absolută a copacilor urbani din Cluj cu `-2,4 .. -6,5 m` (MAE ~6,9 m), deci la pragul `CHM >= 2,5 m` prinde doar ~50 % din coroane (`recall = 0,49–0,53`). Pentru UAT-urile fără LiDAR este util ca **filtru de separare iarbă vs arbore** (cu prag coborât la `1,0–1,5 m`), dar unde există LiDAR nDSM, LiDAR-ul rămâne net superior.

Surse: [DINOv3 SAT-493M](https://huggingface.co/facebook/dinov3-vitl16-pretrain-sat493m), [Meta canopy height](https://gishub.org/blog/canopy-height), [SAM 3](https://docs.ultralytics.com/models/sam-3), [TerraTorch](https://research.ibm.com/publications/terratorch-an-open-source-framework-for-fine-tuning-geospatial-foundation-models), [TerraMind NYC](https://huggingface.co/msradam/TerraMind-base-Flood-NYC), [TorchGeo](https://torchgeo.readthedocs.io/en/stable/tutorials/pretrained_weights.html), [Florence-2 DOTA](https://huggingface.co/Qingyun/Florence-2-large-DOTA-v1.0-lmmrotate), [SegFormer building extraction](https://pubmed.ncbi.nlm.nih.gov/41359638/), [VFM building comparison](https://avesis.ktu.edu.tr/yayin/b5ae33a7-1be8-421f-9f54-0e28b2986525/comparative-analysis-of-vision-foundation-models-for-building-segmentation-in-aerial-imagery), [Google Earth AI](https://arxiv.org/pdf/2510.18318), [Microsoft footprints](https://github.com/microsoft/globalmlbuildingfootprints).

### Verificare independentă (Claude Code, 2026-10-31, după rularea continuată de agentul Antigravity)

- Cifrele din cele două teste corespund fișierelor din `workspace/colab_runs/run_metasat` și `run_canopy`. Tabelul de mai sus a fost corectat față de varianta inițială:
  - valorile ConvNeXt erau 35,5 % detectate și 0 % la IoU ≥ 0,9, nu 45 % și 6,5 %;
  - 0,83 pe pixel aparținea unei singure rulări, nu ansamblului.
- **Comparația corectă e model singur contra model singur.** Meta ViT-H, cu 0,525, e sub cea mai slabă rulare ResNet-34 (0,58). La pixel e egal (0,806), deci pierde la contur: un token ViT acoperă 4,8 m.
- **Recall-ul 1,000 al bazei pe culoare nu e un rezultat.** Referința LiDAR folosea și condiția de culoare. Remăsurat față de o referință fără culoare (LiDAR ≥ 2,5 m, în afara acoperișurilor tale):

| Mască (sat 0,30 m) | Precizie | Recall | IoU | Pe acoperișurile tale |
|---|---|---|---|---|
| doar culoare | 0,379 | 0,534 | 0,285 | 3,3 % |
| CHM ≥ 1,0 m | 0,712 | 0,365 | 0,318 | 1,9 % |
| CHM ≥ 1,5 m | 0,721 | 0,351 | 0,309 | 1,5 % |
| CHM ≥ 2,5 m | 0,731 | 0,331 | 0,295 | 1,1 % |

- Precizia se dublează, ceea ce e real și util. Coborârea pragului la 1,0–1,5 m **nu** recuperează recall-ul (0,33 → 0,37), deci recomandarea inițială nu se confirmă.
- Concluzie: modelul de înălțime poate *confirma* un copac fără LiDAR, dar ratează ~2/3 din coroane. Nu înlocuiește LiDAR-ul pentru ocluzie.
