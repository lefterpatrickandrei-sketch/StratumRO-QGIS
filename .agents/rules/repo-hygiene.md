---
name: repo-hygiene
description: Prevent accidental binary blob commits and enforce clean repository root structure
---

# Repository Hygiene Rule

## Pre-Commit Checks (MANDATORY)

Before any `git add .`, `git add -A`, or `git commit -a`:

1. **Run `git status --short`** and verify NO binary blobs are staged:
   - Forbidden extensions: `*.tif`, `*.gpkg` (>10MB), `*.onnx` (>100MB), `*.qgz`, `*.kmz`, `*.las`, `*.laz`, `*.pt`, `*.pth`, `*.shp`, `*.dbf`
   - Exception: `models/sam2/sam2_decoder.onnx` (<16 MB) is explicitly allowed

2. **Clean root policy:** Only these files belong at repository root:
   - `README.md`, `LICENSE`, `AGENTS.md`, `requirements.txt`, `setup.py`/`pyproject.toml`
   - `.gitignore`, `.env.example`, `metadata.txt`
   - All planning/architecture documents → `docs/` or `workspace/`
   - All scripts → `scripts/` or `tools/`

3. **Directories that MUST be in `.gitignore`:**
   - `national_server/` (downloaded WMS/WFS data, ~2 GB)
   - `projects/` (large QGIS project bundles)
   - `workspace/output/cache_*` (tile cache files)
   - `.kilo/` (adversarial reviewer workspace)
   - `models/*.onnx` except `sam2_decoder.onnx`

4. **Size gate:** Files >10 MB must not be committed without explicit justification documented in the commit message.

## Post-Push Verification

After `git push`, verify with:
```bash
git rev-list --count origin/main..HEAD  # Should be 0
```
