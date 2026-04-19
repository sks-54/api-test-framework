"""Tests for Open-Meteo weather forecast API — 5 parametrized cities from cities.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import allure
import pytest

from src.http_client import HttpClient
from src.validators.weather_validator import WeatherValidator

pytestmark = [pytest.mark.weather, allure.suite("weather")]

logger = logging.getLogger(__name__)

CITIES = json.loads(
    (Path(__file__).parent.parent / "test_data" / "cities.json").read_text(encoding="utf-8")
)

HOURLY_PARAMS = "temperature_2m"
FORECAST_DAYS = 1


# ---------------------------------------------------------------------------
# TC-W-001  Positive — each city returns valid forecast schema
# ---------------------------------------------------------------------------

@allure.title("TC-W-001: Forecast for {city[name]} passes schema validation")
@pytest.mark.parametrize("city", CITIES, ids=[c["name"] for c in CITIES])
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_positive_schema(city: dict[str, Any], env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "hourly": HOURLY_PARAMS,
                "forecast_days": FORECAST_DAYS,
            },
        )
    assert resp.status_code == 200, (
        f"Expected 200 for {city['name']}, got {resp.status_code}"
    )
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, result.errors


# ---------------------------------------------------------------------------
# TC-W-002  Positive — response contains timezone field per city
# ---------------------------------------------------------------------------

@allure.title("TC-W-002: Forecast for {city[name]} includes non-empty timezone")
@pytest.mark.parametrize("city", CITIES, ids=[c["name"] for c in CITIES])
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_timezone_present(city: dict[str, Any], env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "hourly": HOURLY_PARAMS,
                "forecast_days": FORECAST_DAYS,
            },
        )
    assert resp.status_code == 200
    body = resp.json_body
    assert isinstance(body, dict), "Expected dict response"
    assert "timezone" in body, "Response missing 'timezone'"
    assert body["timezone"] and body["timezone"].strip(), "'timezone' must be non-empty"


# ---------------------------------------------------------------------------
# TC-W-003  Negative — invalid coordinates return 4xx
# ---------------------------------------------------------------------------

@allure.title("TC-W-003: Out-of-range latitude (999) returns 4xx")
@pytest.mark.negative
def test_forecast_negative_invalid_coords(env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={"latitude": 999, "longitude": 999, "hourly": HOURLY_PARAMS},
        )
    assert 400 <= resp.status_code < 500, (
        f"Expected 4xx for invalid coords, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# TC-W-004  Negative — missing required params returns 4xx
# ---------------------------------------------------------------------------

@allure.title("TC-W-004: Missing latitude/longitude parameters returns 400")
@pytest.mark.negative
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-002 / Issue #6: /forecast without lat/lon returns 200 silently. "
           "xpass if API fixes this — remove xfail marker then.",
)
def test_forecast_missing_params_returns_4xx(env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/forecast", params={"hourly": HOURLY_PARAMS})
    assert resp.status_code == 400, (
        f"Expected 400 when required params missing, got {resp.status_code}. "
        f"Spec deviation — see BUG-002 / GitHub Issue #6."
    )


# ---------------------------------------------------------------------------
# TC-W-005  Boundary — forecast_days=1 returns exactly 24 hourly entries
# ---------------------------------------------------------------------------

@allure.title("TC-W-005: forecast_days=1 returns 24 hourly temperature entries")
@pytest.mark.boundary
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_boundary_one_day(env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    city = CITIES[0]  # Berlin
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "hourly": HOURLY_PARAMS,
                "forecast_days": 1,
            },
        )
    assert resp.status_code == 200
    temps = resp.json_body.get("hourly", {}).get("temperature_2m", [])
    assert len(temps) == 24, f"Expected 24 hourly entries for 1 day, got {len(temps)}"


# ---------------------------------------------------------------------------
# TC-W-006  Boundary — temperature values within physical valid range [-80, 60]
# ---------------------------------------------------------------------------

@allure.title("TC-W-006: All temperatures for {city[name]} in range [-80°C, 60°C]")
@pytest.mark.parametrize("city", CITIES, ids=[c["name"] for c in CITIES])
@pytest.mark.boundary
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_temperature_range(city: dict[str, Any], env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "hourly": HOURLY_PARAMS,
                "forecast_days": FORECAST_DAYS,
            },
        )
    assert resp.status_code == 200
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, f"Temperature range violations for {city['name']}: {result.errors}"


# ---------------------------------------------------------------------------
# TC-W-007  Performance — each city forecast within max_response_time threshold
# ---------------------------------------------------------------------------

@allure.title("TC-W-007: Forecast for {city[name]} response time within threshold")
@pytest.mark.parametrize("city", CITIES, ids=[c["name"] for c in CITIES])
@pytest.mark.performance
def test_forecast_performance(city: dict[str, Any], env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    max_ms = cfg["thresholds"]["max_response_time"] * 1000
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "hourly": HOURLY_PARAMS,
                "forecast_days": FORECAST_DAYS,
            },
        )
    assert resp.status_code == 200
    assert resp.response_time_ms < max_ms, (
        f"{city['name']}: {resp.response_time_ms:.1f}ms exceeds threshold {max_ms}ms"
    )


# ---------------------------------------------------------------------------
# TC-W-008  Security — HTTPS enforced for weather client
# ---------------------------------------------------------------------------

@allure.title("TC-W-008: HttpClient rejects non-HTTPS base URLs")
@pytest.mark.security
def test_https_enforced_weather(_env_config: dict[str, Any] | None = None) -> None:
    with pytest.raises(ValueError, match="Only HTTPS"):
        HttpClient("http://api.open-meteo.com/v1")


# ---------------------------------------------------------------------------
# TC-W-009  Boundary — forecast_days=16 (max) returns at least 24 entries
# ---------------------------------------------------------------------------

@allure.title("TC-W-009: forecast_days=16 returns >= 24 hourly temperature entries")
@pytest.mark.boundary
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_boundary_max_days(env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    city = CITIES[0]  # Berlin
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "hourly": HOURLY_PARAMS,
                "forecast_days": 16,
            },
        )
    assert resp.status_code == 200
    temps = resp.json_body.get("hourly", {}).get("temperature_2m", [])
    assert len(temps) >= 24, f"Expected >= 24 entries for 16-day forecast, got {len(temps)}"


# ---------------------------------------------------------------------------
# TC-W-010  Negative — extreme south pole coordinates return 4xx
# ---------------------------------------------------------------------------

@allure.title("TC-W-010: Coordinates at south pole extremity (lat=-90) returns valid or 4xx")
@pytest.mark.boundary
def test_forecast_south_pole_boundary(env_config: dict[str, Any]) -> None:
    cfg = env_config["weather"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get(
            "/forecast",
            params={"latitude": -90, "longitude": 0, "hourly": HOURLY_PARAMS},
        )
    assert resp.status_code in (200, 400), (
        f"Expected 200 or 400 for edge coordinate, got {resp.status_code}"
    )
