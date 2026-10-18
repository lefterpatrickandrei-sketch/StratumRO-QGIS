# Raport Verificare Calitate (G5 QA/QC) — UAT Iepurești

- **Data verificării:** 2026-10-08T18:47:13.226355+00:00
- **Stare generală:** **CONFORM_PARȚIAL**
- **Fișier analizat:** `output/UAT_Iepuresti.gpkg`
- **CRS Referință:** EPSG:3844 (Stereo 70)

## Sumar Straturi

| Strat | Număr Entități | CRS Detectat | Geometrii Invalide | Geometrii Nule | Rezultat |
|---|---:|---|---:|---:|---|
| limita_UAT | 1 | EPSG:3844 | 0 | 0 | PASS |
| limita_intravilan | 1 | EPSG:3844 | 0 | 0 | PASS |
| imobile_cadastrale | 0 | EPSG:3844 | 0 | 0 | DATA_GAP |
| constructii | 140 | EPSG:3844 | 0 | 0 | PASS |
| drumuri_poligon | 45 | EPSG:3844 | 0 | 0 | PASS |
| drumuri_ax | 45 | EPSG:3844 | 0 | 0 | PASS |
| cursuri_apa | 2 | EPSG:3844 | 0 | 0 | PASS |
| paduri | 81 | EPSG:3844 | 0 | 0 | PASS |
| poduri | 20 | EPSG:3844 | 0 | 0 | PASS |

## Note privind conformitatea
1. **imobile_cadastrale** are 0 entități, fiind înregistrat în mod legal și transparent ca `DATA_GAP` (server suveran WFS ANCPI nedisponibil / fără credențiale deschise conform INSPIRE voidReason 'Unpopulated').
2. Toate geometriile din straturile populate au fost validate topologic conform librăriei GEOS (0 auto-intersecții, 0 goluri nejustificate).
3. CRS-ul nativ EPSG:3844 (Stereo 70) este confirmat pentru toate tabelele vectoriale.
4. Profil de livrare: **VALIDAT_PENTRU_EXTRACȚIE** (conformitate parțială, asistată pre-cadastral).
