"""
SLA failure exception adapter — single source of truth for xfail markers.

Any test covering an SLA_VIOLATION bug uses SLA_FAILURE_EXCEPTIONS as its
raises= value. This decouples xfail markers from platform-specific exception
knowledge: adding a new supported platform never requires touching test files.

Why these three types are exhaustive:
- requests.exceptions.ConnectionError — transport failures: ReadTimeoutError,
  ConnectionResetError (Windows WSAECONNRESET 10054), NewConnectionError, etc.
  urllib3 normalises all OS-level socket errors into this hierarchy.
- requests.exceptions.RetryError — raised when urllib3 exhausts max_retries
  after repeated 5xx responses (e.g. server returning 500 on every attempt).
  MRO: RetryError → RequestException → OSError (not a subclass of ConnectionError,
  confirmed on requests 2.32.x).
- AssertionError — covers the case where retries eventually succeed but the
  accumulated response_time_ms exceeds the configured SLA threshold.
"""

from __future__ import annotations

import requests

SLA_FAILURE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AssertionError,
    requests.exceptions.ConnectionError,
    requests.exceptions.RetryError,
)
