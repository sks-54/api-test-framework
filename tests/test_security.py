"""Cross-environment security and RFC compliance tests.

Tests HTTP method enforcement (405), content negotiation (406), RFC 7231
method compliance, security response headers, and input safety (injection,
path traversal). These tests are cross-environment and only run without
--env flag (both APIs required).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import allure
import pytest

from src.http_client import HttpClient
from src.sla_exceptions import SLA_FAILURE_EXCEPTIONS

pytestmark = [pytest.mark.security, allure.suite("security")]

logger = logging.getLogger(__name__)

_SECURITY_HEADERS = (
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
)


def _attach(resp: Any, name: str = "Response") -> None:
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms",
        name=f"{name} — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    if resp.json_body is not None:
        body_text = json.dumps(resp.json_body, indent=2)
        if len(body_text) > 3000:
            body_text = body_text[:3000] + "\n... (truncated)"
        allure.attach(body_text, name=f"{name} — body", attachment_type=allure.attachment_type.JSON)


# ---------------------------------------------------------------------------
# TC-S-001  RFC 7231 — POST /name/germany must return 405 Method Not Allowed
# ---------------------------------------------------------------------------

@allure.title("TC-S-001: POST /name/germany returns 405 Method Not Allowed")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_post_method_rejected(env_config: dict[str, Any]) -> None:
    base_url = env_config["countries"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.request("POST", "/name/germany")
    _attach(resp, name="POST /name/germany")
    assert resp.status_code == 405, (
        f"Expected 405 Method Not Allowed for POST /name/germany, got {resp.status_code}. "
        f"RFC 7231 §6.5.5: server must return 405 for unsupported methods."
    )


# ---------------------------------------------------------------------------
# TC-S-002  RFC 7231 — DELETE /name/germany must return 405 Method Not Allowed
# ---------------------------------------------------------------------------

@allure.title("TC-S-002: DELETE /name/germany returns 405 Method Not Allowed")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_delete_method_rejected(env_config: dict[str, Any]) -> None:
    base_url = env_config["countries"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.request("DELETE", "/name/germany")
    _attach(resp, name="DELETE /name/germany")
    assert resp.status_code == 405, (
        f"Expected 405 Method Not Allowed for DELETE /name/germany, got {resp.status_code}. "
        f"RFC 7231 §6.5.5: server must return 405 for unsupported methods."
    )


# ---------------------------------------------------------------------------
# TC-S-003  RFC 7231 — Accept: application/xml returns 406 Not Acceptable
# ---------------------------------------------------------------------------

@allure.title("TC-S-003: Accept: application/xml returns 406 Not Acceptable")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_xml_accept_returns_406(env_config: dict[str, Any]) -> None:
    base_url = env_config["countries"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.request(
            "GET",
            "/name/germany",
            extra_headers={"Accept": "application/xml"},
        )
    _attach(resp, name="GET /name/germany (Accept: application/xml)")
    assert resp.status_code == 406, (
        f"Expected 406 Not Acceptable for Accept: application/xml, got {resp.status_code}. "
        f"RFC 7231 §6.5.6: server must return 406 when it cannot produce the requested media type."
    )


# ---------------------------------------------------------------------------
# TC-S-004  RFC 7231 VIOLATION — POST /forecast returns 415 instead of 405
# ---------------------------------------------------------------------------

@allure.title("TC-S-004: POST /forecast returns 405 Method Not Allowed (RFC 7231 compliance)")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-006 / Issue #14: POST /forecast returns 415 Unsupported Media Type "
           "instead of 405 Method Not Allowed. RFC 7231 §6.5.5 requires 405 for unsupported methods. "
           "415 is only correct when the method is allowed but the content type is wrong. "
           "xpass if Open-Meteo fixes this — remove xfail marker then.",
)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_weather_post_method_rfc_violation(env_config: dict[str, Any]) -> None:
    base_url = env_config["weather"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.request(
            "POST",
            "/forecast",
            params={"latitude": 52.52, "longitude": 13.41, "hourly": "temperature_2m"},
        )
    _attach(resp, name="POST /forecast (RFC compliance check)")
    assert resp.status_code == 405, (
        f"Expected 405 Method Not Allowed (RFC 7231 §6.5.5), got {resp.status_code}. "
        f"Actual: 415 Unsupported Media Type — 415 is only correct when the method IS allowed "
        f"but the content-type is wrong. POST is not an allowed method on /forecast. "
        f"See BUG-006 / GitHub Issue #14."
    )


# ---------------------------------------------------------------------------
# TC-S-005  Security headers — Countries API missing HSTS and security headers
# ---------------------------------------------------------------------------

@allure.title("TC-S-005: REST Countries API returns required security headers")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-007 / Issue #15: restcountries.com returns no HSTS, "
           "X-Content-Type-Options, or X-Frame-Options headers. "
           "These are OWASP-recommended baseline security headers. "
           "xpass if API adds these headers — remove xfail marker then.",
)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_security_headers_present(env_config: dict[str, Any]) -> None:
    base_url = env_config["countries"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/germany")
    _attach(resp, name="GET /name/germany (security header check)")
    response_headers_lower = {k.lower(): v for k, v in resp.headers.items()}
    allure.attach(
        "\n".join(f"{k}: {v}" for k, v in sorted(response_headers_lower.items())),
        name="All response headers",
        attachment_type=allure.attachment_type.TEXT,
    )
    missing = [h for h in _SECURITY_HEADERS if h not in response_headers_lower]
    assert not missing, (
        f"REST Countries API is missing required security headers: {missing}. "
        f"OWASP baseline: Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options. "
        f"See BUG-007 / GitHub Issue #15."
    )


# ---------------------------------------------------------------------------
# TC-S-006  Security headers — Open-Meteo API missing HSTS and security headers
# ---------------------------------------------------------------------------

@allure.title("TC-S-006: Open-Meteo API returns required security headers")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-008 / Issue #16: api.open-meteo.com returns no HSTS, "
           "X-Content-Type-Options, or X-Frame-Options headers. "
           "These are OWASP-recommended baseline security headers. "
           "xpass if API adds these headers — remove xfail marker then.",
)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_weather_security_headers_present(env_config: dict[str, Any]) -> None:
    base_url = env_config["weather"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={"latitude": 52.52, "longitude": 13.41, "hourly": "temperature_2m", "forecast_days": 1},
        )
    _attach(resp, name="GET /forecast (security header check)")
    response_headers_lower = {k.lower(): v for k, v in resp.headers.items()}
    allure.attach(
        "\n".join(f"{k}: {v}" for k, v in sorted(response_headers_lower.items())),
        name="All response headers",
        attachment_type=allure.attachment_type.TEXT,
    )
    missing = [h for h in _SECURITY_HEADERS if h not in response_headers_lower]
    assert not missing, (
        f"Open-Meteo API is missing required security headers: {missing}. "
        f"OWASP baseline: Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options. "
        f"See BUG-008 / GitHub Issue #16."
    )


# ---------------------------------------------------------------------------
# TC-S-007  Input safety — SQL injection in /name/ returns 4xx (not 500)
# ---------------------------------------------------------------------------

@allure.title("TC-S-007: SQL injection in /name/ returns 4xx — server handles safely")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_sql_injection_safe(env_config: dict[str, Any]) -> None:
    base_url = env_config["countries"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/germany' OR 1=1--")
    _attach(resp, name="SQL injection in /name/")
    assert resp.status_code < 500, (
        f"Expected 4xx for SQL injection input, got {resp.status_code}. "
        f"A 5xx response indicates the server is not safely handling the input."
    )
    assert resp.status_code == 404, (
        f"Expected 404 (treated as unknown country name), got {resp.status_code}."
    )


# ---------------------------------------------------------------------------
# TC-S-008  Input safety — path traversal in /name/ returns 4xx (not 500)
# ---------------------------------------------------------------------------

@allure.title("TC-S-008: Path traversal in /name/ returns 4xx — server handles safely")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_path_traversal_safe(env_config: dict[str, Any]) -> None:
    base_url = env_config["countries"]["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/../../etc/passwd")
    _attach(resp, name="Path traversal in /name/")
    assert resp.status_code < 500, (
        f"Expected 4xx for path traversal input, got {resp.status_code}. "
        f"A 5xx response indicates the server is not safely handling the input."
    )
    assert resp.status_code == 404, (
        f"Expected 404 (path traversal neutralised), got {resp.status_code}."
    )
