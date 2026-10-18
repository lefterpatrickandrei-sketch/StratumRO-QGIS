# -*- coding: utf-8 -*-
"""
Antigravity Multi-Provider Agent Runner.
Allows running Antigravity SDK agents against alternative API backends:
  - OpenRouter (Union Alpha, Claude 3.5, Llama 3.3, DeepSeek)
  - NVIDIA NIM (Llama 3.3, Llama 3.2 Vision)
  - Custom Gemini API Key (Bypassing default Antigravity IDE rate limits)
  - Local Ollama (100% offline, zero rate limits)

Usage:
  python scripts/run_agent_with_custom_api.py --provider openrouter --prompt "Explain the cadastral workflow"
  python scripts/run_agent_with_custom_api.py --provider nvidia --prompt "Audit these boundary coordinates"
  python scripts/run_agent_with_custom_api.py --provider gemini --api-key "AIza..." --prompt "Hello"
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Load project root and .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def load_env():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

def get_agent_config(provider: str, model: str = None, api_key: str = None):
    try:
        from google.antigravity import (
            LocalOpenAIAgentConfig,
            LocalAgentConfig,
            CapabilitiesConfig,
        )
    except ImportError:
        print("[ERROR] google-antigravity is not installed. Run: pip install google-antigravity")
        sys.exit(1)

    caps = CapabilitiesConfig(
        file_reads=True,
        file_writes=True,
        command_execution=True,
        subagents=True,
        mcp=True,
    )

    if provider.lower() == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("UNION_ALPHA_API_KEY")
        if not key:
            print("[ERROR] No OpenRouter API key found in .env or arguments.")
            sys.exit(1)
        # Set OPENAI_API_KEY for standard OpenAI client harness
        os.environ["OPENAI_API_KEY"] = key
        model_name = model or "stealth/union-alpha"
        print(f"[+] Configuring Antigravity Agent with OpenRouter: {model_name}")
        return LocalOpenAIAgentConfig(
            base_url="https://openrouter.ai/api/v1",
            model=model_name,
            system_instructions="You are an expert geodetic and cadastral AI assistant.",
            capabilities=caps,
            workspaces=[str(PROJECT_ROOT)],
        )

    elif provider.lower() == "nvidia":
        key = api_key or os.getenv("NVIDIA_API_KEY")
        if not key:
            print("[ERROR] No NVIDIA_API_KEY found in .env or arguments.")
            sys.exit(1)
        os.environ["OPENAI_API_KEY"] = key
        model_name = model or "meta/llama-3.3-70b-instruct"
        print(f"[+] Configuring Antigravity Agent with NVIDIA NIM: {model_name}")
        return LocalOpenAIAgentConfig(
            base_url="https://integrate.api.nvidia.com/v1",
            model=model_name,
            system_instructions="You are an expert geodetic and cadastral AI assistant.",
            capabilities=caps,
            workspaces=[str(PROJECT_ROOT)],
        )

    elif provider.lower() == "ollama":
        model_name = model or "llama3.2"
        print(f"[+] Configuring Antigravity Agent with local Ollama: {model_name}")
        return LocalOpenAIAgentConfig(
            base_url="http://localhost:11434/v1",
            model=model_name,
            system_instructions="You are an expert geodetic and cadastral AI assistant.",
            capabilities=caps,
            workspaces=[str(PROJECT_ROOT)],
        )

    elif provider.lower() == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            print("[ERROR] No OPENAI_API_KEY found in .env or arguments.")
            sys.exit(1)
        os.environ["OPENAI_API_KEY"] = key
        model_name = model or "gpt-4o"
        print(f"[+] Configuring Antigravity Agent with OpenAI: {model_name}")
        return LocalOpenAIAgentConfig(
            base_url="https://api.openai.com/v1",
            model=model_name,
            system_instructions="You are an expert geodetic and cadastral AI assistant.",
            capabilities=caps,
            workspaces=[str(PROJECT_ROOT)],
        )

    elif provider.lower() == "sambanova":
        key = api_key or os.getenv("SAMBANOVA_API_KEY")
        if not key:
            print("[ERROR] No SAMBANOVA_API_KEY found in .env or arguments.")
            sys.exit(1)
        os.environ["OPENAI_API_KEY"] = key
        model_name = model or "Meta-Llama-3.3-70B-Instruct"
        print(f"[+] Configuring Antigravity Agent with SambaNova: {model_name}")
        return LocalOpenAIAgentConfig(
            base_url="https://api.sambanova.ai/v1",
            model=model_name,
            system_instructions="You are an expert geodetic and cadastral AI assistant.",
            capabilities=caps,
            workspaces=[str(PROJECT_ROOT)],
        )

    elif provider.lower() == "cerebras":
        key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not key:
            print("[ERROR] No CEREBRAS_API_KEY found in .env or arguments.")
            sys.exit(1)
        os.environ["OPENAI_API_KEY"] = key
        model_name = model or "gpt-oss-120b"
        print(f"[+] Configuring Antigravity Agent with Cerebras: {model_name}")
        return LocalOpenAIAgentConfig(
            base_url="https://api.cerebras.ai/v1",
            model=model_name,
            system_instructions="You are an expert geodetic and cadastral AI assistant.",
            capabilities=caps,
            workspaces=[str(PROJECT_ROOT)],
        )

    elif provider.lower() == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY")
        model_name = model or "gemini-3.8-flash"
        print(f"[+] Configuring Antigravity Agent with Custom Gemini Key: {model_name}")
        return LocalAgentConfig(
            model=model_name,
            api_key=key,
            system_instructions="You are an expert geodetic and cadastral AI assistant.",
            capabilities=caps,
            workspaces=[str(PROJECT_ROOT)],
        )

    else:
        raise ValueError(f"Unknown provider: {provider}. Options: openrouter, nvidia, openai, sambanova, cerebras, ollama, gemini")

def main():
    parser = argparse.ArgumentParser(description="Antigravity Custom Provider Agent Runner")
    parser.add_argument("--provider", choices=["openrouter", "nvidia", "openai", "sambanova", "cerebras", "ollama", "gemini"], default="openrouter",
                        help="Alternative backend to avoid Gemini 3.8 rate limits")
    parser.add_argument("--model", type=str, default=None, help="Target model name")
    parser.add_argument("--api-key", type=str, default=None, help="Explicit API key override")
    parser.add_argument("--check-only", action="store_true", help="Only verify configuration and exit")
    args = parser.parse_args()

    config = get_agent_config(args.provider, args.model, args.api_key)
    print(f"[OK] Configuration built successfully for {args.provider}: {type(config).__name__}")

if __name__ == "__main__":
    main()
