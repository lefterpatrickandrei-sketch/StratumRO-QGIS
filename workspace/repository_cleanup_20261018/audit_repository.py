"""Inventory for the owner-approved documentation cleanup; never executes product code.

Run from any directory. Only writes this task's audit directory. No migrations,
Git staging, secrets inspection, inference, or QGIS connection are performed.
"""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REPORTS = [
    "KILO_CONFIGURATION_AUDIT.md", "LOCAL_DATA_AUDIT_REPORT.md",
    "MASTER_AUDIT_FINAL_VALIDARE.md",
    *[f"RAPORT_AUDIT_{n}_REZOLUTIE.md" for n in (5, 6, 7, 8, 10, 11, 12)],
    "RAPORT_AUDIT_FINAL_CONSOLIDAT.md",
    "RAPORT_FINAL_CERTIFICARE_CADASTRALA.md", "walkthrough.md",
]
SNAPSHOTS = {"README.md": "README.original.md",
             "AGENTS.md": "AGENTS.original.txt",
             "CLAUDE.md": "CLAUDE.original.txt"}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def sha(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write(name: str, payload) -> None:
    target = OUT / name
    if target.exists():
        raise FileExistsError(f"Audit snapshots are immutable: {target}")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")


def main() -> None:
    tracked = git("ls-files", "-z").rstrip("\0").split("\0")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z").rstrip("\0").split("\0")
    untracked = [p for p in untracked if p and not p.startswith(OUT.relative_to(ROOT).as_posix() + "/")]
    status = git("status", "--porcelain=v1", "-z", "--untracked-files=no")
    dirty = []
    for line in filter(None, status.split("\0")):
        path = line[3:]
        full = ROOT / path
        dirty.append({"status": line[:2], "path": path,
                      "sha256": sha(full) if full.is_file() else None})

    text_index = {}
    definitions = {}
    imports = {}
    for relative in tracked:
        p = ROOT / relative
        if not p.is_file() or p.stat().st_size > 2 * 1024 * 1024:
            continue
        if p.suffix.lower() not in {".md", ".py", ".yml", ".yaml", ".json", ".html", ".ps1", ".bat", ".txt", ".sh"}:
            continue
        if p.name.startswith(".env") or "mcp_config" in p.name.lower():
            continue
        source = p.read_text(encoding="utf-8-sig", errors="replace")
        text_index[relative] = source
        if relative.startswith("stratum_ro/") and p.suffix == ".py":
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            definitions[relative] = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            imports[relative] = sorted({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module})

    moves = []
    for source in REPORTS:
        p = ROOT / source
        if not p.is_file() or source not in tracked:
            raise ValueError(f"Expected tracked report missing: {source}")
        if any(row["path"] == source for row in dirty):
            raise ValueError(f"Report has another agent's changes: {source}")
        moves.append({"action": "MOVE", "source": source,
                      "destination": f"junk/2026-10-18/root_reports/{source}",
                      "sha256": sha(p), "bytes": p.stat().st_size,
                      "reason": "Historical report, retained as evidence; not the current project entry point.",
                      "inbound_mentions": [f for f, content in text_index.items() if f != source and source in content]})
    for source, archive in SNAPSHOTS.items():
        p = ROOT / source
        if any(row["path"] == source for row in dirty):
            raise ValueError(f"Entry document has another agent's changes: {source}")
        moves.append({"action": "COPY_BEFORE_REPLACE", "source": source,
                      "destination": f"junk/2026-10-18/source_snapshots/{archive}",
                      "sha256": sha(p), "bytes": p.stat().st_size,
                      "reason": "Exact snapshot before owner-approved consolidation; .txt prevents discovery as agent instructions."})
    objects = git("rev-list", "--objects", "origin/main..HEAD")
    sizes = subprocess.check_output(
        ["git", "cat-file", "--batch-check=%(objecttype) %(objectsize) %(rest)"],
        input=objects.encode("utf-8"), cwd=ROOT).decode("utf-8").splitlines()
    large = []
    for line in sizes:
        kind, size, *path = line.split(" ", 2)
        if kind == "blob" and int(size) > 20 * 1024 * 1024:
            large.append({"bytes": int(size), "path": path[0] if path else ""})

    write("baseline.json", {"captured_utc": datetime.now(timezone.utc).isoformat(),
          "head": git("rev-parse", "HEAD").strip(),
          "origin_main_cached": git("rev-parse", "origin/main").strip(),
          "ahead_behind_cached": git("rev-list", "--left-right", "--count", "origin/main...HEAD").strip(),
          "tracked_count": len(tracked), "untracked_count_excluding_this_audit": len(untracked),
          "tracked_by_top_level": dict(Counter(p.split("/")[0] if "/" in p else "(root)" for p in tracked)),
          "foreign_dirty_tracked": dirty, "worktrees_porcelain": git("worktree", "list", "--porcelain"),
          "object_storage": git("count-objects", "-vH"),
          "unpublished_blobs_above_20_mib": large,
          "lfs_version": git("lfs", "version").strip(),
          "lfs_files": git("lfs", "ls-files").splitlines(),
          "verification_scope": "Read-only file/Git/AST inspection. No model, tests, QGIS changes, or publication."})
    write("migration_manifest.json", {"schema_version": 1, "approval": "Owner explicitly approved the 13 moves and 3 snapshots in this chat on 2026-10-18.",
          "status": "APPROVED_NOT_YET_APPLIED", "files": moves,
          "restoration": "Check SHA-256, ensure original destination is free, then Move-Item each MOVE destination back to source. COPY_BEFORE_REPLACE snapshots restore document bytes; archive instruction text is historical, never active policy."})
    write("file_inventory.json", {"tracked_paths": tracked, "untracked_paths_excluding_this_audit": untracked,
          "note": "An inventory is not approval to stage, archive, upload, or delete these files. Ignored files and secret values were not inventoried."})
    write("python_structure.json", {"method": "Static AST, no imports executed; definitions do not prove runtime integration.",
          "definitions": definitions, "from_imports": imports})
    print(f"Saved 4 immutable audit files; {len(moves)} approved actions, {len(dirty)} foreign dirty tracked paths protected.")


if __name__ == "__main__":
    main()
