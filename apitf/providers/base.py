from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderModels:
    generation: str   # fast Sonnet-tier model
    reflection: str   # powerful Opus-tier model
    label: str        # shown in [apitf-run] banner


class LLMProvider(ABC):
    """Abstract base for all LLM provider adapters."""

    @classmethod
    @abstractmethod
    def available(cls, explicit_key: str | None = None) -> bool:
        """Return True if this provider can be used right now."""

    @abstractmethod
    def generate(self, prompt: str, model: str) -> str:
        """Send prompt to model and return the raw text response."""

    @property
    @abstractmethod
    def models(self) -> ProviderModels:
        """The generation + reflection model pair for this provider."""
