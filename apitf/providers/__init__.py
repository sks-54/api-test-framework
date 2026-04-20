from __future__ import annotations

from apitf.providers.base import LLMProvider, ProviderModels
from apitf.providers.claude_cli import ClaudeCLIProvider
from apitf.providers.anthropic import AnthropicProvider

_PROVIDER_CLASSES = [
    ClaudeCLIProvider,  # 1. Claude Code session — zero config
    AnthropicProvider,  # 2. Anthropic SDK — ANTHROPIC_API_KEY
]

_NO_AI_MESSAGE = """\
[apitf-run] AI provider : none

  No Claude provider detected. To enable full test generation + reflector review:

    pip install "apitf[ai]"
    export ANTHROPIC_API_KEY=sk-ant-...

  Or run inside a Claude Code session (zero config — uses your account automatically).

  Continuing with 5-test baseline stub (no AI required).
"""


def discover_provider(explicit_key: str | None = None) -> LLMProvider | None:
    """Return the first available Claude provider, or None.

    Priority:
      1. Claude Code CLI (CLAUDECODE=1 + claude in PATH) — auto-detects best model
      2. Anthropic SDK (ANTHROPIC_API_KEY) — auto-detects best model on the account
    Model preference within each: Sonnet for generation, Opus for reflection.
    Falls back to lesser models if preferred ones aren't on the user's plan.
    """
    for cls in _PROVIDER_CLASSES:
        try:
            if cls.available(explicit_key=explicit_key):
                return cls(explicit_key=explicit_key)
        except Exception:
            continue
    return None


__all__ = [
    "LLMProvider",
    "ProviderModels",
    "ClaudeCLIProvider",
    "AnthropicProvider",
    "discover_provider",
    "_NO_AI_MESSAGE",
]
