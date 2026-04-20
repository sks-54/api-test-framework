import pytest
import allure
from apitf.http_client import HttpClient
from apitf.validators.weather_validator import WeatherValidator
from apitf.sla_exceptions import SLA_FAILURE_EXCEPTIONS

pytestmark = [pytest.mark.weather, allure.suite("weather")]

REQUIRED_FIELDS = [
    "latitude",
    "longitude",
    "generationtime_ms",
    "utc_offset_seconds",
    "timezone",
    "timezone_abbreviation",
    "elevation",
]


@allure.title("TC-001: Positive - valid forecast request returns 200 and passes schema validation")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_valid_request(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41})
    assert resp.status_code == 200
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-002: Positive - forecast with hourly temperature returns 200 and passes schema validation")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_hourly_temperature_returns_200(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "hourly": "temperature_2m"})
    assert resp.status_code == 200
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-003: Positive - forecast with daily max temperature returns 200 and passes schema validation")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_daily_temperature_max_returns_200(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "daily": "temperature_2m_max", "timezone": "Europe/Berlin"})
    assert resp.status_code == 200
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-004: Positive - forecast with timezone parameter returns 200 and passes schema validation")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_with_timezone_returns_200(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "timezone": "America/New_York"})
    assert resp.status_code == 200
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-005: Equivalence partitioning - forecast with standard European coordinates returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_equivalence_european_coordinates(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 48.85, "longitude": 2.35, "current_weather": True})
    assert resp.status_code == 200
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-006: Equivalence partitioning - forecast with valid Southern Hemisphere coordinates returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_equivalence_southern_hemisphere_coordinates(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": -33.87, "longitude": 151.21})
    assert resp.status_code == 200
    result = WeatherValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-007: Boundary - forecast with minimum latitude (-90) returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_boundary_min_latitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": -90, "longitude": 0})
    assert resp.status_code == 200


@allure.title("TC-008: Boundary - forecast with maximum latitude (90) returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_boundary_max_latitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 90, "longitude": 0})
    assert resp.status_code == 200


@allure.title("TC-009: Boundary - forecast with minimum longitude (-180) returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_boundary_min_longitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 0, "longitude": -180})
    assert resp.status_code == 200


@allure.title("TC-010: Boundary - forecast with maximum longitude (180) returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_boundary_max_longitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 0, "longitude": 180})
    assert resp.status_code == 200


@allure.title("TC-011: Negative - forecast without required latitude returns 400")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_negative_missing_latitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"longitude": 13.41})
    assert resp.status_code == 400


@allure.title("TC-012: Negative - forecast without required longitude returns 400")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_negative_missing_longitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52})
    assert resp.status_code == 400


@allure.title("TC-013: Negative - forecast with latitude exceeding valid range returns 400")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_negative_latitude_exceeds_max(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 999, "longitude": 13.41})
    assert resp.status_code == 400


@allure.title("TC-014: Negative - forecast with non-numeric latitude returns 400")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_negative_non_numeric_latitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": "invalid", "longitude": 13.41})
    assert resp.status_code == 400


@allure.title("TC-015: Negative - forecast with empty latitude string returns 400")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_negative_empty_latitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": "", "longitude": 13.41})
    assert resp.status_code == 400


@allure.title("TC-016: Boundary - forecast with forecast_days at minimum (1) returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_boundary_forecast_days_min(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "forecast_days": 1})
    assert resp.status_code == 200


@allure.title("TC-017: Boundary - forecast with forecast_days at maximum (16) returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_boundary_forecast_days_max(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "forecast_days": 16})
    assert resp.status_code == 200


@allure.title("TC-018: Performance - forecast response time is within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_performance_forecast_response_time(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41})
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-019: Security - HttpClient rejects HTTP base URL and requires HTTPS")
def test_security_https_enforcement(env_config: dict) -> None:
    cfg = env_config["weather"]
    with pytest.raises(ValueError, match="HTTPS"):
        HttpClient(cfg["base_url"].replace("https://", "http://"))


@allure.title("TC-020: State-based - forecast response body contains all required top-level fields")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_state_forecast_required_fields_present(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41})
    assert resp.status_code == 200
    body = resp.json_body
    for field in REQUIRED_FIELDS:
        assert field in body, f"Missing required field: {field}"


@allure.title("TC-021: State-based - forecast latitude in response reflects requested latitude")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_state_forecast_latitude_reflects_request(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41})
    assert resp.status_code == 200
    assert abs(resp.json_body["latitude"] - 52.52) < 1.0


@allure.title("TC-022: State-based - forecast with hourly param returns hourly key in response body")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_state_forecast_hourly_key_present(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "hourly": "temperature_2m"})
    assert resp.status_code == 200
    assert "hourly" in resp.json_body


@allure.title("TC-023: State-based - forecast with current_weather returns current_weather key in response body")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_state_forecast_current_weather_key_present(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "current_weather": True})
    assert resp.status_code == 200
    assert "current_weather" in resp.json_body


@allure.title("TC-W-024: xfail — /forecast without lat and lon should return 400 but returns 200 (BUG-002)")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-002 / Issue #6: /forecast with no latitude/longitude silently returns 200 instead of 400",
)
def test_forecast_missing_both_params_xfail(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"hourly": "temperature_2m"})
    assert resp.status_code == 400