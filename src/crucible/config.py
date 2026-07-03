"""Runtime configuration, loaded from environment / .env.

Everything defaults to offline `mock` mode so the pipeline runs with no GPU,
no API keys, and no network.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv is optional; env vars still work without it
    pass


@dataclass(frozen=True)
class Config:
    mode: str                      # "mock" | "live"
    local_base_url: str
    local_model: str
    fireworks_api_key: str
    fireworks_base_url: str
    fireworks_model: str
    escalate_threshold: float
    provider: str            # cloud lane: fireworks | anthropic | local
    anthropic_model: str


def load_config() -> Config:
    return Config(
        mode=os.getenv("CRUCIBLE_MODE", "mock").strip().lower(),
        local_base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8000/v1"),
        local_model=os.getenv("LOCAL_LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
        fireworks_api_key=os.getenv("FIREWORKS_API_KEY", ""),
        fireworks_base_url=os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"),
        fireworks_model=os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-70b-instruct"),
        escalate_threshold=float(os.getenv("ROUTER_ESCALATE_THRESHOLD", "0.7")),
        provider=os.getenv("CRUCIBLE_LLM_PROVIDER", "fireworks").strip().lower(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-fable-5"),
    )
