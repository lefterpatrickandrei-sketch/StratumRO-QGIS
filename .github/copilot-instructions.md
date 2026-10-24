# Copilot instructions for StratumRO-QGIS

The full, shared rules are in [AGENTS.md](../AGENTS.md). Read it first. The hybrid tool split is in
[docs/HYBRID_DEV_WORKFLOW.md](../docs/HYBRID_DEV_WORKFLOW.md).

Non-negotiable (short form):

1. All cadastral geometry is in **Stereo 70 (EPSG:3844)**, metric. Do not store or analyse in WGS84.
2. **Never invent, interpolate or move coordinates.** LLMs do not compute geometry; shapely/GDAL/pyproj do.
3. `ADMIS` in code or attributes is an internal test state, **not an approval**. Only the authorised surveyor approves.
4. Distinct physical objects stay distinct. Do not force merges into artificial rectangles.
5. Do not add a new core for an existing function. Find the existing implementation and callers first.
6. Do not push, merge, reset, stash or delete other agents' files. Run `git status -s` before editing.
7. No secrets in files. Never read or copy `.env`.

Before handing over, run:

```powershell
python scripts/validate_project.py --mode fast
python -m unittest discover stratum_ro/test
```

Copilot's role here: completions, boilerplate, small edits, tests, QGIS plugin glue. Leave
architecture and heavy debugging to the Claude and Antigravity sessions.
