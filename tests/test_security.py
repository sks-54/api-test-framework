"""Generic security and RFC compliance tests — config-driven, zero code changes per new API.

All test parametrization is driven by the `security` block in each environment's
config/environments.yaml entry. To add security coverage for a new API:

  1. Add the API to config/environments.yaml (standard 3-step extension)
  2. Add a `security` block with `probe_path`, `probe_params`, and optionally
     `injection_path` and `known_violations`
  3. These tests run automatically — no code changes needed here

Known violations (bugs) are declared in YAML as `known_violations` entries and
automatically translated to xfail markers at collection time, so CI stays green
while the bugs are tracked.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import allure
import pytest
import yaml

from apitf.http_client import HttpClient
from apitf.sla_exceptions import SLA_FAILURE_EXCEPTIONS

pytestmark = [pytest.mark.security, allure.suite("security")]

logger = logging.getLogger(__name__)

_SECURITY_HEADERS = (
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
)

_INJECTION_PAYLOADS: list[tuple[str, str]] = [
    (entry["label"], entry["payload"])
    for entry in json.loads(
        (Path(__file__).parent.parent / "test_data" / "injection_payloads.json").read_text(
            encoding="utf-8"
        )
    )
]

# ---------------------------------------------------------------------------
# Config loading — all parametrization data comes from environments.yaml
# ---------------------------------------------------------------------------

_ALL_ENVS: dict[str, Any] = yaml.safe_load(
    (Path(__file__).parent.parent / "config" / "environments.yaml").read_text(encoding="utf-8")
)
_SECURITY_ENVS: list[tuple[str, dict[str, Any]]] = [
    (name, cfg)
    for name, cfg in _ALL_ENVS.items()
    if name != "version" and "security" in cfg
]


def _violation_index(env_cfg: dict[str, Any], vtype: str, **kw: str) -> dict[str, Any] | None:
    """Return the first known_violation matching type + optional extra keys."""
    for v in env_cfg["security"].get("known_violations", []):
        if v.get("type") == vtype and all(v.get(k) == val for k, val in kw.items()):
            return v
    return None


def _xfail_mark(violation: dict[str, Any]) -> pytest.MarkDecorator:
    return pytest.mark.xfail(
        strict=True,
        raises=SLA_FAILURE_EXCEPTIONS,  # AssertionError (wrong status) + ConnectionError (timeout)
        reason=(
            f"Known {violation['bug_id']} / {violation['issue']}: {violation['reason']}. "
            f"xpass if the API fixes this — remove YAML known_violations entry then."
        ),
    )


_UNSAFE_METHODS: tuple[str, ...] = ("POST", "DELETE", "PUT", "PATCH")


def _method_params() -> list[Any]:
    params: list[Any] = []
    for env_name, env_cfg in _SECURITY_ENVS:
        for method in _UNSAFE_METHODS:
            marks: list[Any] = []
            v = _violation_index(env_cfg, "method", method=method)
            if v:
                marks.append(_xfail_mark(v))
            params.append(pytest.param(env_name, method, id=f"{env_name}-{method}", marks=marks))
    return params


def _header_params() -> list[Any]:
    params: list[Any] = []
    for env_name, env_cfg in _SECURITY_ENVS:
        marks: list[Any] = []
        v = _violation_index(env_cfg, "security_headers")
        if v:
            marks.append(_xfail_mark(v))
        params.append(pytest.param(env_name, id=env_name, marks=marks))
    return params


def _content_neg_params() -> list[Any]:
    params: list[Any] = []
    for env_name, env_cfg in _SECURITY_ENVS:
        marks: list[Any] = []
        v = _violation_index(env_cfg, "content_negotiation")
        if v:
            marks.append(_xfail_mark(v))
        params.append(pytest.param(env_name, id=env_name, marks=marks))
    return params


def _injection_params() -> list[Any]:
    params: list[Any] = []
    for env_name, env_cfg in _SECURITY_ENVS:
        sec = env_cfg["security"]
        if "injection_path" not in sec:
            continue
        for label, payload in _INJECTION_PAYLOADS:
            params.append(pytest.param(env_name, label, payload, id=f"{env_name}-{label}"))
    return params


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
# TC-S-001 / TC-S-002  RFC 7231 — unsupported HTTP methods return 405
# ---------------------------------------------------------------------------

@allure.title("TC-S: {env_name} {method} probe_path → 405 Method Not Allowed")
@pytest.mark.parametrize("env_name,method", _method_params())
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_method_not_allowed(env_name: str, method: str, env_config: dict[str, Any]) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all security tests."
        )
    cfg = env_config[env_name]
    sec = cfg["security"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.request(method, sec["probe_path"], params=sec.get("probe_params") or None)
    _attach(resp, name=f"{method} {sec['probe_path']}")
    assert resp.status_code == 405, (
        f"Expected 405 Method Not Allowed for {method} {base_url}{sec['probe_path']}, "
        f"got {resp.status_code}. RFC 7231 §6.5.5: server must return 405 for unsupported methods."
    )


# ---------------------------------------------------------------------------
# TC-S-003  RFC 7231 — Accept: application/xml returns 406 Not Acceptable
# ---------------------------------------------------------------------------

@allure.title("TC-S: {env_name} Accept: application/xml → 406 Not Acceptable")
@pytest.mark.parametrize("env_name", _content_neg_params())
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_content_negotiation_406(env_name: str, env_config: dict[str, Any]) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all security tests."
        )
    cfg = env_config[env_name]
    sec = cfg["security"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.request(
            "GET",
            sec["probe_path"],
            params=sec.get("probe_params") or None,
            extra_headers={"Accept": "application/xml"},
        )
    _attach(resp, name=f"GET {sec['probe_path']} (Accept: application/xml)")
    assert resp.status_code == 406, (
        f"Expected 406 Not Acceptable for Accept: application/xml on {base_url}{sec['probe_path']}, "
        f"got {resp.status_code}. RFC 7231 §6.5.6: return 406 when requested media type is unavailable."
    )


# ---------------------------------------------------------------------------
# TC-S-004 / TC-S-005 / ...  OWASP security response headers
# ---------------------------------------------------------------------------

@allure.title("TC-S: {env_name} probe_path returns OWASP baseline security headers")
@pytest.mark.parametrize("env_name", _header_params())
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_security_headers_present(env_name: str, env_config: dict[str, Any]) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all security tests."
        )
    cfg = env_config[env_name]
    sec = cfg["security"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(sec["probe_path"], params=sec.get("probe_params") or None)
    response_headers_lower = {k.lower(): v for k, v in resp.headers.items()}
    allure.attach(
        "\n".join(f"{k}: {v}" for k, v in sorted(response_headers_lower.items())),
        name=f"{env_name} — all response headers",
        attachment_type=allure.attachment_type.TEXT,
    )
    missing = [h for h in _SECURITY_HEADERS if h not in response_headers_lower]
    assert not missing, (
        f"{env_name} ({base_url}) missing OWASP baseline security headers: {missing}. "
        f"Required: Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options."
    )


# ---------------------------------------------------------------------------
# TC-S-006 / ...  Input safety — injection payloads return 4xx (never 500)
# ---------------------------------------------------------------------------

@allure.title("TC-S: {env_name} {label} in injection_path → no 5xx (OWASP: server handles safely)")
@pytest.mark.parametrize("env_name,label,payload", _injection_params())
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_injection_safe(
    env_name: str, label: str, payload: str, env_config: dict[str, Any]
) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all security tests."
        )
    cfg = env_config[env_name]
    sec = cfg["security"]
    base_url = cfg["base_url"]
    path = sec["injection_path"].replace("{payload}", payload)
    with HttpClient(base_url) as client:
        resp = client.get(path)
    _attach(resp, name=f"{label} → {path}")
    # OWASP spec: server must not return 5xx for malicious input (any 4xx or 2xx means safe handling).
    # Specific 4xx code varies by payload type — null byte may trigger 400, unknown input may trigger 404.
    assert resp.status_code < 500, (
        f"OWASP injection safety violation for {label} on {base_url}{path}: "
        f"got {resp.status_code}. A 5xx response indicates unsafe input handling — file as bug."
    )
