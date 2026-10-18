GitHub main predates the local roof-workflow and visual-review development. This checkpoint brings the existing local progress into a reviewable branch and consolidates repository navigation for all coding agents.

The branch includes the preceding T10/Lot3/Lot4 work, local RGB–LiDAR experiments, automatic regional roof proposals and their committed review artifacts. The regional output remains NOT PRODUCTION READY; roof proposals are not measured ground footprints or accepted cadastral inventory. Existing reports retain the distinction between real inference, cached-observation packaging and tests with a model double.

The documentation cleanup archives 13 historical root reports without discarding their content, preserves exact original entry-document snapshots, and introduces shared project state, system diagrams, repository rules and handoff guidance. It does not change production algorithms or adopt other agents' uncommitted work.

Validation of the cleanup: 18 archived files match recorded SHA-256 including Git object bytes; 16 pre-existing dirty tracked paths remain unchanged; all 936 initial untracked paths remain present; the shared QGIS project is unchanged; 67 current navigation links pass. No product tests or inference were rerun for this documentation step. Previous runtime checks and limitations are recorded with their respective evidence. CI status for the eventual published branch must be inspected separately.

No automatic merge is requested.


CI update: the initial Linux matrix jobs failed. The Ubuntu/Python 3.10 job reports 443 tests, 4 failures, 19 errors and 9 skips, including missing anthropic/fastapi/torch, unreconciled hash invariants and a Windows-specific assertion. The public job log and structured diagnosis are preserved in workspace/repository_cleanup_20261018/. This documentation cleanup does not repair those failures. Separate authorization has been requested for CI/test changes; keep this PR in draft without merging.
