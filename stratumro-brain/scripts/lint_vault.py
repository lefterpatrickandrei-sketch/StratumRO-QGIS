#!/usr/bin/env python3
"""Check the memory vault against MEMORY_RULES.md.

Usage:  python scripts/lint_vault.py [--root .] [--today YYYY-MM-DD]
Exit code 1 if any error is found. Warnings do not change the exit code.
Only the Python standard library is used.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

TYPES = {"decision": "D", "fact": "F", "lesson": "L", "handoff": "H", "model-note": "M"}
STATUS = {"proposed", "approved", "verified", "deprecated"}
CANON_STATUS = {"approved", "verified", "deprecated"}
SOURCE_TYPES = {"owner", "repo", "public", "agent-inference", "measured"}
CONFIDENCE = {"high", "medium", "low"}
REQUIRED = ["id", "type", "status", "author", "source_type", "sources", "confidence", "created", "recheck_by"]
CHECKED_DIRS = ("canon", "inbox")
SECRET_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "API key (sk-)"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API key"),
]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")


def split_frontmatter(text):
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


def parse_fm(lines):
    data, key = {}, None
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t", "-")) and key is not None:
            item = raw.strip()
            if item.startswith("-"):
                if not isinstance(data[key], list):
                    data[key] = []
                data[key].append(item[1:].strip())
            continue
        if ":" in raw:
            k, v = raw.split(":", 1)
            key = k.strip()
            v = re.sub(r"\s+#.*$", "", v).strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                data[key] = [x.strip() for x in inner.split(",")] if inner else []
            elif v == "":
                data[key] = ""
            else:
                data[key] = v.strip("'\"")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--today", default=None)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    errors, warns = [], []
    ids = {}

    skip_parts = {".git", ".obsidian", ".agents", "node_modules", "_templates", "code-map", "archive"}
    md_files = [p for p in root.rglob("*.md") if not (set(p.relative_to(root).parts) & skip_parts)]
    stems = {p.stem for p in root.rglob("*.md")} | {p.name for p in root.rglob("*.base")} | {p.name for p in root.rglob("*.canvas")}
    stems |= {p.stem for p in root.rglob("*.base")} | {p.stem for p in root.rglob("*.canvas")}

    def rel(p):
        return p.relative_to(root).as_posix()

    for p in md_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        r = rel(p)
        for rx, label in SECRET_PATTERNS:
            if rx.search(text):
                errors.append(f"{r}: possible secret ({label})")
        body_no_code = re.sub(r"```.*?```", "", text, flags=re.S)
        for m in LINK_RE.finditer(body_no_code):
            tgt = m.group(1).strip()
            if tgt.split("/")[-1] not in stems and tgt not in stems:
                warns.append(f"{r}: broken link [[{tgt}]]")
        top = p.relative_to(root).parts[0]
        if top not in CHECKED_DIRS or p.name.lower() == "readme.md":
            continue
        fm_lines, body = split_frontmatter(text)
        if fm_lines is None:
            errors.append(f"{r}: missing frontmatter")
            continue
        fm = parse_fm(fm_lines)
        for k in REQUIRED:
            if k not in fm:
                errors.append(f"{r}: missing field '{k}'")
        t = fm.get("type")
        if t not in TYPES:
            errors.append(f"{r}: type '{t}' not in {sorted(TYPES)}")
        nid = fm.get("id", "")
        if t in TYPES and not re.fullmatch(TYPES[t] + r"-\d{3,}", nid or ""):
            errors.append(f"{r}: id '{nid}' should look like {TYPES[t]}-001 for type {t}")
        if nid:
            if nid in ids:
                errors.append(f"{r}: duplicate id {nid} (also {ids[nid]})")
            ids[nid] = r
            if not p.stem.startswith(nid):
                warns.append(f"{r}: file name should start with the id {nid}")
        st = fm.get("status")
        if st not in STATUS:
            errors.append(f"{r}: status '{st}' not in {sorted(STATUS)}")
        if top == "canon" and st not in CANON_STATUS:
            errors.append(f"{r}: status '{st}' is not allowed in canon/ (use inbox/ until approved)")
        if top == "inbox" and st not in (None, "proposed"):
            warns.append(f"{r}: inbox note has status '{st}'; promote it to canon/ or set proposed")
        if fm.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{r}: source_type '{fm.get('source_type')}' not in {sorted(SOURCE_TYPES)}")
        if fm.get("confidence") not in CONFIDENCE:
            errors.append(f"{r}: confidence '{fm.get('confidence')}' not in {sorted(CONFIDENCE)}")
        for k in ("created", "recheck_by"):
            v = fm.get(k, "")
            if v and not DATE_RE.match(str(v)):
                errors.append(f"{r}: {k} '{v}' is not YYYY-MM-DD")
        owner = fm.get("author") == "owner"
        rb = fm.get("recheck_by", "")
        if not owner and not rb:
            errors.append(f"{r}: non-owner note needs recheck_by")
        if rb and DATE_RE.match(str(rb)):
            try:
                if dt.date.fromisoformat(rb) < today:
                    warns.append(f"{r}: stale, recheck_by {rb} is past")
            except ValueError:
                errors.append(f"{r}: invalid date {rb}")
        if fm.get("source_type") in ("public", "repo", "measured") and not fm.get("sources"):
            warns.append(f"{r}: source_type {fm.get('source_type')} but sources list is empty")
        words = len(body.split())
        if words > 450:
            warns.append(f"{r}: {words} words; split into smaller notes")

    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\nchecked {len(md_files)} markdown files: {len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
