# Misiune v2: bucla continuă 2D (RGB) pe Colab A100 cu validare simultană V1..V6

Versiune revizuită pe 2026-10-30 a promptului „Misiune Autonomă Claude Opus: Antrenare, Rafinare și Validare Simultană în 6 Forme”. Am păstrat obiectivele. Am corectat premisele care nu corespundeau repository-ului și am pus criterii verificabile. Regulile din [AGENTS.md](../AGENTS.md) au prioritate.

## Ce s-a schimbat față de v1 și de ce

| Premisă v1 | Ce era de fapt în repo (2026-10-30, `a7ecd4f`) | Corecție în v2 |
|---|---|---|
| „Scaffold-ul buclei A100” antrenează un model | `continuous_2d_roof_loop.py` nu antrena nimic; era o căutare euristică pe CPU | Bucla reală: `train_roof2d.py` → `scan_roof2d_aoi.py` → pseudo-etichete V1..V6 (commit `9200c08`) |
| V1..V6 se aplică pe poligon | Bucla trimitea `poly_s70` = bounding box-ul clădirii, deci V3/V4 vedeau mereu 4 noduri și treceau | V1..V6 primesc poligonul real, cu cipul georeferențiat exact (transformare afină a mozaicului) |
| Cipurile din `colab_2d_roof_dataset/` sunt etichete curate | Fiecare cip marca doar clădirea proprie; acoperișurile vecine neverificate deveneau fundal (0). Maparea pixel→Stereo 70 folosea bbox-ul clădirii, nu extinderea cipului | Dataset nou `colab_2d_roof_dataset_v3/` pe grila ortofoto (0,15 m), cu etichete parțiale (vezi mai jos) |
| Cele 9 `AJUSTARI_REPARATE_V1_V6` sunt pozitive | Au fost reparate de euristică, fără verdictul proprietarului | `ignore_index=255` până la verdictul proprietarului |
| „Promovare în `ADMIS_GOLD_2D`” | Doar proprietarul setează `ADMIS` (AGENTS.md) | Setul se numește `PSEUDO_GOLD_2D`, statut `PENDING_OWNER_REVIEW` |
| Colab cere WSL2 | `colab` 0.7.5 rulează nativ pe Windows | `colab new/upload/exec/download/stop` direct din PowerShell; scripturile trimise trebuie să fie UTF-8 fără BOM |
| „Bucla nu se oprește până la convergență totală” | Pe GPU plătit, o buclă fără limită poate consuma toate unitățile de calcul | Oprire la convergență, la platou sau la `--max-iterations`; `colab stop` obligatoriu |
| SAM 2.1 + LoRA în fiecare iterație | Cu 31 de ținte și 93 de clădiri de antrenare, LoRA pe SAM este speculativ | Amânat. Se reia numai dacă V2 (versant lipsă) rămâne principalul eșec după bucla segmentatorului |

## Politica de etichete (dataset v3)

- `1` = poligoanele `ADMIS` ale proprietarului.
- `0` = negativele dure ale proprietarului (fără să suprascrie un pozitiv), un inel de 0,3–1,2 m în afara `ADMIS` și solul LiDAR (nDSM < 1 m, erodat 2 m, la peste 1 m de orice candidat). nDSM se folosește **numai pentru etichete**. Intrarea modelului rămâne RGB, deci modelul poate rula pe orice UAT cu ortofoto.
- `255` = tot restul: ținte `AJUSTARE`, reparații euristice, alți candidați din catalog, zonă neverificată, NoData, banda-tampon a împărțirii.
- Împărțire spațială nord/sud la Y = 585715 (Stereo 70), cu bandă de 30 m: 93 `ADMIS` pentru antrenare și 31 pentru validare.

## Pașii misiunii

1. **Preluare.** `git status -s`, `git worktree list`. Citește AGENTS.md, `.agents/rules/hybrid-routing.md`, `stratumro-brain/INDEX.md` și notele inbox D-006 și H-001. Nu atinge fișierele necomise ale altor agenți.
2. **Dataset.** `.\venv\Scripts\python.exe compute/colab/scripts/build_roof2d_aoi_dataset.py --val-min-y 585715`. Inspectează vizual suprapunerea etichetelor pe ortofoto înainte de antrenare.
3. **Test local (RTX 4050).** Rulează `test_roof2d.py` și un smoke de 1–2 epoci pentru bucla completă.
4. **Commit local** cu fișierele proprii. Pachetul Colab = `git archive <sha> stratum_ro compute/colab` + dataset v3 + GPKG-ul deduplicat + `GIT_SHA`.
5. **A100.** `colab new --gpu A100 -s s2d` → `upload` → `exec` (unzip, `pip install rasterio`, buclă în fundal cu `--batch-size 16 --workers 8 --samples-per-epoch 1280`) → urmărire log → `download` → `colab stop -s s2d`.
6. **Fiecare iterație k:** antrenare (iterația 1 pornește de la ImageNet, următoarele de la checkpoint-ul anterior plus pseudo-etichete); scanare AOI; V1..V6 pe fiecare poligon; planșă before/after pentru cele 31 de ținte. **Inspectează planșa JPG vizual.**
7. **Oprire** dacă: IoU mediu `ADMIS` pe val ≥ 0,90 și ≥ 98% vârfuri la 45°/90° și 0 contacte NoData și 0 suprapuneri; sau la platou (câștig IoU val < 0,01 și setul de pseudo-etichete variază cu < 5%); sau la `--max-iterations`.
8. **Livrabile.** `workspace/reviews/final_2d_roofs_a100_epsg3844.gpkg` (toate propunerile, statut `PENDING_OWNER_REVIEW`), `loop_convergence_report.json`, planșa finală. Încarcă rezultatul în QGIS prin MCP `qgis-stratumro`. Nu salva proiectul comun fără acordul proprietarului.
9. **Verificări:** `scripts/validate_project.py --mode fast`, `unittest discover compute/colab/tests`, `test_simultaneous_2d_validator.py`.
10. **Predare.** Notă H-xxx în `stratumro-brain/inbox/`, `lint_vault.py`, `code_map.py`, commit local. Fără push.

## Ce nu se poate afirma

- IoU-ul pe clădirile `ADMIS` din zona de antrenare este optimist. Raportează IoU-ul pe zona de validare.
- Trecerea V1..V6 nu înseamnă acceptare. V1..V6 sunt euristici; verdictul vizual al proprietarului rămâne final.
- O zonă de ~0,42 km² din Cluj nu dovedește generalizarea pe alt UAT. Testul real este o rulare pe un ortofoto din altă zonă.
