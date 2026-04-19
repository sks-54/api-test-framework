"""Markdown API-doc parser — STUB, planned for v1.1.

Full implementation planned for v1.1. Will parse markdown API docs.
See ENHANCEMENTS.md E-02.
"""

from __future__ import annotations

from pathlib import Path

from .base_parser import BaseSpecParser, EndpointSpec


class MarkdownParser(BaseSpecParser):
    """Parse markdown API documentation files.

    Full implementation planned for v1.1 — see ENHANCEMENTS.md E-02.

    Planned implementation outline (two-phase approach):

    Phase 1 — section discovery:
        Split document into sections using ATX heading regex:
            _SECTION_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)

    Phase 2 — block extraction per section:
        - HTTP method + path: _METHOD_PATH_PATTERN = re.compile(
              r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s`]*)")
        - Base URL (atomic): _URL_PATTERN = re.compile(r"https://[^\s`]+")
          URLs are never split across lines — captured as atomic tokens.
        - Response field table: GFM table first-column field names.
        - Fenced code blocks: JSON examples parsed with json.loads
          for response_fields when no explicit table exists.

    Assembly: one EndpointSpec per unique (base_url, method, path) triple.
    env_name inferred from base URL hostname.
    """

    supported_extensions: tuple[str, ...] = (".md", ".markdown")

    def parse(self, source: Path) -> list[EndpointSpec]:
        # TODO (E-02): implement full markdown parsing.
        #
        # Skeleton for v1.1 implementer (do NOT remove):
        #
        #   text = source.read_text(encoding="utf-8")
        #   sections = _split_into_sections(text)   # uses _SECTION_PATTERN
        #
        #   specs = []
        #   for heading, body in sections:
        #       urls    = _URL_PATTERN.findall(body)   # atomic URL tokens
        #       methods = _METHOD_PATH_PATTERN.findall(body)
        #       fields  = _extract_fields_from_table(body)
        #       if not fields:
        #           fields = _extract_fields_from_code_block(body)
        #       for base_url in urls:
        #           base_url = _extract_base_url(base_url)
        #           for method, path in methods:
        #               specs.append(EndpointSpec(...))
        #   return specs

        raise NotImplementedError(
            "MarkdownParser is not yet implemented. "
            "See ENHANCEMENTS.md E-02 for the full implementation plan."
        )
