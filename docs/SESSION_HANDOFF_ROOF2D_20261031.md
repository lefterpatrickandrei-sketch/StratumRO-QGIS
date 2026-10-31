# Predare completă: pipeline-ul 2D de acoperișuri (sesiunile 2026-10-30 … 31)

Pentru orice agent sau sesiune care continuă lucrul (Claude Code, Antigravity/Gemini, Codex, Kilo). Citește întâi [AGENTS.md](../AGENTS.md). Totul de mai jos e verificat în repo la commitul `6074d96`. **Nimic nu e publicat pe GitHub:** sunt 31 de commituri locale peste `origin/main` (`46acdc4`), iar push-ul cere aprobarea proprietarului.

## 1. Starea în 30 de secunde

- **Livrabilul curent:** `workspace/reviews/cladiri_2d_final_r3_epsg3844.gpkg`, strat `cladiri_2d`, EPSG:3844, 328 de clădiri:
  - 137 `ADMIS`: ale proprietarului;
  - 154 `ADMIS_PROPUS`: sfat al agentului, **nu** verdict;
  - 37 `INCERT`.
- **Proprietarul a șters 29 de INCERT în QGIS (2026-10-31).** Le-am salvat ca verdicte ELIMINAT în `workspace/reviews/verdicte_proprietar/verdicte_20261031.gpkg` (strat `eliminate_de_proprietar`) și `.json`.
- **Proiectul QGIS de revizie:** `workspace/reviews/loop_2d_20261030/inspectie_loop_2d_20261030.qgs`, grupul `CLADIRI_2D_FINAL (un singur strat)`. Proiectul comun `inspectie_corectii.qgs` **nu** a fost modificat.
- **Segmentatorul în producție:** ansamblul a 3 modele UNet ResNet-34 (acoperiș, margine, colț). Pe validare: IoU mediu 0,71, 81 % detectate, 26 % cu IoU ≥ 0,9.
- **Colab:** nicio sesiune activă. VM-urile se șterg la oprire.

## 2. Workflow-ul (cod în `compute/colab/scripts/`, teste în `compute/colab/tests/test_roof2d.py`)

| Pas | Script | Ce face | Unde rulează |
|---|---|---|---|
| 1 | `build_roof2d_aoi_dataset.py` (+ `roof2d_data.py`) | mozaic AOI la 0,15 m + etichete parțiale (1 = ADMIS, 0 = negative/inel/sol LiDAR/copaci, 255 = necunoscut), split nord/sud la Y = 585715 | local |
| 2 | `build_consensus_labels.py` | negative de copac (nDSM ≥ 2,5 m + culoarea frunzișului), opțiunea `--consensus` | local |
| 3 | `train_roof2d.py` | UNet cu 3 ieșiri; `--arch resnet34` (folosit), `convnext_*`, `meta_sat_vith` (testat, respins) | Colab A100 |
| 4 | `continuous_2d_roof_loop.py` | antrenare → scanare → V1..V6; `--seed`, `--contact-weight`, `--export-final` | Colab A100 |
| 5 | `scan_roof2d_aoi.py` | inferență pe tot AOI-ul, separare cladiri lipite, eliminare suprapuneri, regularizare; `--probs` refolosește un raster salvat, fără GPU | A100 sau local |
| 6 | `ensemble_probs.py` | media rasterelor de probabilitate | local |
| 7 | `vlm_chips.py`, `vlm_roof_assist.py`, `vlm_merge_finish.py` | Qwen3-VL-8B: verdict + tip acoperiș, LoRA, lipire pe streașină | cipuri local, VLM pe A100 |
| 8 | `finalize_roof2d_map.py` | stratul unic final (cauzele E1–E6), cu `--decisions` din revizia vizuală | local, ~25 s |
| 9 | `audit_roof2d_map.py` | măsurători pe fiecare clădire + planșe de revizie pentru toate clădirile | local |
| 10 | `meta_canopy_eval.py` | înălțimea copacilor din RGB (Meta) comparată cu LiDAR | Colab A100 |

**Comanda finală reproductibilă:**

```
.\venv\Scripts\python.exe compute/colab/scripts/finalize_roof2d_map.py --decisions workspace/colab_runs/audit_r3/decizii_vizuale_r3.json --out <gpkg>
```

Folosește implicit: stratul VLM `workspace/reviews/cladiri_2d_vlm_final_epsg3844.gpkg`, rasterul ansamblului `workspace/colab_runs/loop_q/ens_b1_b3r_l3.tif` și nDSM-ul `workspace/derived/cluj_ndsm_1m.tif`.

**Atenție:** o rulare nouă **nu** aplică ștergerile proprietarului. Înainte de rulare, adaugă id-urile din `verdicte_20261031.json` la `elimina` în fișierul de decizii.

## 3. Modele și artefacte (local, NU în git: `workspace/model_registry_roof2d_20261031.json` are SHA-256)

- **Ansamblul folosit:** `workspace/colab_runs/loop_b1/a100/iter_01/best.pt`, `loop_b3/run_b3r/iter_01/best.pt`, `loop_q/run_l3/iter_01/best.pt` (94 MB fiecare).
- **SAM 2.1 Large:** `models/sam2/sam2.1_hiera_large.pt`; adaugă doar +0,008, deci nu e folosit.
- **Meta ViT-H satelit (head):** `workspace/colab_runs/run_metasat/iter_01/best.pt`, respins.
- **Rasterele de înălțime Meta:** `workspace/colab_runs/run_canopy/chm_*.tif`.
- **Pierdut:** adaptorul LoRA Qwen3-VL. Nu a fost salvat; predicțiile da, în `workspace/colab_runs/vlm_v*/vlm*/vlm_predictions.json`.
- **Riscul principal:** modelele există într-o singură copie, pe acest laptop. Backup-ul (Drive sau LFS) așteaptă decizia proprietarului.

## 4. Rezultate măsurate (aceeași validare: 31 ADMIS din nord)

| Experiment | IoU poligon val | Notă |
|---|---|---|
| ResNet-34, rulări singure (B1/B3r/L3/B4s7) | 0,73 / 0,67 / 0,72 / 0,58 | variație mare între rulări |
| Ansamblul a 3 ResNet-34 + post-procesare | 0,71 (81 % detectate, 26 % ≥ 0,9) | **în producție** |
| ConvNeXt-Small (ImageNet) | 0,42 | respins |
| Meta SSL ViT-H satelit, înghețat | 0,525 (pixel 0,806) | respins: contur prea grosier |
| SAM 2.1 Large (rafinare) | +0,008 | respins |
| Qwen3-VL LoRA (verdict) | acord 0,61 cu proprietarul; 95 % copaci recunoscuți | folosit doar ca sfat |
| Meta canopy din RGB | precizie copac 0,72–0,79 (culoare: 0,38); recall ~0,33 | nu înlocuiește LiDAR |
| OSM / Microsoft footprints | IoU 0,28 / 0,30 pe ADMIS | doar verificare de completitudine |

Detalii: [LOOP_FINAL_2D_20261031.md](LOOP_FINAL_2D_20261031.md) și [WORKFLOW_BIGTECH_COMPARATIE_20261031.md](WORKFLOW_BIGTECH_COMPARATIE_20261031.md).

## 5. Reguli ale proprietarului, spuse în aceste sesiuni

- Validarea e făcută **în QGIS, prin toate formele**, nu doar prin cod. La fiecare buclă: randare prin MCP `qgis-stratumro`, planșe pentru toate clădirile, ANCPI prin MCP.
- **Un singur strat clar:** fără roșu peste verde, fără suprapuneri. Două stări pentru propuneri: ADMIS_PROPUS sau INCERT. Starea „pică o poartă” nu se mai folosește.
- **Conturul urmează colțurile reale ale clădirii,** inclusiv sub copaci. Nu urmează marginea coroanei.
- **Fiecare clădire are tipul de acoperiș în atribute,** pentru cadastru 3D.
- **Commiturile au mesaje care explică cauza, dovada și rezultatul.**
- **Colab A100 e pentru sarcinile grele.** „Big tech” înseamnă modele, blueprint-uri și unelte de la toate companiile mari, nu doar NVIDIA.
- **Nu atinge** modificările necomise ale altor agenți din `stratum_ro/*` și `workspace/baseline/*`.

## 6. Capcane tehnice (au costat timp)

- **`colab upload` din Git Bash** transformă `/content/...` în `C:/Program Files/Git/content/...`. Folosește PowerShell pentru `colab upload`.
- **Scripturile pentru `colab exec -f`** trebuie să fie UTF-8 fără BOM. `Set-Content -Encoding utf8` din PowerShell adaugă BOM.
- **`colab exec` rulează într-un kernel persistent:** modulele rămân în cache. Pentru teste curate, rulează un subproces `python`.
- **La pornire, cu `cd /content/repo`, scriptul VLM nu pornește;** folosește `start_vlm.py`, care face `cd /content/vlm`.
- **Pe Colab:** `pip install -q laspy` (cerut de importurile din `stratum_ro/core`). Pentru `peft`, dezinstalează `torchao` vechi.
- **Checkpoint-urile Meta și `weights_only` din torch:** se rezolvă cu `allow_meta_checkpoint_globals()` din `roof2d_data.py` (scalar numpy înregistrat sub numele `numpy.core...`). Normalizatorul RNet folosește `weights_only=False`, fișierul venind din bucket-ul oficial Meta.
- **DINOv3-SAT și SAM 3** cer acces aprobat pe Hugging Face (401 anonim). Token-ul local nu e citit de agent.
- **MCP `system_run_command`** a rămas blocat peste 30 de minute. Topologia se rulează local, cu `stratum_ro.ai.tools.cadastral_tools.validate_topology`.
- **QGIS ține GeoPackage-urile deschise**, deci nu le poți suprascrie (WinError 32). Scrie într-un fișier nou.

## 7. Ce urmează (cer decizia proprietarului)

1. **Reantrenarea ResNet-34 cu cele 29 de ELIMINAT** ca negative. Asta are cel mai mare câștig așteptat. Rulează aceeași validare, verificare în QGIS, apoi `finalize` cu ștergerile proprietarului.
2. **Revizia celor 37 de INCERT rămase** și validarea tipurilor de acoperiș (100 sunt marcate `DE_VERIFICAT`).
3. **Backup modele** (Drive sau LFS) și **push pe GitHub**.
4. **DINOv3-SAT și SAM 3,** după acordarea accesului pe Hugging Face.

## 8. Commituri (cele mai vechi jos)

```
6074d96 results(bigtech-test): Meta ViT-H backbone + Meta canopy height measured; independent check
2ef58fb / b847c74 / b8c238c  fixes for Meta checkpoints on Colab
39da7e2 feat(bigtech-test): meta_sat_vith + meta_canopy_eval
a7f7f64 docs: workflow vs big-tech comparison
df93814 evidence: OSM and Microsoft footprints vs owner ADMIS
357c85e data(owner): 29 INCERT deleted by owner saved as ELIMINAT; model registry
d4e19f3 / 34f9bf2 / 5547847  loops R3 / R2 / R1 (single clean layer, root causes E1-E6)
6657553 … 9bcbb18  VLM loops 1-3 (Qwen3-VL-8B)
a6278c8 … 0c1d250  QGIS-reviewed loops L1-L4
c313408 … 7a45daf  loops B1-B4 (contact channel, tree negatives, ensemble)
4a9ec9c … 9200c08  first real loop on A100 (dataset v3, trainer, scanner)
```

Note în vault: `stratumro-brain/inbox/H-002` … `H-007`.
