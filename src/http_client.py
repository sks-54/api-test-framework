"""Shared HTTP client wrapper around requests.Session."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class HttpResponse:
    """Encapsulates a parsed HTTP response."""

    status_code: int
    json_body: Any
    response_time_ms: float
    url: str


class HttpClient:
    """Thread-safe HTTP client with retry logic and response-time tracking."""

    _USER_AGENT = "panw-qa-framework/1.0"
    _MAX_RETRIES = 3
    _BACKOFF_FACTOR = 1  # seconds; urllib3 uses exponential: {backoff} * (2 ** (retry - 1))
    _RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})

    def __init__(self, base_url: str, max_response_time: float) -> None:
        """
        Parameters
        ----------
        base_url:
            Root URL for all requests.  Must start with ``https://``.
        max_response_time:
            Soft SLA threshold in milliseconds.  Stored for use by callers /
            validators; not enforced internally to keep this layer generic.
        """
        if not base_url.startswith("https://"):
            raise ValueError(
                f"base_url must use HTTPS. Got: {base_url!r}"
            )

        self.base_url = base_url
        self.max_response_time = max_response_time

        retry_policy = Retry(
            total=self._MAX_RETRIES,
            backoff_factor=self._BACKOFF_FACTOR,
            status_forcelist=self._RETRY_STATUS_CODES,
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,  # we call raise_for_status() ourselves
        )
        adapter = HTTPAdapter(max_retries=retry_policy)

        self._session = requests.Session()
        self._session.mount("https://", adapter)
        self._session.headers.update({"User-Agent": self._USER_AGENT})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict | None = None) -> HttpResponse:
        """Perform a GET request and return an :class:`HttpResponse`.

        Parameters
        ----------
        path:
            Path relative to *base_url* (leading/trailing slashes are handled
            gracefully via :func:`urllib.parse.urljoin` semantics).
        params:
            Optional mapping of query-string parameters.

        Raises
        ------
        requests.HTTPError
            For any 4xx or 5xx response after all retry attempts are exhausted.
        """
        url = self._build_url(path)

        start_ns = time.monotonic_ns()
        response = self._session.get(url, params=params)
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000

        response.raise_for_status()

        try:
            body: Any = response.json()
        except ValueError:
            body = None

        return HttpResponse(
            status_code=response.status_code,
            json_body=body,
            response_time_ms=elapsed_ms,
            url=response.url,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """Join *base_url* and *path* in a slash-safe manner.

        ``urljoin`` requires the base to have a trailing slash so that the
        last path segment is treated as a directory, not a file.  We normalise
        both sides to avoid double-slash or dropped-segment issues.
        """
        base = self.base_url.rstrip("/") + "/"
        # Strip a single leading slash from path so urljoin doesn't treat it
        # as an absolute path and discard the base's path component.
        relative = path.lstrip("/")
        return urljoin(base, relative)
