#!/usr/bin/env python3
"""Generate Markdown map pages of a code repository so it can be browsed in Obsidian.

Usage:  python scripts/code_map.py --repo PATH_TO_CODE_REPO [--out code-map]
Reads only tracked files (git ls-files). Does not modify the code repository.
Standard library only. Output pages are generated: do not edit them by hand.
"""
import argparse
import ast
import datetime as dt
import re
import subprocess
import warnings
from collections import defaultdict
from pathlib import Path


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def first_heading(path):
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:60]:
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem


def fm_field(path, field):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    m = re.search(rf"^{field}:\s*(.+)$", text.split("---")[1] if text.count("---") >= 2 else "", re.M)
    return m.group(1).strip().strip("'\"") if m else ""


def py_info(path):
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        lines = src.count("\n") + 1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            doc = ast.get_docstring(ast.parse(src)) or ""
        return lines, doc.strip().splitlines()[0] if doc.strip() else ""
    except (SyntaxError, ValueError, OSError):
        return 0, ""


def head(title, repo_url, commit, note):
    stamp = dt.date.today().isoformat()
    return (f"---\ntype: code-map\nstatus: verified\nauthor: scripts/code_map.py\nsource_type: repo\n"
            f"created: {stamp}\ncssclasses:\n  - note-codemap\n---\n# {title}\n\n"
            f"> [!info] Generated page\n> Built from commit `{commit[:7]}` on {stamp}. {note} Do not edit by hand; run `python scripts/code_map.py` again.\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", default="code-map")
    a = ap.parse_args()
    repo, out = Path(a.repo).resolve(), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = [f for f in git(repo, "ls-files").splitlines() if f]
    commit = git(repo, "rev-parse", "HEAD") or "unknown"
    remote = re.sub(r"\.git$", "", git(repo, "remote", "get-url", "origin"))
    blob = f"{remote}/blob/{commit}/" if remote.startswith("http") else ""

    def link(path, label=None):
        label = label or path
        return f"[{esc(label)}]({blob}{path.replace(' ', '%20')})" if blob else f"`{esc(label)}`"

    # overview
    stats = defaultdict(lambda: [0, 0, 0])
    for f in files:
        top = f.split("/")[0] if "/" in f else "(root files)"
        p = repo / f
        size = p.stat().st_size if p.exists() else 0
        stats[top][0] += 1
        stats[top][1] += size
        if f.endswith(".py"):
            stats[top][2] += py_info(p)[0]
    rows = sorted(stats.items(), key=lambda kv: -kv[1][0])
    t = head("Repository overview", remote, commit, f"{len(files)} tracked files.")
    t += "| Folder | Tracked files | Size (MB) | Python lines |\n|---|---:|---:|---:|\n"
    for k, (n, s, ln) in rows:
        t += f"| {esc(k)} | {n} | {s / 1_048_576:.1f} | {ln} |\n"
    t += f"\nTotal: {len(files)} files. Repository: {remote or 'local only'}.\n"
    (out / "overview.md").write_text(t, encoding="utf-8", newline="\n")

    # docs
    t = head("Documents", remote, commit, "Markdown files tracked in the code repository.")
    groups = defaultdict(list)
    for f in files:
        if f.lower().endswith(".md"):
            groups[f.split("/")[0] if "/" in f else "(root)"].append(f)
    for g in sorted(groups):
        t += f"## {g} ({len(groups[g])})\n\n"
        for f in sorted(groups[g]):
            t += f"- {link(f, first_heading(repo / f))} (`{f}`)\n"
        t += "\n"
    (out / "documents.md").write_text(t, encoding="utf-8", newline="\n")

    # agents, rules, skills
    t = head("Agents, rules and skills", remote, commit, "Definitions that Antigravity and OpenCode can discover.")
    for title, pred in (("Agent definitions", lambda f: f.startswith(".agents/agents/")),
                        ("Rules", lambda f: f.startswith(".agents/rules/")),
                        ("Skills", lambda f: f.startswith(".agents/skills/") and f.endswith("SKILL.md"))):
        sel = sorted(f for f in files if pred(f) and f.endswith(".md"))
        t += f"## {title} ({len(sel)})\n\n| File | Description |\n|---|---|\n"
        for f in sel:
            t += f"| {link(f)} | {esc(fm_field(repo / f, 'description'))} |\n"
        t += "\n"
    t += "## Top-level instruction files\n\n"
    for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "opencode.json", "mcp_config.json", ".kilorules"):
        p = repo / name
        if name in files and p.exists():
            t += f"- {link(name)}: {p.stat().st_size} bytes\n"
    (out / "agents-and-skills.md").write_text(t, encoding="utf-8", newline="\n")

    # scripts and tools
    t = head("Scripts and tools", remote, commit, "First docstring line of each Python file.")
    for folder in ("tools", "scripts", "mcp", "engine"):
        sel = sorted(f for f in files if f.startswith(folder + "/") and f.endswith(".py"))
        if not sel:
            continue
        t += f"## {folder}/ ({len(sel)} files)\n\n| File | Lines | Docstring |\n|---|---:|---|\n"
        for f in sel:
            ln, doc = py_info(repo / f)
            t += f"| {link(f)} | {ln} | {esc(doc)[:140]} |\n"
        t += "\n"
    (out / "scripts-and-tools.md").write_text(t, encoding="utf-8", newline="\n")

    # package modules
    pkgs = sorted({f.split("/")[0] for f in files if f.endswith("/__init__.py") and f.count("/") == 1})
    t = head("Python packages", remote, commit, "One row per sub-package.")
    for pkg in pkgs:
        sub = defaultdict(lambda: [0, 0])
        for f in files:
            if f.startswith(pkg + "/") and f.endswith(".py"):
                parts = f.split("/")
                key = parts[1] if len(parts) > 2 else "(top level)"
                sub[key][0] += 1
                sub[key][1] += py_info(repo / f)[0]
        t += f"## {pkg}\n\n| Sub-package | Files | Lines |\n|---|---:|---:|\n"
        for k, (n, ln) in sorted(sub.items(), key=lambda kv: -kv[1][1]):
            t += f"| {esc(k)} | {n} | {ln} |\n"
        t += "\n"
    (out / "packages.md").write_text(t, encoding="utf-8", newline="\n")

    # index
    t = head("Code map", remote, commit, "Entry page.")
    t += ("- [[overview]]: folders, sizes, line counts\n- [[documents]]: every Markdown document with a link\n"
          "- [[agents-and-skills]]: agent definitions, rules and skills\n- [[scripts-and-tools]]: scripts with their docstrings\n"
          "- [[packages]]: Python packages by sub-package\n\n"
          "Files that Obsidian cannot open (Python, JSON, QGIS projects) are listed here with a link to the repository; "
          "open them in your code editor.\n")
    (out / "README.md").write_text(t, encoding="utf-8", newline="\n")
    print(f"wrote 6 pages to {out} from {len(files)} tracked files at {commit[:7]}")


if __name__ == "__main__":
    main()
