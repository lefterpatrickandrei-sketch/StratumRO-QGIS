# Shared main QGIS display checkpoint — 2026-10-17

Owner requested showing the results in the main project and versioning every useful artifact, regardless of format.

The existing shared project is `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`. Its active Lot3 group is `LOT3_REPARAT_20261017_NEVALIDAT`; cyan layer `LOT3 - 20 ipoteze / NECESITA VERDICT` uses `lot3_repairs_20261017/selected_v3/lot3_repaired.gpkg`. Twenty roof surfaces belong to ten cases; no owner verdict changed.

QGIS was brought forward, maximized, the active group expanded and historical groups collapsed. Auxiliary log/search/processing/browser docks were hidden to enlarge the map. All Lot3 cases are in the saved overview. Use the existing `Lot3 reparat / T11` through `T20` bookmarks to inspect each case closely.

`live_main_window.png` and `live_canvas.png` capture the actual running main project. `lot3_main_overview.png` is the native map export. Initial smaller-window captures remain diagnostic history. `display_verification.json` confirms path, active data source, count, visibility and saved state.

All 218 files listed in the preceding repair manifest were checked against their SHA-256 hashes and their Git tracking status. They match the committed repair checkpoint `139cb7c`; the prior implementation checkpoint is `b2bd3ca`. This new checkpoint includes the display helper code, current project view, captures, JSON evidence and this note. No videos were created. Original external imagery and unrelated agents' historical files are not claimed to be newly archived by this check. No remote push is performed.

Reusable display helper: `tools/qgis_show_lot3_main_review.py`, executed inside the existing QGIS MCP session. Its new-output-directory guard prevents overwriting evidence accidentally; inspect current state before another run.
