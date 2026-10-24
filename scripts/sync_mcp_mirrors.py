"""Keep MCP client configs in sync with the root ``mcp_config.json``.

The root ``mcp_config.json`` is the single source of truth. Mirrors:

* ``.agents/mcp_config.json``  Antigravity workspace config (tracked in git)
* ``.mcp.json``                Claude Code project config (git-ignored, generated locally)
* ``.vscode/mcp.json``         Copilot / VS Code config (git-ignored, generated locally)

Usage:
    python scripts/sync_mcp_mirrors.py --check   # exit 1 if a present mirror differs
    python scripts/sync_mcp_mirrors.py --sync    # write all mirrors from the root file

``.vscode/mcp.json`` uses the key ``servers`` instead of ``mcpServers``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT_CONFIG = REPO / "mcp_config.json"


def load_servers(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    key = "mcpServers" if "mcpServers" in data else "servers"
    return data[key]


def mirrors(repo: Path) -> dict[Path, str]:
    """Map mirror path -> top-level key used in that file."""
    return {
        repo / ".agents" / "mcp_config.json": "mcpServers",
        repo / ".mcp.json": "mcpServers",
        repo / ".vscode" / "mcp.json": "servers",
    }


def render(servers: dict, key: str) -> str:
    return json.dumps({key: servers}, indent=2, ensure_ascii=False) + "\n"


def check(repo: Path = REPO, require_all: bool = False) -> list[str]:
    """Return a list of problems. A missing git-ignored mirror is not a problem unless required."""
    root_servers = load_servers(repo / "mcp_config.json")
    problems: list[str] = []
    for path, _key in mirrors(repo).items():
        if not path.exists():
            if require_all or path.parent.name == ".agents":
                problems.append(f"missing: {path.relative_to(repo)}")
            continue
        if load_servers(path) != root_servers:
            problems.append(f"differs from mcp_config.json: {path.relative_to(repo)}")
    return problems


def sync(repo: Path = REPO) -> list[Path]:
    root_servers = load_servers(repo / "mcp_config.json")
    written = []
    for path, key in mirrors(repo).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(root_servers, key), encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--sync", action="store_true")
    args = parser.parse_args(argv)
    if args.sync:
        for p in sync():
            print(f"wrote {p.relative_to(REPO)}")
        return 0
    problems = check()
    for p in problems:
        print(p)
    print("MCP mirrors OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
