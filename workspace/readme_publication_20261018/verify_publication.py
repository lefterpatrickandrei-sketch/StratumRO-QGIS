"""Verify README assets, committed local targets and protected pre-existing edits."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()

tracked = set(git("ls-files").splitlines())
docs = ["README.md", "docs/METHODS_AND_SOURCES.md", "docs/README.md",
        "docs/PROJECT_STATE.md", "docs/AGENT_HANDOFF.md",
        "workspace/readme_publication_20261018/README.md"]
errors, links = [], []
for name in docs:
    path = ROOT/name
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        parsed = urlsplit(target)
        if parsed.scheme or not parsed.path:
            continue
        dest = (path.parent/unquote(parsed.path)).resolve()
        rel = dest.relative_to(ROOT).as_posix()
        links.append({"from": name, "target": rel})
        if not dest.exists():
            errors.append(f"Missing target {name}: {rel}")
        if rel not in tracked and not dest.is_dir():
            errors.append(f"Target not staged/tracked {name}: {rel}")
    if text.count("$$") % 2:
        errors.append(f"Unbalanced display math: {name}")
manifest = json.loads((HERE/"figure_manifest.json").read_text(encoding="utf-8"))
for group in ("source_files", "figures"):
    for path, sha in manifest[group].items():
        if digest(ROOT/path) != sha:
            errors.append(f"Figure/source hash mismatch: {path}")
for path in (ROOT/"docs/assets/readme").glob("*.svg"):
    ElementTree.parse(path)
archive = json.loads((HERE/"archive_manifest.json").read_text(encoding="utf-8"))
if digest(ROOT/archive["archive_path"]) != archive["sha256"]:
    errors.append("Archived README hash mismatch")
original = subprocess.check_output(["git", "show", f'{archive["source_commit"]}:README.md'], cwd=ROOT)
if hashlib.sha256(original).hexdigest() != archive["sha256"]:
    errors.append("Archived README differs from source Git blob")
baseline = json.loads((ROOT/"workspace/repository_cleanup_20261018/baseline.json").read_text(encoding="utf-8"))
for item in baseline["foreign_dirty_tracked"]:
    if digest(ROOT/item["path"]) != item["sha256"]:
        errors.append(f'Foreign edit changed: {item["path"]}')
result = {"status": "PASS" if not errors else "FAIL", "head_at_check": git("rev-parse", "HEAD"),
          "documents_checked": docs, "local_link_count": len(links),
          "foreign_tracked_paths_preserved": len(baseline["foreign_dirty_tracked"]),
          "original_readme_archived_byte_identically": digest(ROOT/archive["archive_path"]) == archive["sha256"] == hashlib.sha256(original).hexdigest(),
          "links": links, "errors": errors,
          "scope": "Documentation and artifact integrity; browser rendering and exact-head CI checked separately"}
(HERE/"verification.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k != "links"}, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))
