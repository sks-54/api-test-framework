"""PDF spec parser — extracts EndpointSpec objects from PDF documents."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

from apitf.spec_parser.base_parser import BaseSpecParser, EndpointSpec

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https://[^\s]+")
_METHOD_PATTERN = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\b")
_HOSTNAME_ENV_MAP: dict[str, str] = {
    "restcountries": "countries",
    "open-meteo": "weather",
    "api": "api",
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

        method_hits = list(_METHOD_PATTERN.finditer(full_text))
        for hit in method_hits:
            method = hit.group(0)
            pos = hit.start()
            base_url = self._nearest_url(url_positions, pos)
            if base_url is None:
                logger.warning("No URL found near method %r at position %d", method, pos)
                continue

            try:
                hostname = re.sub(r"https://", "", base_url).split("/")[0]
                sld = hostname.split(".")[0].lower()
                env_name = _HOSTNAME_ENV_MAP.get(sld, sld)
                path = "/" + "/".join(base_url.split("/")[3:]) if "/" in base_url[8:] else "/"
                specs.append(
                    EndpointSpec(
                        env_name=env_name,
                        base_url=base_url,
                        path=path,
                        method=method,
                        response_fields=[],
                        thresholds=_UNRESOLVED_THRESHOLDS,
                    )
                )
            except (IndexError, ValueError) as exc:
                logger.warning("Failed to build EndpointSpec from URL %r: %s", base_url, exc)

        logger.info("PDFParser extracted %d specs from %s", len(specs), source)
        return specs

    @staticmethod
    def _nearest_url(
        url_positions: list[tuple[int, str]], target: int
    ) -> str | None:
        preceding = [(pos, url) for pos, url in url_positions if pos <= target]
        if not preceding:
            return None
        return max(preceding, key=lambda x: x[0])[1]
