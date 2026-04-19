"""Shared HTTP client with retry, timing, HTTPS enforcement, and logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_USER_AGENT = "api-test-framework/1.0"
_DEFAULT_TIMEOUT = 30
_RETRY_TOTAL = 3
_RETRY_BACKOFF = 0.5
_RETRY_STATUS_CODES = (500, 502, 503, 504)


@dataclass
class HttpResponse:
    status_code: int
    json_body: Any
    headers: dict[str, str]
    response_time_ms: float
    url: str
    raw_text: str = field(repr=False)


class HttpClient:
    def __init__(self, base_url: str, timeout: int = _DEFAULT_TIMEOUT) -> None:
        if not base_url.startswith("https://"):
            raise ValueError(f"Only HTTPS base URLs are permitted, got: {base_url!r}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers["User-Agent"] = _USER_AGENT
        retry = Retry(
            total=_RETRY_TOTAL,
            backoff_factor=_RETRY_BACKOFF,
            status_forcelist=_RETRY_STATUS_CODES,
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def get(self, path: str, params: dict[str, Any] | None = None) -> HttpResponse:
        return self.request("GET", path, params=params)

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        url = f"{self._base_url}{path}"
        logger.debug("%s %s params=%r", method, url, params)
        start = time.monotonic()
        resp = self._session.request(
            method,
            url,
            params=params,
            headers=extra_headers,
            timeout=self._timeout,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        json_body: Any = None
        try:
            json_body = resp.json()
        except ValueError:
            logger.warning("Response from %s is not JSON (status=%d)", url, resp.status_code)

        logger.debug("%s %s → %d in %.1fms", method, url, resp.status_code, elapsed_ms)
        return HttpResponse(
            status_code=resp.status_code,
            json_body=json_body,
            headers=dict(resp.headers),
            response_time_ms=elapsed_ms,
            url=resp.url,
            raw_text=resp.text,
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
