# Test Design Techniques

This framework applies 10 test design techniques across every API environment. The techniques are defined in `test_plans/<env>_test_plan.md` and implemented in `tests/test_<env>.py`.

---

## Technique Reference

### 1. Equivalence Partitioning

**Goal:** Test a representative value from each valid input class, not every possible value.

**When to use:** When an endpoint accepts a parameter with a large valid range (names, region codes, coordinates).

**Example — `tests/test_countries.py`:**
```python
@allure.title("TC-004: Equivalence partitioning — GET /name/france returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_by_name_equivalence_france(env_config: dict) -> None:
    # France is a representative valid country name — same input class as Germany
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/france")
    assert resp.status_code == 200
```

---

### 2. Boundary Value Analysis

**Goal:** Test at the exact edges of valid input ranges (min, max, one outside each).

**When to use:** Numeric parameters (latitude, longitude, forecast_days), identifier ranges, list sizes.

**Example — `tests/test_weather.py`:**
```python
@allure.title("TC-007: Boundary — forecast with minimum latitude (-90) returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_boundary_min_latitude(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": -90, "longitude": 0})
    assert resp.status_code == 200
```

---

### 3. Positive (Happy Path)

**Goal:** Verify that the standard valid request returns HTTP 200 and a correct body.

**When to use:** Every endpoint, as the baseline sanity check.

**Example — `tests/test_countries.py`:**
```python
@allure.title("TC-001: Positive — GET /name/germany returns 200 and passes schema validation")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_by_name_positive(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    assert resp.status_code == 200
    result = CountriesValidator().validate(resp.json_body[0])
    assert result.passed, result.errors
```

---

### 4. Negative (Error Paths)

**Goal:** Verify that invalid inputs return the exact specified error code — never a 500.

**When to use:** Missing required parameters, invalid values, nonexistent resources.

**Framework rule:** Assert the **exact** status code (never `>= 400` or `in (400, 404)`). If the API returns the wrong code, file a bug and `xfail`.

**Example — `tests/test_countries.py`:**
```python
@allure.title("TC-010: Negative — GET /name/unknowncountryxyz returns 404")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_nonexistent_country_returns_404(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/unknowncountryxyz")
    assert resp.status_code == 404  # exact code, never >= 400
```

---

### 5. Performance / SLA

**Goal:** Verify the response time is within the SLA threshold defined in `environments.yaml`.

**When to use:** At least one test per environment on the primary endpoint.

**Framework rule:** Threshold is always read from `cfg["thresholds"]["max_response_time"]` — never hardcoded.

**Example — `tests/test_countries.py`:**
```python
@allure.title("TC-013: Performance — GET /name/germany responds within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_country_by_name_performance(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000
```

---

### 6. Reliability

**Goal:** Verify that transient failures are tolerated and tests recover on retry.

**Implementation:** `@pytest.mark.flaky(reruns=2, reruns_delay=2)` on every live HTTP test. If a test consistently fails on all reruns, it is reclassified as `SLA_VIOLATION` and filed as a bug (not flakiness).

**Example** (applied to every `HttpClient` test):
```python
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_valid_request(env_config: dict) -> None:
    ...
```

---

### 7. Security

**Goal:** Verify HTTPS enforcement and OWASP security headers.

**When to use:** Mandatory for every environment — one HTTPS test and one headers test.

**Example — `tests/test_countries.py`:**
```python
@allure.title("TC-016: Security — HttpClient rejects plain HTTP base URL")
def test_https_enforcement(env_config: dict) -> None:
    cfg = env_config["countries"]
    with pytest.raises(ValueError, match="HTTPS"):
        HttpClient(cfg["base_url"].replace("https://", "http://"))
```

Note: No `@pytest.mark.flaky` on security tests — they don't make a real HTTP request.

---

### 8. State-Based (Cross-Reference)

**Goal:** Verify that two endpoints maintain consistent state — data returned by one is reflected in another.

**When to use:** When endpoints share entities (e.g., a country returned by `/name` must appear in `/region`).

**Example — `tests/test_countries.py`:**
```python
@allure.title("TC-018: State-based — Germany has correct region, cca2, membership state")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_germany_state_values(env_config: dict) -> None:
    cfg = env_config["countries"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    country = resp.json_body[0]
    assert country["cca2"] == "DE"
    assert country["region"] == "Europe"
    assert country["independent"] is True
```

---

### 9. Error Handling

**Goal:** Verify that malformed or out-of-range input produces a client error (4xx), never a server error (5xx).

**When to use:** Test inputs that are syntactically valid but semantically wrong — e.g., latitude=999, non-numeric values.

**Example — `tests/test_weather.py`:**
```python
@allure.title("TC-013: Negative — forecast with latitude exceeding valid range returns 400")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_negative_latitude_exceeds_max(env_config: dict) -> None:
    cfg = env_config["weather"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/forecast", params={"latitude": 999, "longitude": 13.41})
    assert resp.status_code == 400
```

---

### 10. Compatibility

**Goal:** Verify the framework runs cleanly on supported Python versions and platforms.

**Implementation:** CI matrix (Rule 26) — ubuntu/3.9, ubuntu/3.12, windows/3.11, mac/3.11. Tests pass on all four combinations, confirming no version-specific breakage.

**Enforced by:** `.github/workflows/ci.yml` Stage 2 (platform) + Stage 3 (versions). The gate job (Stage 4) blocks merge if any platform or version fails.

---

## Technique Coverage Map

| Technique | Countries | Weather | Baseline | Security |
|-----------|-----------|---------|----------|----------|
| Equivalence | TC-004, TC-005 | TC-005, TC-006 | — | — |
| Boundary | TC-007, TC-008, TC-009 | TC-007..TC-010, TC-016..TC-017 | — | — |
| Positive | TC-001, TC-002 | TC-001..TC-004 | TC-001..TC-004 | — |
| Negative | TC-010..TC-012 | TC-011..TC-015 | — | TC-method, TC-406 |
| Performance | TC-013..TC-015 | TC-018 | TC-005..TC-008 | — |
| Reliability | All flaky | All flaky | All flaky | — |
| Security | TC-016 | TC-019 | — | All |
| State-based | TC-017..TC-020 | TC-020..TC-023 | — | — |
| Error Handling | TC-012 | TC-013..TC-015 | — | — |
| Compatibility | CI matrix | CI matrix | CI matrix | CI matrix |
