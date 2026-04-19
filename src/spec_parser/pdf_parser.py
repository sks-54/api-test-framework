"""PDF spec parser — extracts API endpoint definitions from PDF documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pdfplumber

from .base_parser import BaseSpecParser, EndpointSpec

# URLs are atomic units — never split across lines, concatenations, or multiline expressions.
_URL_PATTERN: re.Pattern[str] = re.compile(r"https://[^\s]+")
_ENDPOINT_PATTERN: re.Pattern[str] = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]*)")

# Thresholds are intentionally empty — callers must resolve against config/environments.yaml.
# Never hardcode numeric thresholds here; see DELIVERABLES.md framework Rule 1.
_UNRESOLVED_THRESHOLDS: dict = {}

_HOSTNAME_ENV_MAP: dict[str, str] = {
    "restcountries": "countries",
    "open-meteo": "weather",
    "openweathermap": "weather",
    "jsonplaceholder": "placeholder",
    "pokeapi": "pokemon",
    "swapi": "starwars",
}


def _infer_env_name(base_url: str) -> str:
    without_scheme = re.sub(r"^https?://", "", base_url)
    hostname = without_scheme.split("/")[0]
    sld = hostname.split(".")[0].lower()
    return _HOSTNAME_ENV_MAP.get(sld, sld)


def _extract_base_url(url: str) -> str:
    url = url.rstrip(".,;:)")
    match = re.match(r"(https://[^/]+(?:/[^/]+)?)", url)
    return match.group(1) if match else url


class PDFParser(BaseSpecParser):
    """Parse PDF specification documents and extract :class:`~base_parser.EndpointSpec` objects.

    Performs a two-pass scan: first collects base URLs, then collects endpoint
    paths, then groups endpoints with their nearest preceding URL.

    Note: URLs are atomic units — captured as single regex tokens and never
    split across lines, string concatenations, or multiline expressions.
    """

    supported_extensions: tuple[str, ...] = (".pdf", ".PDF")

    def parse(self, source: Path) -> list[EndpointSpec]:
        if not source.exists():
            raise FileNotFoundError(f"PDF spec not found: {source}")
        full_text = self._extract_full_text(source)
        if not full_text.strip():
            return []
        return self._build_specs(full_text)

    def _extract_full_text(self, source: Path) -> str:
        pages: list[str] = []
        with pdfplumber.open(source) as pdf:
            for page in pdf.pages:
                try:
                    text: Optional[str] = page.extract_text()
                except Exception:
                    text = None
                if text:
                    pages.append(text)
        # Join with newline so URL tokens at page boundaries are separated by whitespace.
        return "\n".join(pages)

    def _build_specs(self, text: str) -> list[EndpointSpec]:
        url_positions: list[tuple[int, str]] = [
            (m.start(), _extract_base_url(m.group()))
            for m in _URL_PATTERN.finditer(text)
        ]
        if not url_positions:
            return []
        endpoint_hits: list[tuple[int, str, str]] = [
            (m.start(), m.group(1), m.group(2))
            for m in _ENDPOINT_PATTERN.finditer(text)
        ]
        if not endpoint_hits:
            return []
        return self._group_and_build(url_positions, endpoint_hits)

    def _group_and_build(
        self,
        url_positions: list[tuple[int, str]],
        endpoint_hits: list[tuple[int, str, str]],
    ) -> list[EndpointSpec]:
        seen_url_positions: dict[str, int] = {}
        for pos, url in url_positions:
            if url not in seen_url_positions:
                seen_url_positions[url] = pos
        ordered_urls: list[tuple[int, str]] = sorted(
            ((pos, url) for url, pos in seen_url_positions.items()),
            key=lambda t: t[0],
        )

        results: list[EndpointSpec] = []
        seen_triples: set[tuple[str, str, str]] = set()
        fallback_url: str = ordered_urls[0][1]

        for ep_pos, method, path in endpoint_hits:
            chosen_url: str = fallback_url
            for url_pos, url in ordered_urls:
                if url_pos <= ep_pos:
                    chosen_url = url
                else:
                    break

            triple = (chosen_url, method, path)
            if triple in seen_triples:
                continue
            seen_triples.add(triple)

            results.append(
                EndpointSpec(
                    env_name=_infer_env_name(chosen_url),
                    base_url=chosen_url,
                    path=path,
                    method=method,
                    response_fields=[],
                    thresholds=dict(_UNRESOLVED_THRESHOLDS),
                    description=f"Extracted from PDF spec — {method} {chosen_url}{path}",
                )
            )
        return results
