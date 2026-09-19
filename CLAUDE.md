# StratumRO — AI Cadastral Engine & Model Architecture

## Available Model Providers
- **OpenRouter (Default)**: `OPENROUTER_API_KEY` loaded from `.env`
  - Recommended Primary Model: `anthropic/claude-3.5-sonnet`
  - Recommended Small/Fast Model: `deepseek/deepseek-chat`
- **NVIDIA NIM**: `NVIDIA_API_KEY` loaded from `.env`
  - Base URL: `https://integrate.api.nvidia.com/v1`
  - Recommended Models: `meta/llama-3.3-70b-instruct`, `nemotron-4-340b`, `meta-llama/llama-3.1-8b-instruct`

## Model Routing Rules
1. **Architecture, Complex Refactoring, Failure Autopsies:** Claude 3.5 Sonnet (`anthropic/claude-3.5-sonnet`) via OpenRouter.
2. **Small edits, Commit messages, Fast coding:** DeepSeek Chat (`deepseek/deepseek-chat`) or Llama 3.1 8B.
3. **Spatial Math & Cadastral Operations:** Strictly local Python (`venv\Scripts\python`). NEVER hallucinate Stereo 70 coordinates or PAD tables.

## Testing Standard
Always verify using the local virtual environment:
`venv\Scripts\python -m unittest discover stratum_ro/test`
