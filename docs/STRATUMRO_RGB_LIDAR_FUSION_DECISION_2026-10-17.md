# Decizie de integrare RGB–LiDAR–SAM2 — 2026-10-17

Stare: cercetare și direcție de implementare, nu implementare nouă sau benchmark. Citiți împreună cu `STRATUMRO_LIDAR_INSPECTION_2026-10-17.md` și `STRATUMRO_ORTHO_RESOLUTION_NODATA_2026-10-17.md`.

## Metoda recomandată

Fuziune prin propuneri, prompturi și verificare locală. Din LiDAR se derivă nDSM (înălțime față de teren), densitate/acoperire și suport de clasificare; opțional plane locale. Din RGB se propun independent clădiri. Se reconciliază propunerile după identitate și suport local, fără unirea automată a corpurilor vecine.

Pentru fiecare propunere, dovezile LiDAR compatibile generează puncte pozitive interioare și o fereastră de context pentru SAM2. Punctele negative provin din dovezi sigure despre suprafețe străine. Lipsa Clasei 6, lipsa returns sau o celulă necunoscută nu generează automat puncte negative. Limita unui seed LiDAR nu devine limita rigidă a clădirii.

SAM2 segmentează imaginea RGB pe baza prompturilor. LiDAR ajută ulterior la verificarea locală a contaminării și separării, ponderat după calitate. Geometria se simplifică după observarea corpului complet. Necunoscut rămâne necunoscut; pentru antrenare folosiți ignore_index, nu fundal.

Sticlă, suprafețe reflectante, unghiul de scanare, ocluziile și diferențele temporale sunt explicații posibile pentru dovezi LiDAR slabe. Materialul și cauza exactă nu se deduc automat din absența Clasei 6. T20 are puncte aproape de DTM pe zone cu acoperiș vizibil: nu s-a demonstrat că problema sa este sticla.

## Ce există deja în cod, verificat prin citire

- `stratum_ro/building_proposals.py`: propuneri separate CLASS_6 și NDSM_CONTEXT, cu eliminarea duplicatelor exacte.
- `stratum_ro/roof_body_proposals.py`: propuneri de corpuri cu RGB și suport LiDAR.
- `stratum_ro/roof_retry.py`: seed-uri locale din înălțime, culoare și clasificare; fallback fără Clasa 6. Fallback-ul continuă să ceară înălțime, deci nu reprezintă detecție RGB independentă pentru toate cazurile.
- `stratum_ro/sam2_engine.py`: encodează RGB prin `set_image`, apoi transmite point_coords, point_labels și box la predictor.

Aceasta este deja o formă de fuziune în pipeline. Nu înseamnă că un model comun RGB–LiDAR este antrenat sau că toate cazurile sunt rezolvate.

## Ce trebuie completat și evaluat

1. Validitate CRS, aliniere, acoperire și compatibilitate temporală, cu stări explicite pe zonă/caz. Păstrați sursele originale.
2. Propuneri RGB independente pentru recuperarea clădirilor fără seed LiDAR. Un model ușor antrenat pe etichete curate este o opțiune; necesită evaluare.
3. Unirea listelor de candidați RGB și LiDAR cu identități și proveniență. Nu intersecție obligatorie și nu union geometric al clădirilor învecinate.
4. Calitatea LiDAR controlează ponderea și ruta de verificare; absența suportului nu produce veto automat. Verificați și filtrele ulterioare, precum building_fraction.
5. Reutilizați embedding-ul SAM2 pentru mai multe obiecte din aceeași imagine. Nu apelați set_image repetat inutil. Contextul și rezoluția modelului trebuie evaluate; o fereastră mai mică nu garantează singură accelerare.
6. Comparați pe aceeași selecție fixată: RGB-only, flux actual și fuziune propusă. Măsurați recall, false positives, calitatea conturului, separarea corpurilor, timpul total inclusiv preprocesarea și VRAM. Nu promiteți accelerare înainte de benchmark.

O etapă ulterioară posibilă este un model antrenat pentru RGB plus înălțime, cu mască de validitate și exemple cu modalitate lipsă. SAM2 standard nu primește direct un canal nDSM suplimentar ca RGB+D; aceasta cere adaptare/antrenare sau un detector separat. Nu prezentați o suprapunere colorată ca echivalent al fuziunii învățate.

## Surse primare

- [Meta SAM2ImagePredictor](https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py): intrare imagine și prompturi puncte/box/mask, reutilizarea embedding-ului imaginii.
- [Meta SAM2](https://github.com/facebookresearch/sam2): model de segmentare ghidată prin prompturi.
- [Bittner et al., Bootstrapped CNNs for Building Segmentation on RGB-D Aerial Imagery, ISPRS 2018](https://isprs-annals.copernicus.org/articles/IV-4/187/2018/isprs-annals-IV-4-187-2018.html): exemplu de cercetare în segmentarea clădirilor din imagine și informație de înălțime; rezultatele nu se extrapolează automat la datele StratumRO.

Acest document completează auditul. Nu modifică pipeline-ul, nu rulează antrenare și nu schimbă verdictul proprietarului asupra cazurilor.
