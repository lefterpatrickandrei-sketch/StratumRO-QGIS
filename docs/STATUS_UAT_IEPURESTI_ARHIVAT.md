# Statut Oficial Proiect: UAT Iepurești (FINALIZAT & ARHIVAT)

> [!IMPORTANT]
> **PROIECT FINALIZAT ȘI ARHIVAT**  
> Cazul de studiu **UAT Iepurești (județul Giurgiu)** este **oficial încheiat** și **eliminat din fluxul de lucru activ** al depozitului StratumRO.
> Nu se mai efectuează dezvoltări active pe acest caz.

---

## 1. Care a fost scopul proiectului UAT Iepurești?
Scopul exclusiv al proiectului UAT Iepurești a fost un **studiu de extragere și recoltare de date deschise (*Open Data Harvesting Benchmark*)**:
- Testarea agregării datelor deschise din multiple surse oficiale naționale și europene:
  - **ANCPI**: limite UAT;
  - **APIA**: blocuri fizice agricole;
  - **ANAR**: bazine hidrografice și cursul râului Neajlov;
  - **INP / cIMeC**: situri arheologice clasate (Repertoriul Arheologic Național);
  - **CNAIR / CFR**: infrastructură de transport;
  - **EEA**: situri comunitare protejate Natura 2000.
- Rezultatele au fost consolidate în `projects/UAT_Iepuresti/UAT_Iepuresti_PUG_Master.gpkg` și au demonstrat cu succes capacitatea de catalogare automată a datelor deschise în QGIS.

Acest scop **a fost atins în totalitate**.

---

## 2. Delimitare Geografică Strictă (Cluj vs. Giurgiu)
- **UAT Iepurești** este o comună rurală situată în **județul Giurgiu (Muntenia)**.
- **Cluj-Napoca** este un municipiu universitar situat în **județul Cluj (Transilvania)**, la peste 450 km distanță.
- **Regulă strictă**: Datele din UAT Iepurești nu se combină, nu se amestecă și nu au nicio legătură spațială cu cele din Cluj-Napoca. Fiecare UAT are propria identitate cadastrală și teritorială.

---

## 3. Direcția Activă a Depozitului StratumRO

Focusul tehnic activ este concentrat **exclusiv pe CADASTRU URBAN în Cluj-Napoca**:
1. **Reconstituire acoperișuri și corpuri 1CC în Stereo 70 (EPSG:3844)** pe eșantionul din campusul USAMV / Mănăștur.
2. **Fuziune senzorială**: Ortofotoplan 15 cm/px + Nor de puncte aerian LiDAR nDSM (înălțimi acoperiș > 2.5m).
3. **Clasificare și Triage**: Motorul System 1 Fast Triage (<35ms pe CPU) pentru filtrarea zgomotului și escaladarea cazurilor ambigue de calcan către VLM.
4. **Livrabile de Producție CAD**: Exporturi TopoLT conforme Ordinului ANCPI 600/2023 (fișiere `.dxf` cu polilinii 2D închise și tabele de coordonate de contur `.cp`).

---

*Data arhivării oficiale: 21 Octombrie 2026*  
*Autoritate: Instrucțiune Proprietar StratumRO*
