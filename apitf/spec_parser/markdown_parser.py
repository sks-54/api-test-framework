"""Markdown spec parser — extracts EndpointSpec objects from Markdown documents.

Expected document format
------------------------
A ``Base URL:`` line declares the API root::

    Base URL: https://api.example.com/v1

Endpoints are listed in a pipe-delimited table whose header row contains the
words "method", "path", and "field" (case-insensitive, substring match)::

    | Method | Path          | Response Fields          |
    |--------|---------------|--------------------------|
    | GET    | /posts/{id}   | id, userId, title, body  |

Columns may appear in any order. Additional columns are ignored.
Tables with no matching headers are skipped.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from apitf.spec_parser.base_parser import BaseSpecParser, EndpointSpec, _resource_from_path

logger = logging.getLogger(__name__)

# Rule 1 — URL atomicity: capture full URL with group(0), never reassemble.
_URL_PATTERN = re.compile(r"https://[^\s]+")

_VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
_UNRESOLVED_THRESHOLDS: dict = {}

_HOSTNAME_ENV_MAP: dict[str, str] = {
    "restcountries": "countries",
    "open-meteo": "weather",
    "jsonplaceholder": "jsonplaceholder",
}


def _env_from_url(base_url: str) -> str:
    """Infer env_name from the second-level domain of base_url (Rule 5)."""
    hostname = _URL_PATTERN.search(base_url)
    if not hostname:
        return "unknown"
    host = hostname.group(0).replace("https://", "").split("/")[0]
    sld = host.split(".")[0].lower()
    return _HOSTNAME_ENV_MAP.get(sld, sld)


def _split_table_row(line: str) -> list[str]:
    """Split a markdown table row on ``|`` and strip whitespace."""
    return [cell.strip() for cell in line.split("|") if cell.strip()]


def _is_separator(line: str) -> bool:
    """True if the line is a table separator row (``|---|---|``)."""
    return bool(re.match(r"^\|[\s\-\|]+\|$", line.strip()))


class MarkdownParser(BaseSpecParser):
    """Parse API specs from Markdown documents."""

    supported_extensions: tuple[str, ...] = (".md", ".markdown")

    def parse(self, source: Path) -> list[EndpointSpec]:
        try:
            # Rule 2: split on whitespace boundaries, never fixed-width byte offsets.
            raw = source.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Cannot read %s: %s", source, exc)
            return []

        # Rule 3: preserve page joins with newline (single file → already newlines).
        lines = raw.split("\n")

        base_url = self._find_base_url(raw)
        if not base_url:
            logger.warning("No 'Base URL: https://...' line found in %s", source)
            return []

        env_name = _env_from_url(base_url)
        specs: list[EndpointSpec] = []

        i = 0
        while i < len(lines):
            # Look for a table header row containing "method" and "path".
            if "|" in lines[i]:
                headers = [h.lower() for h in _split_table_row(lines[i])]
                if any("method" in h for h in headers) and any("path" in h for h in headers):
                    try:
                        method_col = next(j for j, h in enumerate(headers) if "method" in h)
                        path_col = next(j for j, h in enumerate(headers) if "path" in h)
                        field_col = next(
                            (j for j, h in enumerate(headers) if "field" in h), None
                        )
                    except StopIteration:
                        i += 1
                        continue

                    i += 1
                    # Skip separator row.
                    if i < len(lines) and _is_separator(lines[i]):
                        i += 1

                    while i < len(lines) and "|" in lines[i] and not _is_separator(lines[i]):
                        cells = _split_table_row(lines[i])
                        if len(cells) > max(method_col, path_col):
                            method = cells[method_col].upper()
                            path = cells[path_col]
                            fields: list[str] = []
                            if field_col is not None and len(cells) > field_col:
                                fields = [
                                    f.strip()
                                    for f in cells[field_col].split(",")
                                    if f.strip()
                                ]
                            if method in _VALID_METHODS and path.startswith("/"):
                                specs.append(
                                    EndpointSpec(
                                        env_name=env_name,
                                        base_url=base_url,
                                        path=path,
                                        method=method,
                                        response_fields=fields,
                                        thresholds=_UNRESOLVED_THRESHOLDS,
                                        resource_name=_resource_from_path(path),
                                    )
                                )
                            else:
                                logger.warning(
                                    "Skipping row with method=%r path=%r in %s",
                                    method, path, source,
                                )
                        i += 1
                    continue
            i += 1

        logger.info("MarkdownParser extracted %d specs from %s", len(specs), source)
        return specs

    @staticmethod
    def _find_base_url(text: str) -> str | None:
        """Find 'Base URL: https://...' line. Captures full URL atomically (Rule 1)."""
        for line in text.split("\n"):
            if re.search(r"base\s+url", line, re.IGNORECASE):
                match = _URL_PATTERN.search(line)
                if match:
                    return match.group(0).rstrip("/")
        return None
