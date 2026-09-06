# NORME TEHNICE ANCPI PENTRU SCANARE AERIANĂ LIDAR ȘI FOTOGRAMMETRIE (2026)
## Specificații de Achiziție, Clasificare și Extracție a Detaliilor Cadastrale și Topografice

**Emitent:** Agenția Națională de Cadastru și Publicitate Imobiliară (ANCPI) — Direcția de Geodezie și Cartografie  
**Standard:** Integrarea senzorilor aerieni LiDAR și camerelor RGB de înaltă rezoluție în fluxul de avizare cadastrală.

---

### 1. Clasificarea Norului de Puncte LiDAR (Standard ASPRS extins ANCPI):
* **Clasa 2:** Sol (Ground / Teren Natural) — utilizat pentru generarea DTM (Modelul Digital al Terenului).
* **Clasa 3:** Vegetație Joasă ($0.1\text{m} - 0.5\text{m}$).
* **Clasa 4:** Vegetație Medie ($0.5\text{m} - 2.0\text{m}$).
* **Clasa 5:** Vegetație Înaltă / Arbori ($> 2.0\text{m}$).
* **Clasa 6:** Clădiri și Construcții Permanente ($H \ge 2.5\text{m}$, suprafață minimă $8\text{ m}^2$).
* **Clasa 7 / 0:** Stâlpi de înaltă tensiune, turnuri de telecomunicații, structuri zvelte.

### 2. Algoritmul de Fuziune Hibridă (LiDAR + Ortofoto Optic):
* **Principiul dublei validări:**
  1. Masca de înălțime nDSM ($DSM - DTM$) confirmă existența unei mase volumetrice compacte la cota $H \ge 2.5\text{m}$.
  2. Ortofotoplanul optic de sub-decimetru (10–20 cm/pixel) delimitează exact linia de contur a streșinii și a pereților, eliminând rugozitățile discrete ale norului de puncte laser.

### 3. Regula de Separare Semantică & Eliminare Fals-Pozitiv:
* **Interzicerea interferenței vegetației pe clădiri:**
  * Orice impuls LiDAR din clasele 4 sau 5 care cade în perimetrul planimetric al unei clădiri din clasa 6 este tratat conform algoritmului de prioritate structurală: dacă înălțimea este consistentă cu acoperișul, reprezintă o suprastructură a clădirii (coș, lucarnă, antenă), iar dacă este vegetație suspendată, baza acesteia aparține arborelui adiacent pe sol.
  * Pe planurile cadastrale oficiale (DXF ANCPI) nu se admit noduri sau poligoane de vegetație pe corpul $C_1 / C_2$.
