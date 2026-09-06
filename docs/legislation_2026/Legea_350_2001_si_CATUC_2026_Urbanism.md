# LEGEA NR. 350/2001 ȘI NOUL COD AL URBANISMULUI ȘI CONSTRUCȚIILOR (CATUC 2026)
## Criterii Tehnice și Administrative pentru Elaborarea Planurilor Urbanistice Generale (PUG)

**Emitent:** Parlamentul României / Ministerul Dezvoltării, Lucrărilor Publice și Administrației (MDLPA)  
**Cadru de Referință:** Legea nr. 350/2001 privind amenajarea teritoriului și urbanismul, actualizată cu normele de digitalizare GIS și modelare tridimensională (LOD1 / LOD2) valabile în 2026.

---

### Criterii Tehnice & Indicatori Urbanistici Obligatorii:

#### 1. Procentul de Ocupare a Terenului (POT)
* **Definiție Legală:** Raportul dintre suprafața construită la sol ($S_c$) a tuturor corpurilor de clădire (principale + anexe) și suprafața totală a parcelei / unității teritoriale de referință (UTR), exprimat în procente:
  $$\text{POT} = \frac{\sum S_c}{S_{\text{teren}}} \times 100 \quad [\%]$$
* **Regulă de calcul:** În $S_c$ se includ toate clădirile cu fundație permanentă. Nu se includ terasele neacoperite și aleile pietonale permeabile.

#### 2. Coeficientul de Utilizare a Terenului (CUT)
* **Definiție Legală:** Raportul dintre suprafața desfășurată cumulată ($S_d$) a tuturor nivelurilor supraterane ale clădirilor și suprafața parcelei:
  $$\text{CUT} = \frac{\sum S_d}{S_{\text{teren}}}$$
  Unde pentru fiecare clădire: $S_d \approx S_c \times \text{Număr\_Niveluri}$.

#### 3. Regimul de Înălțime și Volumetria Urbanistică (LOD1)
* **Înălțimea la Cornișă ($H_{\text{cornișă}}$):** Cota altimetrică superioară a fațadei principale la baza acoperișului. Determină aliniamentul stradal și regimul de construire ($P$, $P+1E$, $P+2E$, etc.).
* **Înălțimea Maximă la Coamă ($H_{\text{coamă}}$):** Cota celui mai înalt punct structural al clădirii.
* **Incompatibilitate:** $H_{\text{coamă}} \ge H_{\text{cornișă}} \ge 2.50\text{ m}$. Dacă un senzor optic sau LiDAR raportează un element vegetal singular peste cota de coamă, acesta nu modifică regimul de înălțime al construcției.

#### 4. Zonificarea Teritorială pe Unități Teritoriale de Referință (UTR)
* Documentațiile PUG impun împărțirea teritoriului administrativ în celule / UTR-uri omogene cu reglementări unice privind funcțiunea dominantă, POT maxim admisibil, CUT maxim admisibil și cota minimă de spații verzi obligatorii.
