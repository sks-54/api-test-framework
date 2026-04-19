"""Base classes, dataclasses, and registry for the spec-parser layer."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EndpointSpec:
    """Normalised representation of a single API endpoint extracted from a spec document."""

    env_name: str
    base_url: str
    path: str
    method: str
    response_fields: list[str]
    thresholds: dict
    description: str = ""


class BaseSpecParser(abc.ABC):
    """Abstract base class for all spec-file parsers.

    Subclasses must declare the file extensions they handle via the class
    attribute ``supported_extensions`` and implement the ``parse`` method.
    """

    supported_extensions: tuple[str, ...] = ()

    @abc.abstractmethod
    def parse(self, source: Path) -> list[EndpointSpec]:
        """Parse *source* and return a list of :class:`EndpointSpec` objects."""

    def can_parse(self, source: Path) -> bool:
        """Return ``True`` when this parser supports the file at *source*."""
        return source.suffix in self.supported_extensions


class SpecParserRegistry:
    """Registry that maps file extensions to :class:`BaseSpecParser` instances."""

    def __init__(self) -> None:
        self._parsers: list[BaseSpecParser] = []

    def register(self, parser: BaseSpecParser) -> None:
        if not isinstance(parser, BaseSpecParser):
            raise TypeError(f"Expected a BaseSpecParser instance, got {type(parser).__name__!r}.")
        self._parsers.append(parser)

    def get_parser(self, source: Path) -> BaseSpecParser:
        for parser in self._parsers:
            if parser.can_parse(source):
                return parser
        supported = sorted({ext for p in self._parsers for ext in p.supported_extensions})
        raise ValueError(
            f"No parser registered for extension {source.suffix!r}. "
            f"Registered extensions: {supported}."
        )

    def parse(self, source: Path) -> list[EndpointSpec]:
        return self.get_parser(source).parse(source)
