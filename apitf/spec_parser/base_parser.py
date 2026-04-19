"""Abstract base for spec parsers and the EndpointSpec dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EndpointSpec:
    env_name: str
    base_url: str
    path: str
    method: str
    response_fields: list[str]
    thresholds: dict = field(default_factory=dict)
    description: str = ""


class BaseSpecParser(ABC):
    supported_extensions: tuple[str, ...] = ()

    def can_parse(self, source: Path) -> bool:
        return source.suffix in self.supported_extensions

    @abstractmethod
    def parse(self, source: Path) -> list[EndpointSpec]: ...


class SpecParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[BaseSpecParser] = []

    def register(self, parser: BaseSpecParser) -> None:
        self._parsers.append(parser)

    def get_parser(self, source: Path) -> BaseSpecParser | None:
        for p in self._parsers:
            if p.can_parse(source):
                return p
        return None

    def parse(self, source: Path) -> list[EndpointSpec]:
        parser = self.get_parser(source)
        if parser is None:
            raise ValueError(
                f"No registered parser supports {source.suffix!r}. "
                f"Registered: {[type(p).__name__ for p in self._parsers]}"
            )
        return parser.parse(source)
