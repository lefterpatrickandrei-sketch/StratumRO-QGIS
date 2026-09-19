# StratumRO — UI Interaction Capability Matrix (MD 10)

Generated: 2026-09-18
Target Application: QGIS 3.40.0-Bratislava (Windows 11 x64)

## 1. Capability Status Matrix

| Layer | Capability | Status | Evidence | Key Metrics |
|---|---|---|---|---|
| **Qt Semantic** | **Inspection** (find actions, menus, dialogs) | **AVAILABLE** | `workspace/e2e/ui_test.json` | Located `mActionAddOgrLayer` on `mLayerToolBar` |
| **Qt Semantic** | **Interaction** (trigger actions, open/close dialogs) | **AVAILABLE** | `workspace/e2e/ui_test.json`, `ui_test_before.png`, `ui_test_during.png`, `ui_test_after.png` | Triggered action, opened `QgsDataSourceManagerDialog`, dismissed via `QTest.keyClick(Qt.Key_Escape)` |
| **OS Level** | **Inspection** (find window, get element rects) | **AVAILABLE** | `workspace/e2e/os_ui_test.json` | Discovered 364 UIA descendants; located rect `[1627, 187, 1667, 225]` |
| **OS Level** | **Interaction** (real mouse move, click, verify diff) | **AVAILABLE** | `workspace/e2e/os_ui_test.json`, `os_ui_run1_before.png`, `os_ui_run1_after.png`, `os_ui_run2_before.png`, `os_ui_run2_after.png` | Physical mouse moved to `(1647, 206)`, clicked via `pyautogui.click()`, visual diff bbox `(0, 0, 1394, 38)`, pixel diff ratio `0.034433` (3.44%), coordinate variance `0.0 px` across 2 consecutive runs |

---

## 2. Technical Evidence & Provenance

### A. Layer 1 — Qt Semantic Automation (`tools/qt_ui_probe.py`)
- **Execution Mechanism**: QGIS startup via `--code` executing inside `qgis-bin.exe` with initialized `QgisInterface`.
- **Target Located**: Action `mActionAddOgrLayer` discovered deterministically on `mLayerToolBar`.
- **Action Trigger**: Invoked `action.trigger()`.
- **Dialog Validation**: Verified instantiation of `QgsDataSourceManagerDialog` (`isVisible() == True`).
- **Dismissal**: Synthesized `QTest.keyClick(dialog, Qt.Key_Escape)`. Verified dialog destruction/closure (`dialog.isVisible() == False`).
- **Visual Artifacts**:
  - `workspace/e2e/evidence/ui_test_before.png` (344,748 bytes, 1920x1051)
  - `workspace/e2e/evidence/ui_test_during.png` (74,232 bytes, dialog focus)
  - `workspace/e2e/evidence/ui_test_after.png` (344,922 bytes, 1920x1051)
- **Visual Diff**: Distinct SHA256 hashes, diff bbox `(13, 7, 563, 21)` matching status/messageBar update.

### B. Layer 2 — OS-Level Human-Like Perception-Action Loop (`tools/os_ui_driver.py`)
- **Execution Mechanism**: External Python process orchestrating physical cursor and GDI capture.
- **Screen Resolution**: 1920 x 1080 (Windows Desktop).
- **Target Element**: `CheckBox 'Toggle Snapping'` located dynamically via `pywinauto` UIA hierarchy (element rect `[1627, 187, 1667, 225]`).
- **Physical Mouse Control**:
  - `pyautogui.moveTo(1647, 206, duration=0.6)`
  - `pyautogui.click(1647, 206)`
- **Surface Capture**: Direct Windows GDI `PrintWindow` with `PW_RENDERFULLCONTENT`.
- **Perceptual Verification**:
  - **Run 1**: Located rect `[1627, 187, 1667, 225]`, Click point `(1647, 206)`, Diff bbox `(0, 0, 1394, 38)`, Diff ratio `0.034433` (3.44%).
  - **Run 2**: Located rect `[1627, 187, 1667, 225]`, Click point `(1647, 206)`, Diff bbox `(0, 0, 1394, 38)`, Diff ratio `0.034433` (3.44%).
- **Repeatability Variance**: `0.0 px` coordinate variance across runs (exceeds the `<= 1.0 px` gate).
- **Visual Artifacts**:
  - `workspace/e2e/evidence/os_ui_run1_before.png` (298,818 bytes)
  - `workspace/e2e/evidence/os_ui_run1_after.png` (298,845 bytes)
  - `workspace/e2e/evidence/os_ui_run2_before.png` (298,845 bytes)
  - `workspace/e2e/evidence/os_ui_run2_after.png` (298,818 bytes)

---

## 3. Comparison & Architectural Recommendation

| Dimension | Qt Semantic Layer | OS Physical Mouse Layer |
|---|---|---|
| **Precision** | Exact object pointer / deterministic slot invocation | Pixel coordinates derived from UIA bounding box |
| **Stability** | Immune to screen resolution, scaling (DPI), or window occlusion | Sensitive to window positioning, focus stealing, and DPI scaling |
| **Speed** | Millisecond response (~5ms per action) | Trajectory duration required (~600ms mouse glide) |
| **Verification** | In-process Qt state assertion + pixmap grab | Perceptual image diff + repeatability variance check |
| **Recommended Use** | Production pipeline automation & regression testing | Interactive desktop demonstrations & end-user visual walkthroughs |
