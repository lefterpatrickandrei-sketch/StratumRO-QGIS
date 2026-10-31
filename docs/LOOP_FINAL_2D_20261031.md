# Bucla finală 2D (R1–R3) pe toată harta: cauze, corecții, verificări

Data: 2026-10-31. Pornire: stratul VLM `workspace/reviews/cladiri_2d_vlm_final_epsg3844.gpkg` (451 de clădiri), criticat de proprietar în QGIS: roșu peste verde, multe fals-pozitive magenta, contururi care urmăresc coroanele în loc de colțurile clădirii, suprapuneri, validare făcută doar în cod.

**Rezultat:** `workspace/reviews/cladiri_2d_final_r3_epsg3844.gpkg`, strat `cladiri_2d`, EPSG:3844, 357 de clădiri, un singur strat. În QGIS: copia `workspace/reviews/loop_2d_20261030/inspectie_loop_2d_20261030.qgs`, grupul `CLADIRI_2D_FINAL (un singur strat)`. Proiectul comun nu a fost modificat.

## Ce înseamnă culorile și atributele

| `stare` | Culoare QGIS | Sens |
|---|---|---|
| `ADMIS` | albastru | Poligonul tău din revizia Opera (137). Geometria e a ta. Am aplicat doar ajustarea pe streașină, de cel mult 0,45 m, marcată în `geom_ajustata_agent`. |
| `ADMIS_PROPUS` | galben | Propunere a agentului (154): VLM + verificare vizuală. **Nu e verdictul tău.** |
| `INCERT` | magenta punctat | De decis de tine (66). |

`owner_verdict` copiază doar ce ai decis tu. Pentru 3D:
- `tip_acoperis`: TERASA_PLAT, O_APA, DOUA_APE, PATRU_APE, COMPLEX;
- `tip_sursa`: LIDAR_PROFIL, VLM, FORMA_2D sau UNIRE_VIZUALA;
- `tip_incredere`: LIDAR_SI_VLM, O_SINGURA_SURSA, DE_VERIFICAT sau DE_VERIFICAT_VLM_x;
- înălțimi LiDAR: `h_streasina_m`, `h_coama_m`, `h_relief_m`;
- `ocluzie_m2`: suprafața adăugată sub coroane;
- `rectilinear_evidenta`: 1 dacă conturul a fost refăcut la 90° din dovezi.

## Cauzele găsite și ce s-a schimbat

Fiecare cauză a fost găsită cu `compute/colab/scripts/audit_roof2d_map.py` pe toate clădirile, verificată pe planșe și în QGIS prin MCP înainte de corectare. Fiecare corecție are un test în `compute/colab/tests/test_roof2d.py` (26 de teste).

| # | Cauză (dovadă) | Corecție |
|---|---|---|
| E1 | ADMIS-ul tău și propunerile erau livrate ca două straturi; 17 clădiri ADMIS erau acoperite de mai multe propuneri. | Un singur strat. Geometria ta are prioritate, dublurile au fost eliminate. |
| E2 | Tăierea suprapunerilor permitea 0,25 m² la fiecare re-pătratare (41 de perechi). | Partiție strictă. A rămas 1 pereche care nu e proprietar–proprietar (0,027 m²). Cele 12 perechi proprietar–proprietar, sub 1 m², există deja în revizia ta; sunt marcate în `suprapunere_proprietar_m2` și nu au fost tăiate. |
| E3 | `foliage()` vedea țigla teracotă ca frunze de toamnă (13,4% din pixelii acoperișurilor tale) și marginile acoperișurilor ca vegetație (mediana 0,59 din contur). | Regula ExG + textură, cu deschidere morfologică: 0,2% pe acoperișuri, 88,6% pe copaci. LiDAR doar confirmă; casele noi lipsesc din LiDAR-ul mai vechi. |
| E4 | Contururile se opreau la coroană sau o urmăreau în diagonală. | Contur refăcut la 90° din probabilitatea de acoperiș, în cadrul clădirii. Coroana se adaugă doar cu dovezi: înălțimea acoperișului **și** suprafață LiDAR netedă (std 3×3 < 0,8 m; acoperișurile tale mediana 0,46 m, coroanele 1,01 m) sau o mușcătură mică de colț la o clădire simplă. R2D_00177 nu mai cuprinde curtea cu copaci. |
| E5 | Fragmente și micro-laturi: MCP ANCPI a găsit 75 de laturi sub 0,5 m. | Unirea pieselor la aceeași înălțime; colapsarea treptelor fără să înclin pereții (35 rămase, toate trepte ortogonale). Capela unită din 6 piese. |
| E6 | Tipul de acoperiș: profilul LiDAR presupunea coama centrată, așa că acoperișurile în patru ape ieșeau „o apă” (R2D_00135: patru ape 0,18 → 0,94 cu căutarea coamei). | Coama căutată la ±1,5 m; „o apă” doar dacă bate clar celelalte modele; `tip_incredere` marchează dezacordurile cu VLM-ul. |
| V1 | Verificare vizuală a tuturor clădirilor de 3 ori (R1: 385, R2 pe schimbări, R3: 363). | 31 eliminate, 22 trecute la INCERT, 2 promovate, 1 unire; toate în `workspace/colab_runs/audit_r3/decizii_vizuale_r3.json`. Sunt sfaturi ale agentului, nu verdicte. |

## Verificări finale

- **MCP `stratumro-cadastral-tools` `cadastral_validate_ancpi`** pe tot stratul: `passed` true, 0 eșecuri la suprafață sau Stereo 70. 35 de avertismente pentru laturi sub 0,5 m.
- **Topologie** (`validate_topology` din proiect): 357/357 valide, 0 auto-intersecții, 0 vârfuri duble, 0 sliver-uri. Prin MCP `system_run_command` comanda a rămas blocată peste 30 de minute, așa că am rulat-o local.
- **Vârfuri la 45°/90°:** 91,2% (stratul VLM: 82%).

## Limite

- Nu ai validat încă tipurile de acoperiș. 100 de clădiri sunt `DE_VERIFICAT`, iar 50 de O_APA sunt cea mai slabă clasă.
- Pentru `ADMIS_PROPUS` nu am o măsură de precizie independentă. Dovada e verificarea mea vizuală plus VLM-ul calibrat pe revizia ta (90% recall, 0,82 precizie).
- În buclele R1–R3 nu am reantrenat nimic și nu am folosit Colab, cum ai cerut.
