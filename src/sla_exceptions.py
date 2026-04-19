"""
SLA failure exception adapter — single source of truth for xfail markers.

Any test covering an SLA_VIOLATION bug uses SLA_FAILURE_EXCEPTIONS as its
raises= value. This decouples xfail markers from platform-specific exception
knowledge: adding a new supported platform never requires touching test files.

Why these two types are exhaustive (no platform-specific enumeration needed):
- requests.exceptions.ConnectionError is the requests library's normalisation
  layer over all OS/transport failures: ReadTimeoutError, ConnectionResetError
  (Windows WSAECONNRESET 10054), NewConnectionError, etc. urllib3 catches the
  raw OS exception and wraps it before it reaches test code.
- AssertionError covers the case where retries eventually succeed but the
  accumulated response_time_ms exceeds the SLA threshold.

There is no third case: either a response arrives (→ AssertionError if slow)
or it doesn't (→ ConnectionError, regardless of the underlying OS reason).
"""

from __future__ import annotations

import requests

SLA_FAILURE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AssertionError,
    requests.exceptions.ConnectionError,
)
