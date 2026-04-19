"""OpenAPI/Swagger spec parser stub — see ENHANCEMENTS.md E-01."""

from __future__ import annotations

from pathlib import Path

from src.spec_parser.base_parser import BaseSpecParser, EndpointSpec


class OpenAPIParser(BaseSpecParser):
    """Parse OpenAPI 3.x / Swagger 2.x YAML or JSON specs.

    Not yet implemented — see ENHANCEMENTS.md E-01.
    Extend this class to enable zero-framework-change OpenAPI support.
    """

    supported_extensions: tuple[str, ...] = (".yaml", ".yml", ".json")

    def parse(self, source: Path) -> list[EndpointSpec]:
        raise NotImplementedError(
            "OpenAPIParser is a stub — implement E-01 from ENHANCEMENTS.md"
        )
