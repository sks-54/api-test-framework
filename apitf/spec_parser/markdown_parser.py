"""Markdown spec parser stub — see ENHANCEMENTS.md E-02."""

from __future__ import annotations

from pathlib import Path

from apitf.spec_parser.base_parser import BaseSpecParser, EndpointSpec


class MarkdownParser(BaseSpecParser):
    """Parse API specs from Markdown documents.

    Not yet implemented — see ENHANCEMENTS.md E-02.
    Extend this class to enable zero-framework-change Markdown spec support.
    """

    supported_extensions: tuple[str, ...] = (".md", ".markdown")

    def parse(self, source: Path) -> list[EndpointSpec]:
        raise NotImplementedError(
            "MarkdownParser is a stub — implement E-02 from ENHANCEMENTS.md"
        )
