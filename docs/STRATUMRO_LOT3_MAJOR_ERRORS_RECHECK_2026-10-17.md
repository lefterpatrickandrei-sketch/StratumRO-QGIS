# Lot3: reverificare strictă a greșelilor majore

Cererea proprietarului: „Verifica că sunt unele cu greșeli majore”. Etapa este de verificare: nu modifică geometriile, selecția sau proiectul QGIS. S-au comparat toate cele zece scene fără contur (stânga) cu ipotezele etichetate (dreapta), în imagini separate, cu context mai larg. Sursele vectoriale active din QGIS au fost citite și corespund versiunilor din auditul anterior. Sesiunea avea starea dirty; aceasta nu a fost salvată sau resetată în cadrul reverificării.

Evaluarea anterioară a fost prea îngăduitoare, în special pentru T12. Eliminarea unei suprapuneri la T18 și trecerea testelor nu validează forma completă a clădirii. Nu se poate declara un caz bun doar pentru că s-a corectat una dintre muchii sau pentru că poligonul este valid.

| Caz / corp | Constatare vizuală | Concluzie tehnică |
|---|---|---|
| T11:C3 | Orientarea conturului nu urmărește acoperișul. Taie suprafața clădirii din nord-vest, cu omisiuni mari și includeri nepotrivite. | Eroare majoră de formă, nu finisare. C1/C2 se verifică separat. |
| T12:C1 | Dreptunghiul taie extensiile vizibile ale acoperișului roșu și nu urmărește forma exterioară completă. | Eroare de simplificare/omisiune; retrage aprecierea globală „plauzibil”. |
| T12:C2 | Conturul urmărește doar o parte a ansamblului gri și include o zonă brună/deschisă care poate fi terasă ori anexă. Muchiile trec prin acoperiș. | Eroare majoră de delimitare, cu identitate incertă; nu etichetă curată. |
| T12:C3 | Conturul combină o parte a acoperișului gri cu o porțiune a celui alb; restul suprafeței albe este omis. | Delimitare incompletă; clarifică corpurile, fără unire automată. |
| T13:C1 | Aproximarea urmărește parțial forma, dar treptele inferioare și muchiile dinspre vegetație nu sunt confirmate suficient. | Necesită verificare; nu declara rezultat corect pe baza planșei mici. |
| T14:C1 | Dreptunghiul taie proiecțiile de la capete și nu urmărește anvelopa laterală; include o fâșie alăturată pe una dintre laturi. | Eroare substanțială de formă, nu doar lipsa unei anexe. |
| T15:C1 | Acoperișul principal gri este reprezentat, însă conturul depășește marginile vizibile pe unele laturi. Ansamblul vecin nu este automat parte din același corp. | Corecție de margini și verificarea domeniului țintei; nu acceptat. |
| T16:C1 | Un dreptunghi acoperă două porțiuni cu învelitori diferite și ascunde diferențele de muchie de la îmbinare. Culoarea singură nu dovedește două clădiri. | Identitate și anvelopă de verificat; retrage calificarea globală de formă suficientă. |
| T17:C1/C2 | Separarea este păstrată. Colțurile/proiecțiile și golul curții trebuie verificate ca suprafețe reale, nu numai ca topologie. În gol se vede și o mică suprafață roșiatică aparent acoperită, a cărei natură rămâne incertă. | Nu deduce corectitudinea din „două corpuri + o gaură”; avertizările și verificarea anexelor rămân deschise. |
| T18:C1/C2 | Suprapunerea investigată este eliminată, dar colțurile superioare ale halei taie/depășesc muchii vizibile; aripa și celelalte laturi ale anexei brune nu sunt complet conforme. Proiecția rotunjită nu este reprezentată. | Corecție locală reușită, obiecte încă nefinalizate. Nu declara T18 bun în întregime. |
| T19 | Clădirea complexă este vizibilă; niciun contur recuperat. | Omisiune majoră. |
| T20:C1 | Conturul mic, cu orientare nepotrivită, taie interiorul acoperișului superior; nici măcar acel acoperiș nu este complet urmărit. | Eroare majoră de segmentare și formă; acoperișurile joase se tratează separat. |

Imaginile sunt în `workspace/reviews/lot3_major_errors_20261017/`, câte un fișier `Txx_unobscured_review.png` pentru fiecare caz. ID-urile corpurilor sunt etichetate explicit. `review_inventory.json` leagă imaginile de snapshot-ul vectorial și rasterele folosite. `T18_unobscured_review.png` folosește detaliul de 5 cm derivat din SID; celelalte folosesc cache-urile existente de 15 cm. Unele suprafețe sunt ascunse de vegetație; acolo concluzia este incertitudine, nu o limită inventată.

Prioritate pentru reparație: cazurile cu omisiuni/contururi arbitrare T19, T20, T11:C3 și T12; apoi forma T14 și marginile/identitățile rămase. Înaintea adoptării unei reparații se inspectează întreaga anvelopă a corpului, nu numai eroarea locală care a declanșat intervenția. Nu sunt măsurate procente de acuratețe fără referințe curate. Starea tuturor cazurilor rămâne neacceptată de proprietar; prezentul raport este verdictul tehnic al agentului, nu un verdict nou al proprietarului.

Codul de randare, imaginile și raportul acestei verificări sunt salvate împreună în Git. Nu s-au pornit inferențe sau teste noi, deoarece nu s-a schimbat algoritmul de extracție.
