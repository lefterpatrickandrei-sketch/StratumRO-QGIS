# Propunere de publicare — necesită alegerea proprietarului

Repository public: `lefterpatrickandrei-sketch/StratumRO-QGIS`.
Remote main citit: `08524dfa5c45c70e056c69776e88852f558e98e7`.

Opțiunea recomandată este un branch de publicare cu un **draft pull request**, fără merge automat în main. Acesta ar cuprinde cele 35 commituri locale anterioare și cele două checkpointuri ale reorganizării. Nu ar fi un PR exclusiv de documentație: include și progresul Lot2/Lot3/Lot4, fuziune, scanare regională și dovezile lor.

Working tree-ul preexistent al altor agenți rămâne exclus. Nu se publică cele 936 fișiere neversionate doar pentru că au fost inventariate. Nu se schimbă protecții, istoricul, licențe sau stocare LFS.

## Titlu propus

Checkpoint StratumRO roof workflows, review evidence and shared repository documentation

## Descriere propusă

GitHub main predates the local roof-workflow and visual-review development. This checkpoint brings the existing local progress into a reviewable branch and consolidates repository navigation for all coding agents.

The branch includes the preceding T10/Lot3/Lot4 work, local RGB–LiDAR experiments, automatic regional roof proposals and their committed review artifacts. The regional output remains NOT PRODUCTION READY; roof proposals are not measured ground footprints or accepted cadastral inventory. Existing reports retain the distinction between real inference, cached-observation packaging and tests with a model double.

The documentation cleanup archives 13 historical root reports without discarding their content, preserves exact original entry-document snapshots, and introduces shared project state, system diagrams, repository rules and handoff guidance. It does not change production algorithms or adopt other agents' uncommitted work.

Validation of the cleanup: 18 archived files match recorded SHA-256 including Git object bytes; 16 pre-existing dirty tracked paths remain unchanged; all 936 initial untracked paths remain present; the shared QGIS project is unchanged; 67 current navigation links pass. No product tests or inference were rerun for this documentation step. Previous runtime checks and limitations are recorded with their respective evidence. CI status for the eventual published branch must be inspected separately.

No automatic merge is requested.
