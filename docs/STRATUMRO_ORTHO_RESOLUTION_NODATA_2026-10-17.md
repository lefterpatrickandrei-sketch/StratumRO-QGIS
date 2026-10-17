# Ortofoto Cluj: rezoluție și tratarea NoData

Audit prin citire, 2026-10-17. Document pentru continuarea în proiectul comun `C:\Users\lefpa\Downloads\QGIS-AI`. Nu modifică rasterele, algoritmul sau proiectul QGIS. Separă comportamentul verificat de propunerea de integrare.

## Rezoluții măsurate

Surse originale: `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\Orto Cluj-*.sid`. Cele opt bucăți existau deja în această formă. Nu au fost create de această operație de audit. Metadatele GDAL din QGIS și fișierele SDW confirmă:

- Fiecare SID: 30.000 × 30.000 pixeli, trei benzi.
- Pasul grilei: **0,011651 m/pixel = 1,1651 cm/pixel**, pe ambele axe.
- Dimensiune nominală a unei bucăți: **349,53 × 349,53 m**.
- Acesta este pasul rasterului; nu demonstrează independent rezoluția reală a fotografiei sau precizia pozițională.

Rasterele încărcate în QGIS la verificare provin din `workspace/reviews/prompt_recovery_20261013/full_aoi/cache_tile_Cluj-*_halo.tif`. Toate au EPSG:3844, pas **0,15 m/pixel = 15 cm/pixel**, trei benzi și `NoData=0`.

| Bucată | Original, pixeli | Cache cu halo, pixeli | Pas cache |
|---|---:|---:|---:|
| Cluj-0-0 | 30000 × 30000 | 2663 × 2663 | 15 cm |
| Cluj-0-1 | 30000 × 30000 | 2663 × 2663 | 15 cm |
| Cluj-0-2 | 30000 × 30000 | 2663 × 2664 | 15 cm |
| Cluj-1-0 | 30000 × 30000 | 2663 × 2663 | 15 cm |
| Cluj-1-1 | 30000 × 30000 | 2663 × 2663 | 15 cm |
| Cluj-1-2 | 30000 × 30000 | 2663 × 2664 | 15 cm |
| Cluj-2-0 | 30000 × 30000 | 2664 × 2663 | 15 cm |
| Cluj-2-1 | 30000 × 30000 | 2664 × 2663 | 15 cm |

`run_hybrid_full_aoi.py` cere un halo de 25 m și `crop_aoi(..., target_res=0.15)`. Fereastra rezultată are aproximativ 399,45–399,60 m pe latură; halo-ul permite context peste limita bucății. Diferențele de un pixel țin de aliniere/rotunjire. Cache-ul are un pas aproximativ 12,87 ori mai mare decât grila SID. O decupare din cache nu recuperează detaliul sursei native.

Mozaicul `workspace/output/ortofoto_cluj_usamv_rgb.vrt`: 6991 × 6991 pixeli, 15 cm/pixel. Dreptunghiul exterior are 1048,65 × 1048,65 m; aceasta nu este suprafața efectivă cu imagine validă. VRT-ul folosește cele opt `workspace/output/cache_tile_Cluj-*.tif`, nu cele opt cache-uri cu halo de mai sus.

## Ce s-a întâmplat cu partea neagră

În harta QGIS verificată, marginile negre **nu au fost eliminate fizic**. Furnizorul fiecăruia dintre cele opt straturi raportează `sourceHasNoDataValue=True`, `sourceNoDataValue=0`, `useSourceNoDataValue=True`. QGIS afișează aceste zone transparent. Lista suplimentară de transparență RGB este goală. Rasterul păstrează dreptunghiul, poziția și pixelii săi; conturul neregulat vizibil reprezintă acoperirea utilă.

Sunt trei operații diferite:

1. Marcarea NoData/mască: stabilește ce pixeli nu au date.
2. Afișarea transparentă: ascunde acei pixeli pe hartă.
3. Decuparea unei ferestre: citește un dreptunghi georeferențiat pentru un caz. Nu creează automat o mască corectă pentru orice margine neagră.

## Cod existent și limite verificate

- `stratum_ro/ortho_extractor.py`, `build_vrt_mosaic`: comanda GDAL include `-srcnodata 0 -vrtnodata 0`. Aceasta declară invaliditatea; nu inventează imagine în goluri.
- `crop_aoi`, ramura SID/VRT: `gdal_translate -projwin ... -tr ... -a_srs EPSG:3844`. Selectează o fereastră și o grilă de ieșire. `-a_srs` atribuie CRS; nu efectuează reproiecție.
- Ramura GeoTIFF din aceeași funcție scrie pixelii și transformarea, dar nu copiază explicit NoData/masca și nu aplică resampling la `target_res`. Contractul nu este uniform între ramuri.
- Fallback-ul `_generate_fallback_vrt` este doar un XML placeholder, cu dimensiune 1000 × 1000 și comentarii cu numele fișierelor; nu conține benzile și sursele necesare unui mozaic real. Nu trebuie tratat drept recuperare funcțională.
- VRT-ul existent `workspace/output/ortofoto_cluj_usamv_rgb.vrt` raportează `nodata=None` și măști `all_valid`; nu are declarațiile NoData din comanda de mai sus. Intenția constructorului și artefactul actual diferă.
- `tools/build_lot3_v3_selection.py:create_covering_crop`: citește o fereastră din VRT, cu margine, și refuză fereastra dacă există orice pixel RGB `(0,0,0)`. Nu repară golurile. Scrie `nodata=None`. Varianta `tools/build_lot3_clean_selection.py` scrie `nodata=0`.
- `stratum_ro/evaluation_preflight.py`: verifică măștile raster și suplimentar RGB `(0,0,0)` în fereastra cerută. Fereastra trebuie să aibă acoperire completă. Este o barieră de validare, nu un algoritm de eliminare a fundalului.
- Varianta istorică `tools/build_lot3_revised_selection.py` folosește `np.clip(rgb, 1, 255)`. Aceasta transformă 0 în 1 și poate ascunde NoData; nu recuperează date. Nu se reutilizează pentru această problemă.

Nu presupune că orice pixel negru din orice ortofoto este NoData: pot exista pixeli întunecați valizi. Verificarea RGB este un fallback conservator pentru sursele cunoscute, nu o regulă universală de clasificare.

## Contract propus pentru integrarea în StratumRO — încă neimplementat prin acest audit

1. Înregistrează separat rezoluția sursei și rezoluția de procesare, CRS, transformarea, sursele și metoda de resampling.
2. Citește masca/alpha/NoData din sursă. Construiește o mască booleană explicită de validitate; păstreaz-o prin mozaicare, reproiecție, resampling și decupare. Regula RGB-zero se activează doar pentru o sursă verificată și se documentează.
3. Opțional restrânge dreptunghiul rasterului la limitele pixelilor valizi, păstrând masca pentru golurile și marginile neregulate. Recalculează transformarea geografică; nu muta imaginea arbitrar.
4. La cusături citește și bucățile vecine cu halo, dintr-un mozaic valid. Dacă un acoperiș continuă dincolo de fereastră, extinde fereastra înainte de inferență. NoData nu se completează cu valori artificiale.
5. Scrie GeoTIFF cu mască internă/alpha sau o convenție NoData verificată. Verifică după redeschidere aceleași coordonate, pasul grilei și invaliditatea. Nu valida numai aspectul în QGIS.
6. În antrenare, pixelii necunoscuți/NoData folosesc `ignore_index` (de exemplu 255), nu clasa negativă 0. În inferență și vectorizare sunt excluși explicit. Ferestrele parțial valide se procesează numai dacă algoritmul respectă masca; altfel se refuză cu motiv clar.
7. Testele de integrare necesare: contur negru, gol interior, umbră validă, cusătură între două bucăți, păstrarea măștii la export și clădire care traversează marginea ferestrei. Nu porni antrenare pentru a valida aceste operații raster.

Până la implementarea și verificarea contractului, formularea corectă este: **fundalul NoData este transparent în QGIS, iar ferestrele de evaluare sunt controlate pentru acoperire; tratarea generală a NoData nu este încă uniformă în toate ramurile StratumRO.**

Referințe: [GDAL gdalbuildvrt](https://gdal.org/en/stable/programs/gdalbuildvrt.html), [Rasterio masks](https://rasterio.readthedocs.io/en/stable/topics/masks.html).
