import allure
import pytest

from apitf.http_client import HttpClient
from apitf.validators.countries_validator import CountriesValidator

REQUIRED_FIELDS: list[str] = [
    "tld", "cca2", "ccn3", "cca3", "cioc", "independent", "status",
    "unMember", "idd", "capital", "altSpellings", "region", "subregion",
    "landlocked", "borders", "name", "population", "currencies", "languages",
]

pytestmark = [pytest.mark.countries, allure.suite("countries")]


@allure.title("TC-001: Positive — GET /name/germany returns 200 and passes schema validation")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_by_name_positive(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    assert resp.status_code == 200
    result = CountriesValidator().validate(resp.json_body[0])
    assert result.passed, result.errors


@allure.title("TC-002: Positive — GET /region/europe returns 200 and passes schema validation")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_countries_by_region_positive(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/region/europe")
    assert resp.status_code == 200
    result = CountriesValidator().validate(resp.json_body[0])
    assert result.passed, result.errors


@allure.title("TC-003: Positive — GET /all?fields=name,population returns 200 and every country has the population field")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_all_countries_with_fields_positive(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/all?fields=name,population")
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list) and len(resp.json_body) > 200
    assert all("population" in c and c["population"] >= 0 for c in resp.json_body), \
        "Some entries are missing the population field or have a negative value"


@allure.title("TC-004: Equivalence partitioning — GET /name/france returns 200 for another valid country name")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_by_name_equivalence_france(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/france")
    assert resp.status_code == 200
    result = CountriesValidator().validate(resp.json_body[0])
    assert result.passed, result.errors


@allure.title("TC-005: Equivalence partitioning — GET /region/asia returns 200 for a valid region")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_countries_by_region_equivalence_asia(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/region/asia")
    assert resp.status_code == 200
    result = CountriesValidator().validate(resp.json_body[0])
    assert result.passed, result.errors


@allure.title("TC-006: Equivalence partitioning — response Content-Type header is application/json")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_response_content_type_is_json(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("Content-Type", "")


@allure.title("TC-007: Boundary — GET /name/chad returns 200 for shortest common single-word country name")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_minimum_name_length(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/chad")
    assert resp.status_code == 200
    result = CountriesValidator().validate(resp.json_body[0])
    assert result.passed, result.errors


@allure.title("TC-008: Boundary — GET /name/germany with all required fields as filter returns each field present")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_with_all_required_fields_filter(env_config: dict) -> None:
    cfg = env_config["countries"]
    fields_param = ",".join(REQUIRED_FIELDS)
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get(f"/name/germany?fields={fields_param}")
    assert resp.status_code == 200
    country = resp.json_body[0]
    for field in REQUIRED_FIELDS:
        assert field in country, f"Missing required field: {field}"


@allure.title("TC-009: Boundary — GET /name/guinea partial match returns multiple results containing Guinea")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_partial_name_match_returns_multiple_results(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/guinea")
    assert resp.status_code == 200
    names = [c.get("name", {}).get("common", "") for c in resp.json_body]
    assert len([n for n in names if "Guinea" in n]) > 1


@allure.title("TC-010: Negative — GET /name/unknowncountryxyz returns 404 for a nonexistent country")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_nonexistent_country_returns_404(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/unknowncountryxyz")
    assert resp.status_code == 404


@allure.title("TC-011: Negative — GET /region/unknownregionxyz returns 404 for a nonexistent region")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_nonexistent_region_returns_404(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/region/unknownregionxyz")
    assert resp.status_code == 404


@allure.title("TC-012: Negative — GET /name/12345 returns 404 for a numeric-only country name")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_numeric_name_returns_404(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/12345")
    assert resp.status_code == 404


@allure.title("TC-013: Performance — GET /name/germany responds within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_by_name_performance(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-014: Performance — GET /region/europe responds within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_region_europe_performance(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/region/europe")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-015: Performance — GET /all?fields=name,population responds within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_all_countries_performance(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/all?fields=name,population")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-016: Security — HttpClient rejects plain HTTP base URL with ValueError matching HTTPS")
def test_https_enforcement(env_config: dict) -> None:
    cfg = env_config["countries"]
    with pytest.raises(ValueError, match="HTTPS"):
        HttpClient(cfg["base_url"].replace("https://", "http://"))


@allure.title("TC-017: State-based — Germany response body contains all required fields")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_germany_response_contains_required_fields(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    assert len(resp.json_body) >= 1
    country = resp.json_body[0]
    for field in REQUIRED_FIELDS:
        assert field in country, f"Missing field: {field}"


@allure.title("TC-018: State-based — Germany has correct cca2, cca3, ccn3, region, subregion, and membership state")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_germany_state_values(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    assert resp.status_code == 200
    country = resp.json_body[0]
    assert country["cca2"] == "DE"
    assert country["cca3"] == "DEU"
    assert country["ccn3"] == "276"
    assert country["region"] == "Europe"
    assert country["subregion"] == "Western Europe"
    assert country["independent"] is True
    assert country["unMember"] is True
    assert country["landlocked"] is False
    assert country["status"] == "officially-assigned"


@allure.title("TC-019: State-based — Europe region response is a list with more than one country")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_europe_region_returns_multiple_countries(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/region/europe")
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    assert len(resp.json_body) > 40


@allure.title("TC-020: State-based — GET /all returns a list of more than 200 countries")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_all_countries_returns_full_list(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/all?fields=name,population")
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    assert len(resp.json_body) > 200


@allure.title("TC-023: Cross-reference — country from /name/germany appears in /region/europe results")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_country_name_appears_in_region_cross_reference(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        country_resp = client.get("/name/germany")
    assert country_resp.status_code == 200
    region = country_resp.json_body[0]["region"]
    with HttpClient(cfg["base_url"]) as client:
        region_resp = client.get(f"/region/{region}")
    assert region_resp.status_code == 200
    names = [c.get("name", {}).get("common", "") for c in region_resp.json_body]
    assert any("Germany" in n for n in names), (
        f"Germany not found in /region/{region} results. "
        "Cross-reference: a country found via /name must appear in /region results."
    )


@allure.title("TC-C-021: xfail — GET /alpha/ZZZ999 should return 404 but returns 400 (BUG-001)")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-001 / Issue #5: /alpha/ZZZ999 returns 400 Bad Request instead of 404 Not Found",
)
def test_alpha_invalid_code_returns_404_xfail(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/alpha/ZZZ999")
    assert resp.status_code == 404


@allure.title("TC-C-022: xfail — GET /all population field must be >= 1 for all entries (BUG-003)")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-003 / Issue #7: 5 territories return population=0 violating minimum population contract",
)
def test_all_countries_population_nonzero_xfail(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/all?fields=name,population")
    assert resp.status_code == 200
    assert all(c.get("population", 0) >= 1 for c in resp.json_body), \
        "Some entries have population=0 — spec requires all countries to have population >= 1"