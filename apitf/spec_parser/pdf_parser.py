"""PDF spec parser — extracts EndpointSpec objects from PDF documents."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

from apitf.spec_parser.base_parser import BaseSpecParser, EndpointSpec, _resource_from_path

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https://[^\s]+")

# Pattern A: "METHOD https://full-url" — one full URL per endpoint in the PDF
_METHOD_FULL_URL = re.compile(
    r"\b(GET|POST|PUT|DELETE|PATCH)\s+(https://[^\s]+)"
)
# Pattern B: "METHOD /relative-path" — base URL declared separately at top of doc
_METHOD_REL_PATH = re.compile(
    r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]*)"
)
# Fallback: bare METHOD keyword with no path token following
_METHOD_ONLY = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\b")

# Matches "Fields: id, name, status" or "Response fields: id, name"
_FIELDS_PATTERN = re.compile(
    r"(?:response\s+)?fields?\s*:\s*([^\n]+)", re.IGNORECASE
)
# Matches "env_label https://..." lines — used to build an explicit env→base_url map
_ENV_URL_LINE_PATTERN = re.compile(r"^(\w[\w\-]*)\s+(https://[^\s]+)", re.MULTILINE)

_HOSTNAME_ENV_MAP: dict[str, str] = {
    "restcountries": "countries",
    "open-meteo": "weather",
    "petstore3": "petstore3",
    "swagger": "petstore3",
}
_UNRESOLVED_THRESHOLDS: dict = {}


class PDFParser(BaseSpecParser):
    supported_extensions: tuple[str, ...] = (".pdf", ".PDF")

    def parse(self, source: Path) -> list[EndpointSpec]:
        specs: list[EndpointSpec] = []
        try:
            with pdfplumber.open(source) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
        except Exception as exc:
            logger.error("Failed to open PDF %s: %s", source, exc)
            return specs

        full_text = "\n".join(pages)
        url_positions: list[tuple[int, str]] = [
            (m.start(), m.group(0)) for m in _URL_PATTERN.finditer(full_text)
        ]
        fields_positions: list[tuple[int, list[str]]] = [
            (m.start(), [f.strip() for f in m.group(1).split(",") if f.strip()])
            for m in _FIELDS_PATTERN.finditer(full_text)
        ]
        env_url_map: dict[str, str] = {
            m.group(1): self._base_only(m.group(2))
            for m in _ENV_URL_LINE_PATTERN.finditer(full_text)
        }
        if env_url_map:
            logger.debug("Detected env→URL map: %s", env_url_map)

        hits = self._collect_hits(full_text, url_positions)

        for pos, method, base_url, path in hits:
            try:
                hostname = re.sub(r"https://", "", base_url).split("/")[0]
                sld = hostname.split(".")[0].lower()
                env_name = _HOSTNAME_ENV_MAP.get(sld, sld)
                response_fields = self._nearest_fields(fields_positions, pos)
                specs.append(
                    EndpointSpec(
                        env_name=env_name,
                        base_url=base_url,
                        path=path,
                        method=method,
                        response_fields=response_fields,
                        thresholds=_UNRESOLVED_THRESHOLDS,
                        resource_name=_resource_from_path(path),
                    )
                )
            except (IndexError, ValueError) as exc:
                logger.warning("Failed to build EndpointSpec from URL %r: %s", base_url, exc)

        logger.info("PDFParser extracted %d specs from %s", len(specs), source)
        return specs

    @classmethod
    def _collect_hits(
        cls,
        full_text: str,
        url_positions: list[tuple[int, str]],
    ) -> list[tuple[int, str, str, str]]:
        """Return (pos, method, base_url, path) for every endpoint found.

        Three patterns handled in priority order:
        A) "METHOD https://host/path" — full URL per endpoint; split into base+path.
        B) "METHOD /relative-path"    — base URL declared separately; nearest URL = base.
        C) bare METHOD keyword        — last resort; extract path from nearest full URL.
        """
        results: list[tuple[int, str, str, str]] = []
        covered: set[int] = set()

        # Pattern A: METHOD https://full-url
        for hit in _METHOD_FULL_URL.finditer(full_text):
            pos = hit.start()
            method = hit.group(1)
            full_url = hit.group(2)
            base_url = cls._base_only(full_url)
            path = cls._path_from_url(full_url)
            results.append((pos, method, base_url, path))
            covered.add(pos)

        # Pattern B: METHOD /relative-path
        for hit in _METHOD_REL_PATH.finditer(full_text):
            pos = hit.start()
            if pos in covered:
                continue
            method = hit.group(1)
            raw_path = hit.group(2)
            nearest = cls._nearest_url(url_positions, pos)
            if nearest is None:
                logger.warning("No URL found near %s %s at pos %d", method, raw_path, pos)
                continue
            results.append((pos, method, cls._base_only(nearest), raw_path))
            covered.add(pos)

        # Pattern C: bare METHOD fallback
        for hit in _METHOD_ONLY.finditer(full_text):
            pos = hit.start()
            if pos in covered:
                continue
            method = hit.group(0)
            nearest = cls._nearest_url(url_positions, pos)
            if nearest is None:
                logger.warning("No URL found near method %r at pos %d", method, pos)
                continue
            base_url = cls._base_only(nearest)
            path = cls._path_from_url(nearest)
            results.append((pos, method, base_url, path))

        results.sort(key=lambda x: x[0])
        return results

    @staticmethod
    def _base_only(url: str) -> str:
        """Return scheme + host from a full URL, stripping path."""
        parts = url.split("/")
        return "/".join(parts[:3])

    @staticmethod
    def _path_from_url(url: str) -> str:
        """Return the path portion of a URL, or '/' if none."""
        parts = url.split("/")
        if len(parts) > 3 and parts[3]:
            return "/" + "/".join(parts[3:])
        return "/"

    @staticmethod
    def _nearest_url(
        url_positions: list[tuple[int, str]], target: int
    ) -> str | None:
        preceding = [(pos, url) for pos, url in url_positions if pos <= target]
        if not preceding:
            return None
        return max(preceding, key=lambda x: x[0])[1]

    @staticmethod
    def _nearest_fields(
        fields_positions: list[tuple[int, list[str]]], target: int, window: int = 400
    ) -> list[str]:
        """Return fields declared within *window* chars after *target* (the method hit)."""
        following = [
            (pos, fields)
            for pos, fields in fields_positions
            if target < pos <= target + window
        ]
        if not following:
            return []
        return min(following, key=lambda x: x[0])[1]
