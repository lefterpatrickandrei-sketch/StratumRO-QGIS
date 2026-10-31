# Amprente externe pentru zona Cluj (comparație, 2026-10-31)

- `osm_3844.gpkg`: clădiri OpenStreetMap (Overpass, bbox AOI), © OpenStreetMap contributors, ODbL.
- `ms_3844.gpkg`: Microsoft Global ML Building Footprints, quadkey 120320201 (fișierul Romania), ODbL.

Comparație cu cele 137 de clădiri ADMIS ale proprietarului, în zona cu ortofoto valid:

| Sursă | Clădiri în zonă | ADMIS găsite (IoU ≥ 0,5) | IoU mediu | IoU ≥ 0,9 |
|---|---|---|---|---|
| OSM | 142 | 24 % | 0,28 | 0 % |
| Microsoft | 165 | 26 % | 0,30 | 0 % |
| Ansamblul nostru (val, `loop_q`) | – | 81 % | 0,71 | 26 % |

Microsoft nu are înălțimi aici. OSM are 101 clădiri cu `building:levels` și 26 cu `roof:shape` în tot bbox-ul.

Stratul final R3 nu conține 16 clădiri OSM și 37 Microsoft (IoU < 0,3). Acestea sunt candidați de verificat, nu adevăr. Rulat cu `venv` Python; codul de comparație e descris în istoricul conversației și în commit.
