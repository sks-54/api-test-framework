from __future__ import annotations

import os
from pathlib import Path

from apitf.providers.base import LLMProvider, ProviderModels

_GEN_PREFERENCES = [
    "claude-sonnet-4-6",
    "claude-3-5-sonnet-20241022",
    "claude-haiku-4-5-20251001",
    "claude-haiku-3-5",
]
_REF_PREFERENCES = [
    "claude-opus-4-7",
    "claude-opus-4-5",
    "claude-sonnet-4-6",
    "claude-3-5-sonnet-20241022",
]

_MAX_TOKENS = 8192


def _load_dotenv() -> str | None:
    root = Path(__file__).parent.parent.parent
    dotenv = root / ".env"
    if not dotenv.exists():
        return None
    try:
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == "ANTHROPIC_API_KEY":
                return val.strip().strip('"').strip("'") or None
    except OSError:
        pass
    return None


def _resolve_key(explicit_key: str | None) -> str | None:
    return explicit_key or os.environ.get("ANTHROPIC_API_KEY") or _load_dotenv()


def _best_model(client: object, preferences: list[str]) -> str:
    """Return the best available model by intersecting preferences with the API's model list."""
    try:
        available = {m.id for m in client.models.list().data}  # type: ignore[attr-defined]
        for pref in preferences:
            if pref in available:
                return pref
    except Exception:
        pass
    return preferences[0]  # assume the top preference is available; API will error if not


class AnthropicProvider(LLMProvider):
    """Anthropic SDK provider — uses ANTHROPIC_API_KEY or explicit --api-key."""

    def __init__(self, explicit_key: str | None = None) -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=_resolve_key(explicit_key))
        gen = _best_model(self._client, _GEN_PREFERENCES)
        ref = _best_model(self._client, _REF_PREFERENCES)
        self._models = ProviderModels(
            generation=gen,
            reflection=ref,
            label=f"Anthropic SDK ({gen} / {ref})",
        )

    @classmethod
    def available(cls, explicit_key: str | None = None) -> bool:
        if not _resolve_key(explicit_key):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def models(self) -> ProviderModels:
        return self._models

    def generate(self, prompt: str, model: str) -> str:
        message = self._client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
