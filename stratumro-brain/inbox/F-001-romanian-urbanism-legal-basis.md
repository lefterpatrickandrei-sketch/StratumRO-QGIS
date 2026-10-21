---
id: F-001
type: fact
status: proposed
author: perplexity-computer
source_type: public
sources:
  - url: https://www.juridice.ro/846860/modificari-esentiale-privind-dezvoltarea-proiectelor-imobiliare-in-romania-noul-cod-al-urbanismului.html
    retrieved: 2026-10-21
  - url: https://www.aicps.ro/stiri/tehnic/a-intrat-in-vigoare-codul-amenajarii-teritoriului-urbanismului-si-constructiilor-catuc-25-august-2026
    retrieved: 2026-10-21
  - url: https://www.bpv-grigorescu.com/ro/noutati-si-publicatii/publicatii/noul-cod-al-amenajarii-teritoriului-urbanismului-si-constructiilor-din-romania-adoptat-legea-nr-1692026
    retrieved: 2026-10-21
  - url: https://sintact.ro/legislatie/monitorul-oficial/codul-amenajarii-teritoriului-urbanismului-si-17050344/ks-ii-cz-viii
    retrieved: 2026-10-21
  - url: https://legislatie.just.ro/Public/DetaliiDocument/270782
    retrieved: 2026-10-21
confidence: medium
created: 2026-10-21
recheck_by: 2027-01-21
cssclasses:
  - note-fact
supersedes: []
---
# F-001 Romanian urbanism legal basis (as of 21 October 2026)

Claims [PUB]:
- Law 169/2026 (Code of Territorial Planning, Urbanism and Construction) was published on 10 August 2026 (Official Gazette 661) and entered into force on 25 August 2026.
- It repeals Law 350/2001 and Law 50/1991.
- Art. 573: PUGs older than 7 years are to be updated within 3 years; existing PUGs stay valid until then. Art. 582: procedures started earlier follow the earlier rules; new PUG documentation after entry into force is started in GIS format.
- Order 904/2023 (technical norms for spatial datasets of urbanism documentation): GeoPackage 1.3.1 or higher, EPSG:3844, simple geometries, no overlaps and no gaps in functional zoning.

Not verified: whether Order 233/2016 and Order 904/2023 apply unchanged under the Code; the contents of MDLPA Orders 975/2026 and 1,022/2026; how to obtain parcel and intravilan data officially.

Affects: `stratum_ro/pug_product.py` still cites Law 350/2001 [REPO].
