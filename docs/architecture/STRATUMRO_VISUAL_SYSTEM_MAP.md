# StratumRO — Harta Vizuală de Arhitectură și Sistem 🗺️📐

**Versiune:** 1.0 (Post-Sincronizare Arhitecturală 2026-09-19)  
**Standard de Guvernanță:** `AGENTS.md` (Cele 8 Reguli Științifice bazate pe Evidențe)  
**Stare Teste:** 193 teste unitare descoperite (184 trecute, 9 omise, 0 eșuate)  

---

## 1. 👥 Harta Actorilor și a Fluxului de Lucru Activ

Acesta este singurul flux operațional aprobat pentru dezvoltarea și auditarea StratumRO:

```mermaid
flowchart TD
    subgraph SursaDeDecizie["1. Decident Uman"]
        USER["👤 USER (TU)<br/>Direcție strategică & aprobare"]
    end

    subgraph DezvoltareExecutie["2. Motor Principal de Execuție"]
        AGY["⚡ ANTIGRAVITY<br/>Inginerie, cod, teste, măsurători, git"]
    end

    subgraph Platforma["3. StratumRO (Platforma Tehnică)"]
        direction TB
        QGIS["🖥️ QGIS Desktop & Processing Framework"]
        GEO["📐 Motoare Geodezice Deterministe (Python/GEOS)"]
        SENSORS["🛰️ Date Reale (LiDAR, Ortofoto, Cadastru)"]
        PROV["🤖 Provideri AI (OpenRouter, NVIDIA NIM, Local Mock)"]
        MCP["🔌 Server MCP (Audit & Inspecție pe stdio)"]
    end

    subgraph AuditAdversarial["4. Control & Securitate"]
        KILO["🛡️ KILO<br/>Reviewer adversarial, detectare metric leakage, anti no-op"]
    end

    subgraph SursaDeAdevar["5. Sursa Unică de Adevăr"]
        GITHUB["🐙 GITHUB (origin/main)<br/>Cod autoritar, date înghețate, teste"]
    end

    USER -->|Instrucțiuni & Cerințe| AGY
    AGY -->|Scrie cod, rulează teste| Platforma
    Platforma -->|Evidențe, rapoarte, diff-uri| KILO
    KILO -->|Review adversarial, validare| AGY
    AGY -->|git commit & push| GITHUB
    GITHUB -.->|Referință stabilă| USER

    classDef human fill:#2b3a42,stroke:#4f9da6,stroke-width:2px,color:#fff;
    classDef dev fill:#1f3c88,stroke:#5893d4,stroke-width:2px,color:#fff;
    classDef plat fill:#232931,stroke:#4ecca3,stroke-width:2px,color:#fff;
    classDef audit fill:#3f2e56,stroke:#a64942,stroke-width:2px,color:#fff;
    classDef truth fill:#1b262c,stroke:#f8b500,stroke-width:2px,color:#fff;

    class USER human;
    class AGY dev;
    class QGIS,GEO,SENSORS,PROV,MCP plat;
    class KILO audit;
    class GITHUB truth;
```

> [!NOTE]
> **Claude Desktop** este **RETRAS** din fluxul activ (feedback-ul anterior este doar istoric).

---

## 2. 🧠 Modelul Mental Dual: Astăzi vs. Ținta Faza 4

Separarea fundamentală dintre realitatea implementată pe disc și specificația arhitecturală țintă:

```mermaid
flowchart LR
    subgraph REALITATE["STRATUMRO ASTĂZI (Implementat pe Disc)"]
        direction TB
        A1["🛰️ Ortofoto + LiDAR Stereo 70"]
        A2["⚡ SAM 2 ONNX DirectML / CPU + nDSM"]
        A3["📐 Regularizare 90° Deterministă"]
        A4["🧪 Validare Geodezică (IoU, HD95)"]
        A5["📦 Livrabile CAD TopoLT (DXF, .CP, PAD)"]
        A6["👥 Punct Critic: Semnătură Geodez Autorizat"]

        A1 --> A2 --> A3 --> A4 --> A5 --> A6
    end

    subgraph TINTA["STRATUMRO ȚINTĂ (Faza 4 - Platformă GeoAI)"]
        direction TB
        B1["🎯 USER TASK"]
        B2["📋 TaskSpec (CRS, bounds, risk, livrabile)"]
        B3["🔍 Context Engine (hardware, layers, provideri)"]
        B4["🧭 Capability Routing & Fallback"]
        B5["⚙️ Workflow DAG & Execution Loop"]
        B6["🛡️ Dynamic Risk Gates & Verification"]
        B7["📊 Evidence Graph & Provenance"]

        B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7
    end

    REALITATE -.->|Evoluție incrementală prin felii mici testate| TINTA

    classDef today fill:#1a3636,stroke:#40534c,stroke-width:2px,color:#d6efd8;
    classDef target fill:#2c3e50,stroke:#3498db,stroke-width:2px,color:#ecf0f1;
    class A1,A2,A3,A4,A5,A6 today;
    class B1,B2,B3,B4,B5,B6,B7 target;
```

---

## 3. 🏛️ Harta Componentelor Tehnice pe Disc

Structura celor 5 subsisteme majore din repository:

```mermaid
graph TD
    subgraph SUB1["1. Geomatics & Cadastral Engine (Deterministic Python)"]
        VEC["vectorizer.py<br/>• Regularizare 90°<br/>• Dreptunghi canonic 4-noduri<br/>• Partiție planară"]
        CAD["cad_exporter.py<br/>• TopoLT: 1CC, 2CC, CP, VARFURI<br/>• Generator Tabele PAD<br/>• Format .CP e-Terra"]
        V3D["volumetric_3d.py<br/>• Extrudare 3D LoD1 solidă<br/>• MultiPolygonZ în GeoPackage<br/>• OGC CityJSON v1.1"]
    end

    subgraph SUB2["2. Fuziune Senzorială (LiDAR + Raster)"]
        LIDAR["lidar_processor.py<br/>• Ingestie LAS/LAZ (laspy)<br/>• Generare nDSM (H >= 2.5m)<br/>• Filtrare vegetație/sol"]
        ORTHO["ortho_extractor.py<br/>• Slicing VRT/GeoTIFF Stereo 70<br/>• Generare chip-uri 512x512"]
    end

    subgraph SUB3["3. Inferență AI Segmentare"]
        ONNX["onnx_engine.py<br/>• Meta SAM 2 Hiera<br/>• DirectML pe DirectX 12 GPU<br/>• Fallback CPU multithreaded"]
    end

    subgraph SUB4["4. Nucleu AI Decuplat & Rutare"]
        TS["task_spec.py (Faza 4)<br/>• TaskSpec tipizat<br/>• Validare Stereo 70 EPSG:3844<br/>• Anvelopă România"]
        REG["registry.py<br/>• ProviderRegistry<br/>• CapabilityMatch<br/>• Fallback la Local Mock"]
        ROUT["router.py<br/>• Separare Matematică vs AI<br/>• Redirecționare capabilități"]
        EXEC["task_graph.py & executor.py<br/>• DAG asincron cu EventBus<br/>• Gestionare stări sarcini"]
        VLM["vlm_verifier.py<br/>• Inspecție vizuală multimodală<br/>• NVIDIA NIM Vision"]
    end

    subgraph SUB5["5. Integrare QGIS & Interfețe"]
        DOCK["stratum_ro_dockwidget.py<br/>• Interfață vizuală QGIS<br/>• Selecție AOI & straturi"]
        PROC["processing_provider.py<br/>• Algoritm QGIS Processing<br/>• Headless CLI: qgis_process"]
        MCP_S["mcp/stratumro_server.py<br/>• Server MCP pe stdio<br/>• Unelte de inspecție și audit"]
    end

    SUB2 --> SUB3
    SUB3 --> SUB1
    SUB4 --> SUB1
    SUB5 --> SUB4
    SUB5 --> SUB1

    classDef c1 fill:#1b4965,stroke:#62b6cb,stroke-width:2px,color:#fff;
    classDef c2 fill:#2b2d42,stroke:#8d99ae,stroke-width:2px,color:#fff;
    classDef c3 fill:#3d5a80,stroke:#98c1d9,stroke-width:2px,color:#fff;
    classDef c4 fill:#14213d,stroke:#fca311,stroke-width:2px,color:#fff;
    classDef c5 fill:#22223b,stroke:#c9ada7,stroke-width:2px,color:#fff;

    class VEC,CAD,V3D c1;
    class LIDAR,ORTHO c2;
    class ONNX c3;
    class TS,REG,ROUT,EXEC,VLM c4;
    class DOCK,PROC,MCP_S c5;
```

---

## 4. 🔄 Pipeline-ul Cadastral Detaliat: De la Senzor la Livrabil

```mermaid
sequenceDiagram
    autonumber
    actor Inginer as Inginer Geodez (QGIS)
    participant QGIS as Plugin StratumRO
    participant Fusion as Fuziune Senzorială
    participant AI as SAM 2 DirectML
    participant Geom as Motor Regularizare 90°
    participant CAD as Exportator TopoLT / PAD
    participant VLM as Verificator Multimodal (NIM)

    Inginer->>QGIS: Selectează AOI în Stereo 70 (EPSG:3844)
    QGIS->>Fusion: Extrage nDSM din LiDAR (H >= 2.5m) + Ortofoto
    Fusion->>AI: Trimite chip orto + prompte din nDSM
    AI->>AI: Segmentare binară mască clădiri
    AI->>Geom: Trimite poligoane brute
    Geom->>Geom: Regularizare ortogonală 90° (MRR canonic)
    Geom->>Geom: Retragere streașină (-0.40m) & partiție planară
    Geom->>VLM: Trimite chip clădire pentru control tipologie
    VLM-->>Geom: Scor încredere & confirmare
    Geom->>CAD: Generează DXF (1CC, 2CC, CP), .CP, PAD
    CAD->>Inginer: Încarcă livrabilele în QGIS Canvas & 3D
    Note over Inginer: ⚠️ Verificare umană & semnare oficială ANCPI
```

---

## 5. 🤖 Matricea Providerilor AI și Ierarhia de Fallback

Cum rezolvă `ProviderRegistry.resolve_provider()` fiecare solicitare:

```mermaid
flowchart TD
    REQ["Solicitare Sarcină<br/>(TaskSpec + ProviderCapability)"] --> CHECK_MATH{"Este sarcină de<br/>calcul topo / CAD?"}

    CHECK_MATH -- DA --> LOCAL_MATH["📐 Python Determinist Local<br/>(Zero halucinații LLM!<br/>Shapely, GEOS, ezdxf)"]

    CHECK_MATH -- NU --> PREF{"Există provider<br/>preferat specificat?"}

    PREF -- DA și DISPONIBIL --> MATCH_PREF["Folosește Providerul Preferat"]

    PREF -- NU sau INDISPONIBIL --> FILTER["Filtrează providerii activi<br/>după capabilitate"]

    FILTER --> CANDIDATES{"Există candidați<br/>activi în rețea?"}

    CANDIDATES -- DA --> ROUTE_CLOUD["Rutează la Providerul Activ:<br/>• OpenRouter (Llama 3.3 70B - 722ms)<br/>• NVIDIA NIM (Llama 3.2 11B Vision - 652ms)"]

    CANDIDATES -- NU --> ALLOW_FB{"allow_fallback = True?"}

    ALLOW_FB -- DA --> LOCAL_MOCK["🛡️ Local Deterministic Mock<br/>(deterministic-planner-v1 - 0.0ms)<br/>Garanție 100% disponibilitate offline"]

    ALLOW_FB -- NU --> FAIL["Returnează None<br/>(Eroare controlată)"]

    classDef math fill:#005f73,stroke:#0a9396,stroke-width:2px,color:#fff;
    classDef cloud fill:#9b2226,stroke:#ae2012,stroke-width:2px,color:#fff;
    classDef mock fill:#2b9348,stroke:#55a630,stroke-width:2px,color:#fff;
    classDef gate fill:#343a40,stroke:#6c757d,stroke-width:2px,color:#fff;

    class LOCAL_MATH math;
    class ROUTE_CLOUD cloud;
    class LOCAL_MOCK mock;
    class CHECK_MATH,PREF,FILTER,CANDIDATES,ALLOW_FB gate;
```

---

## 6. 🛑 Liniile Roșii și Regulile de Siguranță Geodezică

| Domeniu | Regula Absolută StratumRO | Motivul Tehnic / Legal |
| :--- | :--- | :--- |
| **Coordonate Stereo 70** | **Strict Python Determinist Local** | Niciun LLM nu are voie să inventeze sau să aproximeze coordonate geodezice ($X, Y, Z$) sau tabele PAD. |
| **Statut Legal Cadastral** | **Pre-Cadastru Asistat (Human-in-the-Loop)** | Generarea fișierelor DXF / .CP nu constituie intabulare autonomă; semnătura geodezului autorizat ANCPI este legal obligatorie. |
| **Limita de Recall Phase 3** | **Raportare transparentă (6.15%)** | Nu se ascund limitele reale (4 TP din 65 referințe); sistemul accelerează digitalizarea, nu garantează perfecțiunea automată. |
| **Poarta de Testare** | **193 Teste Unitare (184 Passed, 0 Failed)** | Nicio modificare de cod nu este acceptată fără rularea suitei complete și raportarea exactă a stării. |
| **Integritate Date** | **Ground Truth Înghețat** | Fișierele `tier1_teren.geojson` și predicțiile benchmark sunt read-only; zero contaminare a datelor de test. |
