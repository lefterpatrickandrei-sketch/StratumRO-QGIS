# AGENTS.md

This repository is a small Python workspace centered on lightweight MCP tooling and local experiments.

## What matters here
- The main implementation lives in [mcp/filesystem/server.py](mcp/filesystem/server.py). It exposes simple tools with FastMCP.
- File operations are intentionally restricted to [workspace/](workspace/). Keep any new filesystem behavior inside that boundary unless the task explicitly requires otherwise.
- The repository currently has no formal test suite. When changing Python behavior, run a small smoke test or direct module execution and report the result.

## Guidance for API-provider work
- If you add or modify an API-provider integration, keep provider-specific logic isolated and explicit.
- Prefer environment variables or simple config values for endpoints, API keys, and model names; do not hardcode secrets.
- Keep the integration surface narrow and reusable so additional providers can be added later without rewriting the calling code.
- Avoid broadening filesystem access, introducing unrelated dependencies, or making network calls outside the task scope.
- Prefer small, typed functions with clear docstrings over large abstractions.

## Working conventions
- Use Python and the local virtual environment in [venv/](venv/) when available.
- Follow the existing simple style: short functions, clear return values, and minimal scaffolding.
- If the task involves MCP, update [mcp/filesystem/server.py](mcp/filesystem/server.py) or the server config in [.aider.mcp.json](.aider.mcp.json) instead of creating unrelated boilerplate.
