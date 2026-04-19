"""Tests for REST Countries API — all 4 required test cases plus coverage for
schema, boundaries, cross-reference, negative, performance, and reliability."""

from __future__ import annotations

import json
import logging
from typing import Any

import allure
import pytest

from apitf.http_client import HttpClient
from apitf.validators.country_validator import CountryValidator

pytestmark = [pytest.mark.countries, allure.suite("countries")]

logger = logging.getLogger(__name__)

EXPECTED_EUROPE_REGION_MIN: int = 40


def _attach(resp: Any, name: str = "Response") -> None:
    """Attach HTTP response metadata and body to the Allure report."""
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
# TC-C-001  Positive — Germany by name
# ---------------------------------------------------------------------------

@allure.title("TC-C-001: Germany lookup by name returns valid schema")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_germany_schema(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/germany")
    _attach(resp)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    result = CountryValidator().validate(resp.json_body)
    assert result.passed, result.errors


# ---------------------------------------------------------------------------
# TC-C-002  Positive — country by ISO code
# ---------------------------------------------------------------------------

@allure.title("TC-C-002: Country lookup by ISO alpha-2 code (DE)")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_country_by_alpha_code(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/alpha/DE")
    _attach(resp)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    result = CountryValidator().validate(resp.json_body)
    assert result.passed, result.errors
    names = [c["name"]["common"] for c in resp.json_body if isinstance(c, dict)]
    assert "Germany" in names, f"'Germany' not found in response names: {names}"


# ---------------------------------------------------------------------------
# TC-C-003  Negative — non-existent country name returns 404
# ---------------------------------------------------------------------------

@allure.title("TC-C-003: Non-existent country name returns 404")
@pytest.mark.negative
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_invalid_country_name_returns_404(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/zzzznotacountry")
    _attach(resp)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ---------------------------------------------------------------------------
# TC-C-004  Negative — invalid alpha code returns 404
# ---------------------------------------------------------------------------

@allure.title("TC-C-004: Invalid alpha code returns 404 — deviations are bugs")
@pytest.mark.negative
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-001 / Issue #5: /alpha/ZZZ999 returns 400 instead of 404. "
           "xpass if API fixes this — remove xfail marker then.",
)
def test_invalid_alpha_code_returns_404(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/alpha/ZZZ999")
    _attach(resp)
    assert resp.status_code == 404, (
        f"Expected 404 (resource not found), got {resp.status_code}. "
        f"Spec deviation — see BUG-001 / GitHub Issue #5."
    )


# ---------------------------------------------------------------------------
# TC-C-005  Boundary — Europe region has at least EXPECTED_EUROPE_REGION_MIN countries
# ---------------------------------------------------------------------------

@allure.title("TC-C-005: Europe region count meets minimum boundary")
@pytest.mark.boundary
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_europe_region_count(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/region/europe")
    _attach(resp)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert isinstance(resp.json_body, list), "Expected list response"
    count = len(resp.json_body)
    assert count >= EXPECTED_EUROPE_REGION_MIN, (
        f"Europe region returned {count} countries, expected >= {EXPECTED_EUROPE_REGION_MIN}"
    )


# ---------------------------------------------------------------------------
# TC-C-006  Boundary — population = 1 edge case (Vatican City)
# ---------------------------------------------------------------------------

@allure.title("TC-C-006: Very low population country (Vatican) passes schema validation")
@pytest.mark.boundary
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_very_low_population_passes_validator(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/vatican")
    _attach(resp)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    result = CountryValidator().validate(resp.json_body)
    assert result.passed, result.errors


# ---------------------------------------------------------------------------
# TC-C-007  State — cross-reference: Germany's region contains Germany
# ---------------------------------------------------------------------------

@allure.title("TC-C-007: Cross-reference — Germany's region endpoint contains Germany")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_cross_reference_germany_region(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        country_resp = client.get("/name/germany")
    _attach(country_resp, name="Step 1 — /name/germany")
    assert country_resp.status_code == 200
    assert isinstance(country_resp.json_body, list) and len(country_resp.json_body) > 0
    region = country_resp.json_body[0]["region"]

    with HttpClient(base_url) as client:
        region_resp = client.get(f"/region/{region}")
    _attach(region_resp, name=f"Step 2 — /region/{region}")
    assert region_resp.status_code == 200
    names = [c["name"]["common"] for c in region_resp.json_body if isinstance(c, dict)]
    assert "Germany" in names, f"Germany not found in region {region!r}: {names[:10]}"


# ---------------------------------------------------------------------------
# TC-C-008  Boundary — all-countries endpoint returns >= min_results_count
# ---------------------------------------------------------------------------

@allure.title("TC-C-008: All-countries endpoint returns at least min_results_count entries")
@pytest.mark.boundary
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_all_countries_min_count(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    min_count = cfg["thresholds"]["min_results_count"]
    with HttpClient(base_url) as client:
        resp = client.get("/all", params={"fields": "name"})
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms\nCount: {len(resp.json_body) if isinstance(resp.json_body, list) else 'n/a'}",
        name="Response — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert isinstance(resp.json_body, list)
    assert len(resp.json_body) >= min_count, (
        f"Expected >= {min_count} countries, got {len(resp.json_body)}"
    )


# ---------------------------------------------------------------------------
# TC-C-009  Performance — Germany lookup under max_response_time threshold
# ---------------------------------------------------------------------------

@allure.title("TC-C-009: Germany lookup response time within threshold")
@pytest.mark.performance
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_germany_lookup_performance(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    max_ms = cfg["thresholds"]["max_response_time"] * 1000
    with HttpClient(base_url) as client:
        resp = client.get("/name/germany")
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms\nThreshold: {max_ms:.0f}ms",
        name="Response — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert resp.status_code == 200
    assert resp.response_time_ms < max_ms, (
        f"Response time {resp.response_time_ms:.1f}ms exceeds threshold {max_ms}ms"
    )


# ---------------------------------------------------------------------------
# TC-C-010  Performance — region/europe response time within threshold
# ---------------------------------------------------------------------------

@allure.title("TC-C-010: Region/Europe response time within threshold")
@pytest.mark.performance
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_europe_region_performance(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    max_ms = cfg["thresholds"]["max_response_time"] * 1000
    with HttpClient(base_url) as client:
        resp = client.get("/region/europe")
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms\nThreshold: {max_ms:.0f}ms",
        name="Response — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert resp.status_code == 200
    assert resp.response_time_ms < max_ms, (
        f"Response time {resp.response_time_ms:.1f}ms exceeds threshold {max_ms}ms"
    )


# ---------------------------------------------------------------------------
# TC-C-011  Security — HTTPS enforced (HttpClient raises on http://)
# ---------------------------------------------------------------------------

@allure.title("TC-C-011: HttpClient rejects non-HTTPS base URLs")
@pytest.mark.security
def test_https_enforced(_env_config: dict[str, Any] | None = None) -> None:
    with pytest.raises(ValueError, match="Only HTTPS"):
        HttpClient("http://restcountries.com/v3.1")


# ---------------------------------------------------------------------------
# TC-C-012  Compatibility — response works with pathlib and json parsing
# ---------------------------------------------------------------------------

@allure.title("TC-C-012: Response JSON body is deserializable as a list of dicts")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_response_json_structure(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/france")
    _attach(resp)
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list), "Expected JSON list at root"
    assert all(isinstance(item, dict) for item in resp.json_body), "Expected list of dicts"


# ---------------------------------------------------------------------------
# TC-C-013  Negative — search by language returns correctly filtered results
# ---------------------------------------------------------------------------

@allure.title("TC-C-013: Language filter /lang/spa returns Spanish-speaking countries")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_by_language(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/lang/spa")
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms\nCount: {len(resp.json_body) if isinstance(resp.json_body, list) else 'n/a'}",
        name="Response — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    assert len(resp.json_body) > 0, "Expected at least one Spanish-speaking country"
    result = CountryValidator().validate(resp.json_body)
    assert result.passed, result.errors


# ---------------------------------------------------------------------------
# TC-C-014  Negative — filter by currency returns non-empty list
# ---------------------------------------------------------------------------

@allure.title("TC-C-014: Currency filter /currency/eur returns eurozone countries")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_countries_by_currency(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/currency/eur")
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms\nCount: {len(resp.json_body) if isinstance(resp.json_body, list) else 'n/a'}",
        name="Response — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    assert len(resp.json_body) > 0, "Expected at least one EUR country"


# ---------------------------------------------------------------------------
# TC-C-015  Negative — invalid region returns 404
# ---------------------------------------------------------------------------

@allure.title("TC-C-015: Invalid region returns 404")
@pytest.mark.negative
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_invalid_region_returns_404(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/region/notaregion99")
    _attach(resp)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ---------------------------------------------------------------------------
# TC-C-016  Boundary — fields filter reduces payload size
# ---------------------------------------------------------------------------

@allure.title("TC-C-016: Fields filter limits response keys to requested fields only")
@pytest.mark.boundary
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_fields_filter_limits_response(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/germany", params={"fields": "name,capital"})
    _attach(resp)
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    for item in resp.json_body:
        assert "name" in item, "Expected 'name' in filtered response"
        assert "capital" in item, "Expected 'capital' in filtered response"
        unexpected = set(item.keys()) - {"name", "capital"}
        assert not unexpected, f"Unexpected keys in filtered response: {unexpected}"


# ---------------------------------------------------------------------------
# TC-C-017  Reliability — /name/germany response includes HTTPS URL in flag
# ---------------------------------------------------------------------------

@allure.title("TC-C-017: Germany response flag URL uses HTTPS")
@pytest.mark.security
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_germany_flag_url_uses_https(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/germany")
    _attach(resp)
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list) and len(resp.json_body) > 0
    flags = resp.json_body[0].get("flags", {})
    for key in ("png", "svg"):
        if key in flags:
            url = flags[key]
            assert url.startswith("https://"), f"Flag URL {url!r} is not HTTPS"


# ---------------------------------------------------------------------------
# TC-C-018  Boundary — search is case-insensitive for country names
# ---------------------------------------------------------------------------

@allure.title("TC-C-018: Country name search is case-insensitive")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_country_name_case_insensitive(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp_lower = client.get("/name/germany")
        resp_upper = client.get("/name/GERMANY")
    _attach(resp_lower, name="/name/germany (lowercase)")
    _attach(resp_upper, name="/name/GERMANY (uppercase)")
    assert resp_lower.status_code == 200
    assert resp_upper.status_code == 200
    names_lower = {c["name"]["common"] for c in resp_lower.json_body if isinstance(c, dict)}
    names_upper = {c["name"]["common"] for c in resp_upper.json_body if isinstance(c, dict)}
    assert names_lower == names_upper, "Case-insensitive search returned different results"


# ---------------------------------------------------------------------------
# TC-C-019  Negative — empty country name returns 400 or 404
# ---------------------------------------------------------------------------

@allure.title("TC-C-019: Empty path segment in /name/ returns 4xx")
@pytest.mark.negative
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_empty_name_segment_returns_4xx(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/")
    _attach(resp)
    assert resp.status_code == 404, (
        f"Expected 404 for empty name segment, got {resp.status_code}. "
        f"Non-404 4xx response is a spec deviation — report as bug."
    )


# ---------------------------------------------------------------------------
# TC-C-020  Full schema — all-countries subset passes CountryValidator
# ---------------------------------------------------------------------------

@allure.title("TC-C-020: First 10 countries from /all pass full schema validation")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_all_countries_schema_sample(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/all", params={"fields": "name,capital,population,currencies,languages"})
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms\nTotal countries: {len(resp.json_body) if isinstance(resp.json_body, list) else 'n/a'}\nValidating: first 10",
        name="Response — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert resp.status_code == 200
    sample = resp.json_body[:10]
    allure.attach(
        json.dumps(sample, indent=2),
        name="Response — first 10 countries",
        attachment_type=allure.attachment_type.JSON,
    )
    result = CountryValidator().validate(sample)
    assert result.passed, result.errors


# ---------------------------------------------------------------------------
# TC-C-021  Boundary — all countries must have population >= 1
# ---------------------------------------------------------------------------

@allure.title("TC-C-021: All countries from /all have population >= 1")
@pytest.mark.boundary
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-003 / Issue #7: 5 uninhabited territories return population=0. "
           "xpass if API fixes this — remove xfail marker then.",
)
def test_all_population_boundary(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/all", params={"fields": "name,population"})
    allure.attach(
        f"URL: {resp.url}\nStatus: {resp.status_code}\nTime: {resp.response_time_ms:.1f}ms\nTotal countries: {len(resp.json_body) if isinstance(resp.json_body, list) else 'n/a'}",
        name="Response — metadata",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert resp.status_code == 200
    zero_pop = [
        item.get("name", {}).get("common", "unknown")
        for item in resp.json_body
        if isinstance(item, dict) and item.get("population", 1) == 0
    ]
    if zero_pop:
        allure.attach(
            json.dumps(zero_pop, indent=2),
            name="Countries with population=0 (spec violation)",
            attachment_type=allure.attachment_type.JSON,
        )
    assert zero_pop == [], (
        f"Expected all countries to have population >= 1. "
        f"Found {len(zero_pop)} with population=0: {zero_pop}. "
        f"Spec deviation — see BUG-003 / GitHub Issue #7."
    )


# ---------------------------------------------------------------------------
# TC-C-022  Equivalence — Americas is a valid region partition (returns 200)
# ---------------------------------------------------------------------------

@allure.title("TC-C-022: Americas region returns 200 with non-empty list")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_americas_region_valid_partition(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/region/americas")
    _attach(resp, name="/region/americas")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert isinstance(resp.json_body, list), "Expected list response"
    assert len(resp.json_body) > 0, "Expected non-empty list for Americas region"


# ---------------------------------------------------------------------------
# TC-C-023  Equivalence — region name is case-insensitive (EUROPE == europe)
# ---------------------------------------------------------------------------

@allure.title("TC-C-023: Region name lookup is case-insensitive (EUROPE returns 200)")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_region_name_case_insensitive(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp_lower = client.get("/region/europe")
        resp_upper = client.get("/region/EUROPE")
    _attach(resp_lower, name="/region/europe (lowercase)")
    _attach(resp_upper, name="/region/EUROPE (uppercase)")
    assert resp_lower.status_code == 200, f"Expected 200 for lowercase, got {resp_lower.status_code}"
    assert resp_upper.status_code == 200, (
        f"Expected 200 for uppercase region — API should be case-insensitive, got {resp_upper.status_code}"
    )
    assert isinstance(resp_lower.json_body, list) and isinstance(resp_upper.json_body, list)
    assert len(resp_lower.json_body) == len(resp_upper.json_body), (
        f"Case variants returned different counts: lower={len(resp_lower.json_body)}, "
        f"upper={len(resp_upper.json_body)}"
    )


# ---------------------------------------------------------------------------
# TC-C-024  Negative — special characters in name parameter return 4xx, not 500
# ---------------------------------------------------------------------------

@allure.title("TC-C-024: Special characters in /name/ return 4xx (not 500)")
@pytest.mark.negative
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_special_chars_in_name_returns_4xx(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/name/!@#$%special")
    _attach(resp, name="/name/!@#$%special")
    assert resp.status_code < 500, (
        f"Expected 4xx for special-char name, got {resp.status_code}. "
        f"A 5xx response indicates an unhandled server exception — report as bug."
    )
    assert resp.status_code == 404, (
        f"Expected 404 for non-existent special-char name, got {resp.status_code}."
    )


# ---------------------------------------------------------------------------
# TC-C-025  Negative — invalid field name in ?fields= returns 200 (API accepts gracefully)
# ---------------------------------------------------------------------------

@allure.title("TC-C-025: Invalid field name in ?fields= returns 200 with empty objects")
@pytest.mark.negative
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_invalid_field_name_returns_200_gracefully(env_config: dict[str, Any]) -> None:
    cfg = env_config["countries"]
    base_url = cfg["base_url"]
    with HttpClient(base_url) as client:
        resp = client.get("/all", params={"fields": "invalidfield"})
    _attach(resp, name="/all?fields=invalidfield")
    assert resp.status_code == 200, (
        f"Expected 200 (API returns empty objects for unknown field names), got {resp.status_code}. "
        f"A 5xx indicates an unhandled server exception — report as bug."
    )
    assert isinstance(resp.json_body, list), "Expected list response for /all"
    assert len(resp.json_body) > 0, "Expected non-empty list (countries with empty {} objects)"
