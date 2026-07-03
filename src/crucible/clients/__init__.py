"""Model clients: local (vLLM/ROCm), cloud (Fireworks), and a mock for offline runs."""
from __future__ import annotations

from ..config import Config
from .base import LLMClient, LLMResponse, MockClient
from .local_llm import LocalLLMClient
from .fireworks import FireworksClient


def build_clients(cfg: Config) -> dict[str, LLMClient]:
    """Return {"local": ..., "cloud": ...}. In mock mode both are stubs.

    The cloud lane provider is chosen by cfg.provider: 'anthropic' (Claude Fable 5),
    'fireworks' (default), or 'local' (route everything to the MI300X model).
    """
    if cfg.mode == "mock":
        return {"local": MockClient("local"), "cloud": MockClient("cloud")}
    local = LocalLLMClient(cfg.local_base_url, cfg.local_model)
    if cfg.provider == "anthropic":
        from .anthropic_client import AnthropicClient
        cloud = AnthropicClient(cfg.anthropic_model)
    elif cfg.provider == "local":
        cloud = local
    else:
        cloud = FireworksClient(cfg.fireworks_base_url, cfg.fireworks_api_key, cfg.fireworks_model)
    return {"local": local, "cloud": cloud}


__all__ = ["LLMClient", "LLMResponse", "MockClient", "LocalLLMClient", "FireworksClient", "build_clients"]
