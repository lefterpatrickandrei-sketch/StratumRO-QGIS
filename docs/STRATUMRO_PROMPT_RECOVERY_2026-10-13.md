# StratumRO — cercetare, corecții și verificare, 13 octombrie 2026

## Rezultatul și limitele

**Clarificare ulterioară confirmată de utilizator:** contururile discutate26–29 sunt amestecate: clădiri și alte suprafețe. Tipul fiecărui obiect rămâne de stabilit. Valorile pe toate29 de referințe de mai jos sunt comparații geometrice istorice pe un set mixt; nu reprezintă rata de detecție a clădirilor. Nu recalculăm artificial14/25 și nu excludem automat toate cele4 obiecte. Confirmarea este salvată în reference_semantics_confirmation.json.
Codul a fost corectat și testat. StratumRO rămâne un generator de propuneri pentru inspecție. Contururile utilizatorului din GMW sunt referințe de dezvoltare, nu un set independent de contururi oficiale. Nu s-au modificat geometriile de referință.

## Cercetare și cauze
- API-ul oficial SAM2 acceptă puncte pozitive (1), negative (0) și mai multe măști. Scorul măștii nu stabilește că obiectul este o clădire: https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py
- Clasificările ASPRS disting clădirile (6) de vegetație (3/4/5), dar clasificarea observată poate fi greșită: https://www.asprs.org/wp-content/uploads/2010/12/LAS_1_3_r11.pdf
- MEASURED: referința21 conține 898 puncte, zero clasa6, 493 clasa4/5. Excluderea categorică a vegetației nu poate fi folosită global pentru recuperarea acestui acoperiș.
- IMPLEMENTED: extragerea optică alegea cel mai mare fragment, chiar când alt fragment conținea punctul pozitiv. Selecția măștii putea favoriza obiecte fără legătură cu punctul indicat.
- MEASURED: în diagnosticul9–11, propuneri nDSM de 3593–3918m² acoperă clădiri mici și context. Propunerile separate din clasa6 recuperează unele obiecte.
- MEASURED: amestecarea noilor măști cu cele existente înainte de regularizare poate deteriora cazul5 (.7470→.4933). Această strategie a fost respinsă. Ipotezele rămân în straturi separate.

## IMPLEMENTED
1. sam2_engine.py: fragmentele sunt selectate după punctele pozitive; fiecare mască se evaluează pe componenta indicată. Puncte negative opționale, filtrare în afara imaginii, respingere măști fără componentă validă. Suprafața pixelului folosește determinantul transformării afine; caseta folosește toate cele patru colțuri.
2. sensor_review.py: evidență clasa6/vegetație și date disponibile, identitate geometrică stabilă și motive explicite pentru inspecție. Nicio geometrie nu este eliminată de aceste criterii și niciuna nu este aprobată automat.
3. building_proposals.py: propuneri clasa6 distincte de contextul nDSM. Contextul fără clasa6 se păstrează pentru acoperișuri precum21. Duplicate exacte eliminate.
4. run_hybrid_full_aoi.py: opțiunea experimentală --proposal-policy focused_class6; --output-dir pentru rulări separate; alternativele sunt regularizate separat, păstrate în CLADIRI_ALTERNATIVE și REVIZUIRE_SENZORI, fără a intra automat în livrabilul CAD. Exportul la sol nu mai inventează statusul APROBAT.
5. LidarProcessor returnează grilele observațiilor pe clase; politica implicită de completare rămâne legacy.

## TESTED
306 teste descoperite: 297 trecute, 9 omise, zero eșecuri; exit0; 43.178s. Log: workspace/reviews/prompt_recovery_20261013/unit_tests_final.log. Compilarea Python și verificarea git diff --check au trecut. Nu s-au schimbat manifestele de referință/golden.

## MEASURED — diagnostic pe toate cele29
Decupaje90m, maximum3 propuneri de context și separat maximum3 propuneri clasa6. Centrul decupajului și alegerea punctului clasa6 sunt ghidate de centrul referinței, ca în experimentul anterior. Conturul referinței nu este dat modelului. Aceasta NU este o evaluare independentă sau o rulare completă fără referințe. În referințele mari, decupajul90m poate fi insuficient.

7/29 cazuri au cel puțin un contur de context cu IoU≥.50. Cu alternativele separate,15/29 au cel puțin o opțiune peste prag. Sunt101 apariții de predicții de context și83 de alternative; aparițiile pot reprezenta aceleași clădiri în decupaje suprapuse. Nu sunt TP și nici un număr de clădiri unice. Un scor maxim peste prag nu aprobă conturul complet.

| Referință | IoU context | IoU alternativă clasa6 | Verdict numeric pentru opțiuni |
|---|---:|---:|---|
| REF_TIER1_001 | 0.0931 | 0.9237 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_002 | 0.8864 | 0.8843 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_003 | 0.8550 | 0.8220 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_004 | 0.3824 | 0.4326 | Necesită corecție / referință de clarificat |
| REF_TIER1_005 | 0.7470 | 0.7302 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_006 | 0.9363 | 0.9364 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_007 | 0.3601 | 0.3219 | Necesită corecție / referință de clarificat |
| REF_TIER1_008 | 0.5689 | 0.8070 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_009 | 0.0000 | 0.3489 | Necesită corecție / referință de clarificat |
| REF_TIER1_010 | 0.0000 | 0.7500 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_011 | 0.0000 | 0.8580 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_012 | 0.1434 | 0.8635 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_013 | 0.0508 | 0.2992 | Necesită corecție / referință de clarificat |
| REF_TIER1_014 | 0.3752 | 0.4633 | Necesită corecție / referință de clarificat |
| REF_TIER1_015 | 0.0000 | 0.1458 | Necesită corecție / referință de clarificat |
| REF_TIER1_016 | 0.0000 | 0.0534 | Necesită corecție / referință de clarificat |
| REF_TIER1_017 | 0.0000 | 0.5459 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_018 | 0.0000 | 0.8395 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_019 | 0.0000 | 0.8221 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_020 | 0.9082 | 0.9560 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_021 | 0.8939 | 0.0018 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_022 | 0.0000 | 0.0000 | Necesită corecție / referință de clarificat |
| REF_TIER1_023 | 0.0040 | 0.0000 | Necesită corecție / referință de clarificat |
| REF_TIER1_024 | 0.0000 | 0.0000 | Necesită corecție / referință de clarificat |
| REF_TIER1_025 | 0.3563 | 0.5021 | Există opțiune ≥.50; verificare necesară |
| REF_TIER1_026 | 0.0367 | 0.0061 | Necesită corecție / referință de clarificat |
| REF_TIER1_027 | 0.2438 | 0.2184 | Necesită corecție / referință de clarificat |
| REF_TIER1_028 | 0.0582 | 0.0628 | Necesită corecție / referință de clarificat |
| REF_TIER1_029 | 0.2141 | 0.0000 | Necesită corecție / referință de clarificat |

## Inspecție vizuală efectuată
Au fost inspectate cele5 planșe cu toate29 de cazuri. La6 alternativa este curată. La10,11,12 apar acoperișuri ratate de context. La14 există îmbunătățire, dar separarea corpurilor nu este rezolvată. La17 și25 contururile rămân parțiale chiar dacă scorul trece pragul. La21 păstrăm conturul de context și îl trimitem la verificare; alternativa clasa6 nu îl poate înlocui.

Referințele26,28,29 includ vizibil parcări/teren/vegetație, iar27 se extinde în afara acoperișului și în NoData. Nu trebuie presupuse contururi de clădire pentru măsurarea erorii. La22 nu este evident un acoperiș în poziția referinței; diferența de dată/sursă trebuie verificată. La24 obiectul pare un complex cu curte; semantica trebuie clarificată. Geometriile au rămas intacte. Detalii: visual_review.json și reference_lidar_diagnosis.json.

## Procedura de acceptare
- Se păstrează rezultatul de context și alternativele separat; selecția unei alternative este o decizie de inspecție, nu o unire automată.
- Se verifică obiectul urmărit, acoperirea întregului acoperiș, contururile suplimentare, separarea corpurilor și conflictele LiDAR/ortofoto.
- Orice lipsă de clasa6, vegetație dominantă, date insuficiente sau formă concavă este motiv de verificare, nu dovadă că obiectul trebuie șters.
- Înainte de afirmații despre toate clădirile, se clarifică tipul fiecărei referințe și se separă terenul/parcela de acoperiș; nu se rescriu contururile pentru a crește scorul.
- Evaluarea completă folosește asociere1:1 și raportează predicțiile neasociate separat; acestea nu sunt automat clădiri false.

## Rularea completă
TESTED: rulare completă reușită, exit0, toate8 tile-urile, fără centre/contururi de referință în inferență. 1282 prompturi evaluate (nu clădiri unice); fuziune132.99s. Rezultatul principal conține240 contururi, alternativele144, anexele19. Coada de verificare352 intrări (189 principale +144 alternative +19 anexe). Cele51 principale fără conflict evident rămân NEVERIFICAT, nu APROBAT.

QGIS3.40 standalone a citit toate23 de straturi: geometrii valide, EPSG3844. DXF:39710 entități, zero erori de audit structural. Aceste verificări nu confirmă corectitudinea obiectelor fizice.

MEASURED — comparație geometrică istorică pe referințe mixte, nu evaluare exclusivă a clădirilor: asociere1:1 la IoU≥.50 față de toate29 referințele:

| Set | Potriviri | Referințe | Predicții | Referințe neasociate | Predicții neasociate |
|---|---:|---:|---:|---:|---:|
| Principal |7|29|240|22|233|
| Alternative |13|29|144|16|131|
| Opțiuni combinate pentru inspecție |14|29|384|15|370|

Predicțiile neasociate pot fi clădiri reale neincluse în cele29 referințe. Nu se interpretează ca370 artefacte. Setul combinat este un inventar de ipoteze și poate conține variante ale aceleiași clădiri; nu este un livrabil cu384 clădiri distincte aprobate. Status: UNVERIFIED_CONDITIONAL_METRICS.

Inspecția full_aoi_comparison.png: la6 alternativa urmărește bine acoperișul (IoU.908), mai bine decât principalul (.743); la14 principalul rămâne greșit grupat (.341), iar alternativa automată nu recuperează ținta. La21 principalul este păstrat (.831), fără suport clasa6. Diferența față de diagnosticul cu centre de referință este explicită: nu se prezintă15/29 drept performanță a rulării autonome.

Dovezi: full_aoi_verification.json, full_aoi/qgis_readback.json, full_aoi.log. Fișierele sunt generate sub workspace/reviews/prompt_recovery_20261013/full_aoi, separat de livrabilul activ. Hashurile GeoPackage/DXF active și ale referinței au rămas identice cu cele de la începutul verificării. Niciun contur nu a fost aprobat automat.

## Probleme rămase
Separarea corpurilor7/14, clădiri mici9/13/15/16, acoperișuri fără suport clasa6 (22–24), semantică/data referințelor26–29, contururi false de vegetație încă păstrate în coada de verificare. Calitatea trebuie verificată pe date noi, nefolosite în dezvoltare, înaintea unei afirmații de generalizare.

## Control vizual DXF
Randarea DXF real a fost efectuată (full_aoi/dxf_preview.png). Fișierul este valid structural, însă tabelul de coordonate foarte lung comprimă harta în vederea de ansamblu. Verdict: planșa NU este acceptată vizual ca livrabil final; paginarea/dispunerea tabelului rămâne de corectat. Nu se confundă auditul DXF fără erori cu lizibilitatea unui desen.
