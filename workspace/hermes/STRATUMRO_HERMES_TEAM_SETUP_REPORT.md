# STRATUMRO HERMES TEAM SETUP REPORT

**Date:** September 21, 2026
**Overall:** PARTIAL — profiles and role configuration created; live collaboration/integration gates remain.

## SYSTEM

- Windows: Windows 11 x64 (configured environment)
- RAM policy: 16 GB machine; maximum 3 warm bot backends initially
- Repository: `C:\Users\lefpa\Downloads\QGIS-AI`

## HERMES

- Version: `0.21.3`
- Install: git installation at `C:\Users\lefpa\AppData\Local\hermes\hermes-agent`
- Active global model at audit time: `gpt-5.6-terra` via `openai-codex`
- Gateway: stopped
- Global fallback chain: none configured

## PROJECT / GIT

- Branch: `main`
- HEAD: `c976864`
- Remote: `StratumRO-QGIS`
- Working tree: dirty with pre-existing tracked and untracked work. No destructive Git command was run.
- Existing current-project map: present and reviewed.
- Current executable test evidence in previous audit: 250 discovered, 241 passed, 9 skipped, 0 failed, exit code 0. This is not re-run by this setup step.

## PROVIDERS / MODELS

- OpenAI Codex subscription: active for Hermes global reasoning.
- OpenRouter: configured; a prior llama probe passed, but the current free Nemotron route failed with upstream idle timeout.
- NVIDIA NIM: configured; prior StratumRO direct probe verified one vision model, while other model IDs failed or timed out.
- Anthropic/OpenAI direct API: prior artifacts report credit-related failures.
- Local deterministic provider: available in StratumRO artifacts as a fallback/planning path.
- Ollama: explicitly excluded; not installed, started, or selected.

No provider is marked universally healthy solely because a key exists. Model assignment must be refreshed after provider probes.

## BOTS / PROFILES

Created six cloned Hermes profiles:

1. `stratumro-architect` — architecture and planning
2. `stratumro-coder` — implementation and testing
3. `stratumro-geospatial` — geospatial/scientific safety
4. `stratumro-qgis` — QGIS/PyQGIS/Processing/MCP
5. `stratumro-reviewer` — read-only adversarial review
6. `stratumro-researcher` — official-source research

Each has a role-specific `SOUL.md` and Bot Mode metadata in `profile.yaml`. All currently inherit the cloned `gpt-5.6-terra` / `openai-codex` configuration. They have not yet been assigned different models because the current evidence does not justify six separate routes.

## SKILLS

Project-local skills found and preserved:

- `gsd-cadastre`
- `qgis-live`
- `huashu-design`

Existing Hermes skill matrix and project-local rules were retained. No broad “install everything” action was taken.

## MCP

Repository configuration declares:

- `stratumro`
- `filesystem`
- `dataset_manager`
- `context7`
- `qgis`

MCP catalog discovery succeeded. Live local server startup and tool calls are still pending. GitHub MCP/auth is not verified; Hermes status reports no GitHub API key configured.

## BUILDERIO / AGENTIC NATIVE

The requested check was whether BuilderIO/Agentic Native must be implemented to achieve the target. Current evidence shows no required gap: Hermes profiles, skills, MCP, Git context, and isolated role memories already provide the requested foundation.

**Decision: no implementation now.** Do not introduce a second SDK, IDE, or agent runtime without a concrete missing capability and a minimal integration design.

## SECURITY

- No secrets are included in this report.
- Profiles were cloned from `default`, so their `.env` files contain copied credentials. Keep them local and rotate credentials previously exposed in pasted chat material.
- No product source, ground truth, baseline, or scientific artifact was changed during setup.

## REMAINING ACCEPTANCE GATES

- [ ] Confirm Bot Mode displays all six profiles in Hermes Desktop.
- [ ] Start one Architect read-only test.
- [ ] Run Geospatial review of the Architect result.
- [ ] Run independent Reviewer review.
- [ ] Test Bot-to-Bot collaboration group.
- [ ] Live-test selected repository MCP servers.
- [ ] Verify QGIS runtime/MCP or mark unavailable.
- [ ] Refresh provider/model matrix after current OpenRouter timeout.
- [ ] Configure a fallback only after a live-verified model is selected.

## NEXT SAFE ACTION

Run the three read-only bot tests in order: Architect → Geospatial → Reviewer. Do not start Phase 4.4 or modify StratumRO until those reports are reviewed and explicitly approved.
