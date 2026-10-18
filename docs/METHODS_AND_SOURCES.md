# Metode, convenții și surse

Acest document explică formulele din [README](../README.md), raportate la implementarea citită la checkpointul `e6011fa` și la rapoartele versionate. Nu introduce algoritmi noi și nu constituie o evaluare independentă a preciziei cadastrale.

## Coordonate, pixeli și validitate

Transformarea afină folosește convenția `Affine(a,b,c,d,e,f)`:

$$
\begin{bmatrix}x\\y\end{bmatrix}=\begin{bmatrix}a&b\\d&e\end{bmatrix}\begin{bmatrix}u\\v\end{bmatrix}+\begin{bmatrix}c\\f\end{bmatrix}
$$

`u` este coloana, `v` rândul, măsurate de la colțul exterior superior stâng. Pentru centrul pixelului adaugă 0,5 ambelor. Ordinea celor șase valori dintr-un tuple GDAL este `(c,a,b,f,d,e)`, diferită de constructorul `Affine`; nu le interschimba. Pentru raster nord-orientat, rotațiile `b,d` sunt zero, `a>0`, `e<0`. [Convenția GDAL](https://gdal.org/en/stable/tutorials/geotransforms_tut.html).

Într-un CRS proiectat în metri, determinantul $|ae-bd|$ este aria pixelului în m². Suprafața validă însumează numai pixelii incluși de masca sursei. Un pixel întunecat nu este automat NoData; măștile GDAL valide și măștile booleene NumPy pot avea convenții inverse. [Rasterio masks](https://rasterio.readthedocs.io/en/stable/topics/masks.html).

Citirea generică [CoreRasterReader](../stratum_ro/core/raster/reader.py) returnează o bandă și transformarea ferestrei. Citirea regională RGB, mozaicul și masca au o implementare separată, `OrthoMosaic`, în [regional_roofs.py](../stratum_ro/regional_roofs.py). Nu sunt încă un contract unic pentru toate traseele SID/VRT/GeoTIFF. Atribuirea unui CRS nu reproiectează coordonatele. La transformări, ordinea axelor trebuie explicitată; [pyproj `always_xy`](https://pyproj4.github.io/pyproj/stable/api/transformer.html) menține convenția x/y când este cerută.

## Înălțime relativă și LiDAR

Diferența DSM minus DTM estimează înălțimea suprafeței deasupra terenului. Înainte de calcul trebuie verificate CRS, unități, datum vertical, rezoluție, alinierea grilelor și datele de achiziție. Egalitatea dimensiunilor matricilor nu dovedește coincidența geografică.

`CoreRasterReader.compute_difference` respinge dimensiuni diferite și exclude NaN și valoarea NoData configurată. Apelantul trebuie să armonizeze metadatele, măștile și valorile NoData, inclusiv când sursele folosesc valori diferite. Funcția nu produce singură un DTM din norul de puncte și nu certifică coînregistrarea ortofoto–LiDAR. Fluxul regional folosește grile de context preexistente. Înălțimea și clasa punctelor sunt dovezi auxiliare; arborii pot fi înalți, iar clădirile pot avea suport incomplet în clasa 6.

## Geometrie și metrici

Pentru un inel cu noduri ordonate și ultimul conectat la primul:

$$
A_{\mathrm{inel}}=\frac12\left|\sum_{i=1}^{n}(x_i y_{i+1}-x_{i+1}y_i)\right|
$$

Suprafața poligonului scade golurile interioare; componentele distincte își păstrează identitatea. Codul utilizează operațiile [Shapely](https://shapely.readthedocs.io/en/stable/measurement.html), nu o nouă implementare manuală a formulei. Calculul este plan, în unitățile CRS-ului; coordonate în grade nu oferă automat m².

| Măsură | Ce exprimă | Implementarea actuală |
|---|---|---|
| IoU | Aria intersecției / aria reuniunii; 0–1 | `compute_iou`: întoarce 0 pentru intrări goale sau operații eșuate; verifică separat validitatea datelor. |
| Boundary RMSE | Eroarea medie pătratică a distanțelor la contur, în unitățile CRS | `compute_boundary_rmse`: două direcții, medie ponderată prin numărul total de eșantioane. |
| Hausdorff | Discrepanța maximă aproximată între geometrii | `compute_hausdorff`: funcția discretă GEOS/Shapely, densificare implicită 0,10, fallback fără densificare. |
| Deplasarea centrului | Distanța dintre centroizi | `compute_centroid_shift`; nu verifică forma sau colțurile. |

Sursa comună a acestor funcții: [core/geometry/metrics.py](../stratum_ro/core/geometry/metrics.py). Existența metricilor în core nu înseamnă că toți apelanții istorici au fost migrați către acest modul.

Boundary RMSE eșantionează **inelele exterioare**, inclusiv părțile unui MultiPolygon. Numărul punctelor fiecărui inel este `max(4, ceil(perimetru / pas))`, implicit pas 0,20 m; punctele sunt distribuite uniform fără repetarea capătului. Fiecare distanță este cea minimă la `.boundary` al celeilalte geometrii, care poate include goluri. Nu este o corespondență între vârfuri și nu măsoară explicit fiecare gol prin eșantionare proprie. Intrările lipsă produc infinit. Folosește un CRS metric și aceeași țintă geometrică pentru ambele obiecte.

Figura didactică IoU din README folosește două dreptunghiuri de 10 × 6 m, deplasate orizontal cu 1 m. Intersecția este 9 × 6 = 54 m², reuniunea 60 + 60 − 54 = 66 m², IoU = 54/66. Acesta este un exemplu calculat, fără a reprezenta un benchmark pe clădirile reale.

## Segmentare, simplificare și ținta geometrică

[SAM2](https://github.com/facebookresearch/sam2) realizează segmentare promptabilă; masca nu este în sine o clasificare semantică sau o limită cadastrală. [Lucrarea originală](https://arxiv.org/abs/2408.00714) descrie modelul de fundație. [Vectorizatorul](../stratum_ro/vectorizer.py) și regulile de domeniu transformă măștile în ipoteze geometrice. Formele trebuie simplificate fără a șterge aripi reale, a umple curți sau a uni corpuri independente. Numărul mic de noduri nu este singur un criteriu de corectitudine.

Acoperișul vizibil și amprenta pereților la sol au poziții diferite în prezența streșinii, înălțimii, perspectivei sau ocluziei. Un offset presupus nu este măsurare de teren. Referințele GMW mixte și predicțiile respinse/neacceptate nu devin etichete curate prin schimbarea numelui stratului. [Protocol de decizie](STRATUMRO_AGENT_DECISION_PROTOCOL.md), [porți de evaluare](STRATUMRO_EVALUATION_GATES.md).

## Proveniența figurilor și a numerelor

- **T10:** [imagine originală](../workspace/reviews/t10_antigravity_20261013/t10_before_after.png), [raport și verdict ulterior](../workspace/reviews/t10_antigravity_20261013/t10_report.json). Captura are starea istorică anterioară acceptării; nu a fost modificată.
- **Regional:** [raport scanare](../workspace/reviews/regional_roofs_20261017/scan_v1/report.json), [rutare și mască revizuite](../workspace/reviews/regional_roofs_20261017/masked_review_v2/mask_guard_report.json), [selecție curentă](../workspace/reviews/regional_roofs_20261017/CURRENT_REVIEW.json). Nu combina distribuția inițială 563/461/1057 cu cea revizuită 380/644/1057. Graficul folosește explicit varianta revizuită.
- **Arie:** 419681,0475 m² reprezintă aria validă a nucleelor raportată; nu o suprafață totală a municipiului sau o sumă de suprafețe cadastrale.
- **Timp:** 443,394 s reprezintă intervalul `execution_elapsed_s` al scanării. Nu include tot traseul de inițializare, revizie și livrare. Nu justifică procente de timp economisit față de operatori.
- **Cod și reproducere:** [generator figuri](../workspace/readme_publication_20261018/build_figures.py), [hash-uri și date selectate](../workspace/readme_publication_20261018/figure_manifest.json). Generatorul citește rapoartele și produce SVG/PNG; nu rulează SAM2 și nu editează capturile originale.
- **CI:** [workflow](../.github/workflows/ci.yml), [dovezi CI versionate](../workspace/ci_repair_20261018/README.md). Rezultatele testelor software se raportează separat de precizia produsului.

## Bibliografie și documentare

Sursele oficiale GDAL, Rasterio, Shapely, pyproj și SAM2 sunt legate lângă metoda pe care o explică. [QGIS Processing](https://docs.qgis.org/3.40/en/docs/pyqgis_developer_cookbook/processing.html) documentează folosirea providerelor existente. README utilizează [formulele GitHub](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions) și [diagrame Mermaid](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams); figurile statice oferă și o variantă direct vizibilă.
