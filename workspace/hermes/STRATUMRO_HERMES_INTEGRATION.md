# STRATUMRO HERMES INTEGRATION

**Date:** 2026-09-21
**Status:** PARTIAL — Phase A substantially completed; Bot profiles created; collaboration and live MCP tests remain.

## Objective

Use Hermes native capabilities for a persistent StratumRO-QGIS development team. Do not build a new SDK or IDE. Do not modify StratumRO product code during setup.

## Verified repository

- Root: `C:\Users\lefpa\Downloads\QGIS-AI`
- Branch: `main`
- HEAD: `c976864`
- Remote: `StratumRO-QGIS`
- Working tree: intentionally dirty with pre-existing tracked and untracked changes. No reset/clean/switch/delete operation was performed.
- Existing project context: `AGENTS.md`, `.agents/`, `workspace/architecture/`, `workspace/baseline/`, `mcp/`, and `mcp_config.json`.

## Hermes state

- Hermes: `0.21.3` / upstream `0469740a`
- Current global model: `gpt-5.6-terra` via `openai-codex`
- Current global fallback chain: empty
- Current gateway: stopped
- Initial warm backend policy: retain 3 maximum
- Ollama: excluded by project policy

## Profiles created

Six cloned Hermes profiles were created from `default`, without messaging channels:

- `stratumro-architect`
- `stratumro-coder`
- `stratumro-geospatial`
- `stratumro-qgis`
- `stratumro-reviewer`
- `stratumro-researcher`

Each profile now has:

- a role-specific `SOUL.md`;
- a `profile.yaml` with `ui_meta.hermes-bots` title/description;
- the cloned model configuration (`gpt-5.6-terra` / `openai-codex`);
- cloned provider credentials in its profile `.env`.

The credentials were not printed. Because cloning copies `.env` values into six profiles, rotate any credentials that were exposed in earlier chat material before production use.

## Role boundaries

- Architect: read/analyze/plan; no automatic code changes.
- Coder: approved patch/test/diff workflow.
- Geospatial: deterministic CRS/geometry/topology/measurement safety.
- QGIS: PyQGIS, Processing, runtime, and QGIS-MCP verification.
- Reviewer: independent read-only adversarial review.
- Researcher: current official-source verification; no repository changes.

## MCP

The repository declares five local MCP servers: `stratumro`, `filesystem`, `dataset_manager`, `context7`, and `qgis`. Hermes exposes a large catalog, but no local StratumRO MCP server was launched or live-tested yet. Do not enable every server for every bot; use the smallest useful surface by role.

## Provider/model evidence

Previous artifacts show:

- StratumRO direct NVIDIA NIM vision probe: one model passed; several other model IDs failed or timed out.
- OpenRouter llama probe: passed in prior live testing.
- Current Hermes error: OpenRouter free Nemotron upstream idle timeout.
- Anthropic/OpenAI direct API probes: credit-related failures in prior artifacts.

Therefore the OpenRouter free Nemotron model is not a safe default. The Hermes global Codex model remains the active working model in the current environment. The existing StratumRO provider matrix is historical/role-planning evidence and must not be treated as proof that every assigned route is currently healthy.

## BuilderIO / Agentic Native decision

The requested check was whether BuilderIO/Agentic Native fills a real Hermes capability gap. The inspected Agent-Native project is a framework for applications where UI and agents share actions, state, tools, skills, memory, jobs, MCP/A2A, and application surfaces. That is a product/application architecture, not a replacement for Hermes profiles and Bot Mode.

The current Hermes/StratumRO setup already covers the requested persistent specialist profiles, skills, MCP configuration, Git context, memory isolation, and role boundaries. No demonstrated missing capability currently requires implementing BuilderIO/Agentic Native inside Hermes or StratumRO.

Decision: **no BuilderIO/Agentic Native implementation now**. Revisit only if a concrete requirement appears that Hermes native profiles/skills/MCP/Git cannot satisfy. Any future integration should be a narrow adapter or MCP boundary, not a second SDK/IDE/agent runtime.

Evidence reviewed: BuilderIO/agent-native repository and Builder's agent-native architecture material. The repository describes shared UI/agent actions and SQL-backed state; Builder's architecture guidance describes making an app reachable through standard agent interfaces such as MCP.

## Not yet verified

- Hermes Desktop Bot Mode rendering of all six profiles.
- Bot-to-bot group collaboration.
- Live invocation of the repository MCP servers.
- GitHub MCP/authentication; Hermes status reports GitHub API key not configured.
- QGIS Desktop 3.40/PyQGIS/QGIS-MCP live bridge.
- Fresh role-specific model probes after the current OpenRouter timeout.
- The first Architect read-only bot test was attempted using the newly created profile and OpenRouter model. The model returned no repository audit because its browser tool could not start and it did not fall back to the available terminal/filesystem tools. This is a bot workflow failure, not evidence about the repository.

## Safety state

No StratumRO product source, ground truth, golden baseline, or scientific reference artifact was modified by this setup. The existing dirty worktree remains untouched.
