# STRATUMRO — PHASE 2: FORMAL CONTRACTS & COMPATIBILITY BOUNDARIES

**Document Type:** Master Phase 2 Architecture Contracts & Decoupling Dossier  
**Project:** StratumRO Industrial-Grade Geomatics & GeoAI Platform  
**Repository Commit:** `c9768641acb0bef0806593c84f549acba5960703` (Branch: `main`)  
**Audit Standard:** 8 Evidence-First Scientific Rules (AGENTS.md §3)  
**Execution Mode:** Controlled Implementation (Strict Zero Mutation pe Codul de Producție Existent)  
**Phase Status:** `PASS`  
**Date:** 2026-09-20  
**Authoritative Orchestrator:** Antigravity  

---

## 1. EXECUTIVE SUMMARY & VERIFICATION STATUS

Phase 2 (**Formal Contracts & Compatibility Boundaries**) a fost finalizată cu succes cu statusul:

### **STATUS: `PASS`**

În conformitate cu principiul suveran:
> **„CE TREBUIE SĂ OFERE O COMPONENTĂ SE DEFINEȘTE ÎNAINTE SĂ DECIDEM UNDE VA LOCUI IMPLEMENTAREA EI.”**

Am construit stratul formal de contracte, interfețe abstracte (`Protocol`, `ABC`) și modele de date (`dataclasses`) în pachetul dedicat [`stratum_ro/contracts/`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/), **fără a muta sau altera niciun fișier de producție existent** (`vectorizer.py`, `cad_exporter.py`, `volumetric_3d.py`, etc. au rămas 100% neschimbate).

### Rezultatele Verificării Criminalistice:
1. **Integritate Cod Urmărit:** `0 linii de cod existente modificate` (`git diff` este complet gol).
2. **Phase 1 Golden Freeze Re-verificat:** Suita [`stratum_ro/test/test_phase1_golden_freeze.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_phase1_golden_freeze.py) a fost executată și a confirmat 100% imuabilitatea Ground Truth-ului și a modulelor de producție.
3. **Noua Suită de Testare a Contractelor:** [`stratum_ro/test/test_contracts.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_contracts.py) (8 teste rulate și trecute în 0.001s).
4. **Total Suită Teste:** `227 teste descoperite: 218 passed, 9 skipped (GUI PyQGIS context), 0 failed în 28.56s`.

---

## 2. INVENTARUL CONTRACTELOR EXISTENTE (SINTEZĂ)

Raportul complet a fost generat în [`workspace/phase2/existing_contracts_inventory.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/phase2/existing_contracts_inventory.md).  
S-au descoperit **46 de clase și contracte existente** în codebase, majoritatea concentrate în stratul AI (`TaskSpec`, `RiskAssessment`, `ProvenanceChain`, `BaseAIProvider`).

### Lacunele Identificate și Acoperite în Faza 2:
- **Absența unui contract comun pentru vectori/rastere:** Geometriile erau pasate ca obiecte Shapely brute fără metadate de CRS sau proveniență.
- **Lipsa abstracției pentru pachete de domeniu:** Nu exista o clasă de bază `BaseDomainPack` care să definească capabilitățile specifice (cadastru, topografie, 3D).
- **Cuplajul modelului de viziune:** SAM 2 nu avea o interfață separată de providerii de chat LLM.
- **Ambiguitatea axelor geodezice:** Lipsa unei enumerări clare a convențiilor de axe ($X/Y$ cartezian vs $X=\text{Nord}, Y=\text{Est}$ ANCPI).

---

## 3. PACHETUL DE CONTRACTE FORMALE (`stratum_ro/contracts/`)

Pachetul conține 10 module specializate, fără nicio dependență de QGIS sau de vreo interfață grafică:

```text
stratum_ro/contracts/
├── __init__.py           # Export unificat al tuturor contractelor
├── geo.py                # CommonGeoObject, Coordinate2D/3D, BoundingBox, IGeoProcessor
├── geodesy.py            # AxisOrder, CRSMetadata, ICRSManager, ITransformer
├── geometry.py           # IGeometryEngine (regularizare 90°, topologie, metrice)
├── domain.py             # DomainMaturity, DomainCapability, BaseDomainPack
├── cadastre.py           # TopoLTLayer, CadastralPoint, PADTableSpec, CPInterchangeSpec
├── vision.py             # VisionPrompt, VisionMaskResult, IVisionEngine (Decuplat de LLM)
├── workflow.py           # WorkflowStatus, ApprovalState, ApprovalRequest/Decision, IWorkflowRunner
├── validation.py         # ValidationSeverity, ValidationIssue, ValidationReport, IValidator
├── provenance.py         # ProvenanceRecordContract, IProvenanceRecorder (W3C PROV-O)
└── adapter.py            # IQgisAdapter, ILegacyAdapter (Boundaries decuplare)
```

---

## 4. DETALIUL CONTRACTELOR CHEIE

### 4.1 `CommonGeoObject` & `IGeoProcessor` ([`geo.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/geo.py))
Încapsulează orice entitate geospațială (clădire, parcelă, ax drum) într-o structură agnostică de client:
```python
@dataclass
class CommonGeoObject:
    id: str
    geometry: Any          # Shapely geometry sau GeoJSON dict
    crs: str               # e.g., "EPSG:3844"
    attributes: Dict[str, Any]
    metadata: Dict[str, Any]
    provenance_id: Optional[str] = None
```

### 4.2 `AxisOrder` & `ITransformer` ([`geodesy.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/geodesy.py))
Garantează non-autoritatea LLM-urilor asupra calculului numeric:
- `AxisOrder.EASTING_NORTHING` (convenția carteziană PROJ/GIS) vs `AxisOrder.NORTHING_EASTING` (convenția ANCPI $X=\text{Nord}$, $Y=\text{Est}$).
- `ITransformer` impune ca transformările să fie executate **exclusiv de motoare geodezice deterministe locale**.

### 4.3 `IGeometryEngine` ([`geometry.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/geometry.py))
Definește operațiile geometrice pure (2D):
- `regularize_90(polygon, tolerance)`
- `fit_canonical_rectangle(polygon)`
- `validate_topology(polygon) -> (bool, str)`
- `compute_area(polygon) -> float`
- `compute_boundary_rmse(candidate, reference)`

### 4.4 `BaseDomainPack` & `DomainCapability` ([`domain.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/domain.py))
Definește ciclul de viață al oricărui Domain Pack:
- Enumerarea `DomainMaturity` (`MATURE`, `PARTIAL`, `EXPERIMENTAL`, `FUTURE`).
- Interfața abstractă `BaseDomainPack` care forțează declararea explicită a capabilităților deterministe vs AI.

### 4.5 `CadastralPoint` & `TopoLTLayer` ([`cadastre.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/cadastre.py))
Izolează legislația românească (ANCPI Ordinul 600/2023) în afara Core-ului universal:
- Straturile TopoLT: `1CC` (construcție de bază), `2CC` (anexă), `CP` (limită imobil), `VARFURI`, `NUMERE_PCT`.
- `CadastralPoint` expune metoda `as_pad_row()` care formatează punctele cu precizie de 2 zecimale pentru tabelul de coordonate PAD.

### 4.6 `IVisionEngine` ([`vision.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/vision.py))
Separat complet de LLM:
- Procesează imagini RGB și `VisionPrompt` (bounding box, point prompts).
- Returnează măști binare `np.ndarray` și scor de încredere IoU, gata de transmis către vectorizare.

### 4.7 `ApprovalRequest` & `ApprovalDecision` ([`workflow.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/workflow.py))
Interfața formală a porților umane (Human-in-the-Loop):
- Când un task depășește pragul de risc (ex. modificarea limitelor cadastrale), se emite un `ApprovalRequest`.
- Executorul este blocat în starea `AWAITING_APPROVAL` până la primirea deciziei semnate a persoanei autorizate.

---

## 5. REZULTATELE TESTĂRII & VERIFICĂRII REGRESIEI

### 5.1 Teste Contracte Noi (`test_contracts.py`):
```text
Ran 8 tests in 0.001s
OK
```
1. `test_01_common_geo_object_contracts` — Validat.
2. `test_02_geodesy_and_crs_metadata_contracts` — Validat.
3. `test_03_domain_pack_abstraction` — Validat.
4. `test_04_cadastral_point_and_pad_table_contracts` — Validat.
5. `test_05_vision_engine_contracts_decoupling` — Validat.
6. `test_06_approval_request_and_decision_lifecycle` — Validat.
7. `test_07_validation_contracts_reporting` — Validat.
8. `test_08_provenance_contract_serialization` — Validat.

### 5.2 Teste de Înghețare Faza 1 (`test_phase1_golden_freeze.py`):
```text
Ran 5 tests in 0.015s
OK
```
Toate cele 14 fișiere Ground Truth și cele 23 module critice au sumele de control SHA-256 identice.

### 5.3 Test Suite General (`stratum_ro/test/`):
```text
Ran 227 tests in 28.558s
OK (skipped=9)
```
- **218 teste passed**.
- **9 teste skipped** (strict PyQGIS C++ GUI context).
- **0 eșecuri**.

---

## 6. PRECONDIȚII ȘI REGULI PENTRU FAZA 3 (CORE EXTRACTION)

Având contractele formale definite, Faza 3 (**Core Extraction**) va putea începe în siguranță:

### Permis în Faza 3:
- Crearea pachetelor concrete în `stratum_ro/core/` (ex. `core/geodesy/`, `core/geometry/`, `core/qa_qc/`).
- Mutarea treptată a funcțiilor matematice din `vectorizer.py` în `core/geometry/regularizer.py`, **păstrând aliase de import retrocompatibile în `vectorizer.py`**.
- Rularea la fiecare pas a testelor `test_phase1_golden_freeze.py` și `test_contracts.py`.

### Interzis în Faza 3:
- NU șterge fișierele vechi înainte ca toate testele să treacă prin aliase retrocompatibile.
- NU altera logica matematică a regularizării 90° sau calculul de suprafață.

---

**STATUS FINAL: PHASE 2 COMPLETE — FORMAL CONTRACTS ESTABLISHED & VERIFIED.**
