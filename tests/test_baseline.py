"""Generic baseline tests — config-driven, zero code changes per new API.

All parametrization is driven by environments.yaml. Every environment entry
that declares base_url and thresholds automatically gets these checks:

  TC-B-001  HTTPS enforcement — HttpClient rejects http:// at construction time
  TC-B-002  Positive baseline — probe_path returns 2xx within SLA threshold
  TC-B-003  Invalid-path 404 — /apitf_no_such_path_xyz_404 returns 404
  TC-B-004  Performance threshold — probe_path response time < max_response_time

To add a new API: add it to config/environments.yaml. No code changes here.
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

pytestmark = [pytest.mark.compatibility, allure.suite("baseline")]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_ALL_ENVS: dict[str, Any] = yaml.safe_load(
    (Path(__file__).parent.parent / "config" / "environments.yaml").read_text(encoding="utf-8")
)
_BASELINE_ENVS: list[tuple[str, dict[str, Any]]] = [
    (name, cfg)
    for name, cfg in _ALL_ENVS.items()
    if name != "version" and "base_url" in cfg
]

_NONEXISTENT_PATH = "/apitf_no_such_path_xyz_404"


def _violation_index(env_cfg: dict[str, Any], vtype: str) -> dict[str, Any] | None:
    for v in env_cfg.get("security", {}).get("known_violations", []):
        if v.get("type") == vtype:
            return v
    return None


def _probe(env_cfg: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Return (base_url, probe_path, probe_params) for an env."""
    base_url: str = env_cfg["base_url"]
    sec = env_cfg.get("security", {})
    probe_path: str = sec.get("probe_path", "/")
    probe_params: dict[str, Any] = sec.get("probe_params") or {}
    return base_url, probe_path, probe_params


def _env_params() -> list[Any]:
    return [pytest.param(name, id=name) for name, _ in _BASELINE_ENVS]


def _perf_params() -> list[Any]:
    params: list[Any] = []
    for env_name, env_cfg in _BASELINE_ENVS:
        marks: list[Any] = []
        v = _violation_index(env_cfg, "performance_sla")
        if v:
            marks.append(pytest.mark.xfail(
                strict=False,
                raises=SLA_FAILURE_EXCEPTIONS,
                reason=(
                    f"Known {v['bug_id']} / {v['issue']}: {v['reason']}. "
                    "xpass if the API meets the SLA — remove YAML known_violations entry then."
                ),
            ))
        params.append(pytest.param(env_name, id=env_name, marks=marks))
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
# TC-B-001  HTTPS enforcement — HttpClient must reject http:// at construction
# ---------------------------------------------------------------------------

@allure.title("TC-B: {env_name} base_url uses HTTPS (http:// rejected at construction)")
@pytest.mark.parametrize("env_name", _env_params())
def test_https_enforced(env_name: str, env_config: dict[str, Any]) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all baseline tests."
        )
    cfg = env_config[env_name]
    base_url: str = cfg["base_url"]
    assert base_url.startswith("https://"), (
        f"{env_name}: base_url must use HTTPS. Got: {base_url!r}. "
        "Update environments.yaml to use https://."
    )
    http_url = base_url.replace("https://", "http://", 1)
    with pytest.raises(ValueError, match="HTTPS"):
        HttpClient(http_url)


# ---------------------------------------------------------------------------
# TC-B-002  Positive baseline — probe_path returns 2xx
# ---------------------------------------------------------------------------

@allure.title("TC-B: {env_name} probe_path returns 2xx")
@pytest.mark.parametrize("env_name", _env_params())
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_positive_baseline(env_name: str, env_config: dict[str, Any]) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all baseline tests."
        )
    cfg = env_config[env_name]
    base_url, probe_path, probe_params = _probe(cfg)
    with HttpClient(base_url) as client:
        resp = client.get(probe_path, params=probe_params or None)
    _attach(resp, name=f"GET {probe_path}")
    assert 200 <= resp.status_code < 300, (
        f"{env_name} probe_path {base_url}{probe_path} returned {resp.status_code}. "
        f"Expected 2xx — baseline GET must succeed."
    )


# ---------------------------------------------------------------------------
# TC-B-003  Invalid-path 404
# ---------------------------------------------------------------------------

@allure.title("TC-B: {env_name} non-existent path → 404")
@pytest.mark.parametrize("env_name", _env_params())
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_invalid_path_404(env_name: str, env_config: dict[str, Any]) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all baseline tests."
        )
    cfg = env_config[env_name]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(_NONEXISTENT_PATH)
    _attach(resp, name=f"GET {_NONEXISTENT_PATH}")
    assert resp.status_code == 404, (
        f"{env_name}: GET {base_url}{_NONEXISTENT_PATH} returned {resp.status_code}. "
        f"Expected 404 Not Found for a non-existent resource. "
        f"RFC 7231 §6.5.4: server must return 404 when the origin server did not find the resource."
    )


# ---------------------------------------------------------------------------
# TC-B-004  Performance threshold — from YAML, never hardcoded
# ---------------------------------------------------------------------------

@allure.title("TC-B: {env_name} probe_path response time < max_response_time")
@pytest.mark.parametrize("env_name", _perf_params())
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_performance_threshold(env_name: str, env_config: dict[str, Any]) -> None:
    if env_name not in env_config:
        pytest.skip(
            f"--env flag excludes {env_name!r}. Run `pytest` (no --env) to include all baseline tests."
        )
    cfg = env_config[env_name]
    base_url, probe_path, probe_params = _probe(cfg)
    max_ms = cfg["thresholds"]["max_response_time"] * 1000
    with HttpClient(base_url) as client:
        resp = client.get(probe_path, params=probe_params or None)
    _attach(resp, name=f"GET {probe_path} (perf)")
    assert resp.response_time_ms < max_ms, (
        f"SLA violation: {env_name} {base_url}{probe_path} "
        f"took {resp.response_time_ms:.0f}ms, threshold is {max_ms:.0f}ms. "
        f"File as SLA_VIOLATION bug if consistently failing across reruns."
    )
