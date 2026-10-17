# Lot3: checkpoint intermediar de reparație

Lucru autorizat după `ad057cc`: repararea erorilor majore și salvarea tuturor artefactelor utile. Acest checkpoint este intermediar; variantele nu sunt acceptate de proprietar și nu au înlocuit încă geometriile din QGIS.

Implementare nouă în produs:

- `roof_mask_fidelity.py`: mod optic explicit care păstrează extensiile și orientarea observată, curăță găuri mici de mască (<4 m²) cu diagnostic și încearcă simplificări în limite de suport/acoperire/deplasare. Găurile mari se păstrează. Mod planar separat, numai pentru ținte deja revizuite ca planuri rectangulare; nu forțează un dreptunghi când verificarea eșuează.
- `CadastralRoofWorkflow.extract`: politici explicite SENSOR_FUSION / OPTICAL_FIDELITY / OPTICAL_PLANAR_CORE, prompturi pozitive și negative verificate în imagine, context invalid permis numai explicit și cu minimum 90% date valide. Masca de validitate este aplicată înainte de vectorizare. Acceptarea rămâne umană.
- `roof_masked_preflight.py`: extensie explicită a preflight-ului pentru un context cu NoData real, după verificările standard de identitate, imagine/hash, CRS și acoperire. Nu șterge erori de schemă sau lipsa reviziei; punctul trebuie să fie valid. Avertizarea de completitudine rămâne obligatorie. Validatorul de bază modificat anterior de alt agent nu este editat de acest lucru.
- Runner-ul produsului transmite aceste opțiuni din manifest. Noile opțiuni nu schimbă implicitul regional.

Date: SID-urile originale nu declară CRS în GDAL. Cele nouă decupaje la 5 cm au fost comparate cu cache-urile proiectului la aceleași coordonate: corelații RGB 0,916–0,988. Interpretarea EPSG:3844 este cea a proiectului existent, nu o validare geodezică independentă; transformările XY nu au fost schimbate. `coordinate_checks.json` păstrează verificarea.

13 ținte pregătite în `workspace/reviews/lot3_repairs_20261017/`. Lotul inițial de 12 trece preflight-ul; T12:C2 este separat deoarece contextul conține NoData. Masca explicită de validitate din cache a fost transferată pe decupajul nativ, fără modificarea RGB. T12:C2 trece ruta explicită cu 98,45% context valid, dar păstrează avertizarea privind acoperirea. Versiunea anterioară exactă a TIFF-ului T12 a fost recuperată în `covers/T12_before_mask.tif`; hash-ul corespunde exact celui înregistrat de prima inferență (`source_mask_versioning.json`). Manifestele istorice și crop-urile inferenței sunt păstrate.

Primele rezultate reale recuperează casa T11:C3 în orientarea potrivită, forma completă a acoperișului roșu T12:C1 și mai mult din T12:C3, precum și întregul complex T19 omis anterior. T20 are acum două măști de acoperiș, dar eliminarea conductelor/echipamentelor și forma simplă sunt încă în lucru. Un experiment cu prompturi negative a pierdut porțiuni de acoperiș și nu este adoptat. T18:C1 rămâne prea complex în prima reluare; nu se înlocuiește un contur doar pentru că s-a generat altul.

Directoare: `attempt1/` măști brute și rularea reală; `simplified1/`, `simplified2/` comparații de simplificare; `masked_T12/` reluare cu mască; `T20_prompt_revision/` experiment neadoptat; `T20_planar_final/` este numele unei încercări, NU o confirmare de rezultat final (raportul spune NEEDS_GEOMETRY_REVIEW). Toate versiunile, rapoartele, imaginile și sursele derivate sunt păstrate. Scripturile sunt în tools/, modulele reutilizabile și testele în stratum_ro/.

Verificările executate până aici: 20 teste relevante noi/existente trecute, plus inferențele reale și imaginile inspectate. Suita completă și integrarea QGIS se execută după stabilizarea ultimei versiuni. Nu declarați acest checkpoint livrare finală. Următorii pași sunt controlul anexelor T20/T18, alegerea pe imagini a variantelor care îmbunătățesc întregul obiect, verificarea suprapunerilor, integrarea în același QGIS și un nou checkpoint cu verdictul exact al limitelor rămase.
