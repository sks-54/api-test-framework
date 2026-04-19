# TEST PLAN: Multi-Environment API Test Framework
**Version:** 1.0  
**Date:** 2026-04-18  
**Author:** QA Sr Staff Engineer  
**Assignment:** Take-Home API Test Framework  
**APIs Under Test:** REST Countries v3.1 | Open-Meteo v1  

---

## Table of Contents
1. [Scope](#1-scope)
2. [Approach](#2-approach)
3. [Test Cases](#3-test-cases)
4. [Resources](#4-resources)
5. [Environment](#5-environment)
6. [Deliverables](#6-deliverables)
7. [Risk & Mitigations](#7-risk--mitigations)

---

## 1. Scope

### 1.1 In Scope

#### REST Countries API (`https://restcountries.com/v3.1`)
- Endpoint: `GET /region/{region}` — collection retrieval and count validation
- Endpoint: `GET /name/{name}` — single-resource retrieval and schema validation
- Endpoint: `GET /all?fields={fields}` — bulk retrieval with field filtering and data integrity
- Cross-reference behavior: consistency between `/name` and `/region` responses
- HTTP response codes: 200, 400, 404, 429, 500-series
- Response schema structure, field presence, and data type correctness
- Performance characteristics: response time against configurable SLA thresholds
- Reliability characteristics: retry behavior on transient 5xx failures
- Security posture: HTTPS enforcement, absence of credentials in logs or responses
- Compatibility: cross-platform path handling via `pathlib.Path`

#### Open-Meteo API (`https://api.open-meteo.com/v1`)
- Endpoint: `GET /forecast` with latitude/longitude, temperature_unit, and hourly parameters
- Parametrized execution across 5 cities defined in `test_data/cities.json`
- Temperature range validation for current and hourly data
- Hourly entry count validation
- Timezone field presence and format validation
- HTTP response codes: 200, 400, 404, 422, 500-series
- Performance, reliability, security, and compatibility coverage matching Countries API

#### Cross-API and Framework-Level
- Environment switching via `environments.yaml` (dev, staging, production)
- Parametrization via external JSON test data (`test_data/cities.json`)
- Retry logic configuration driven by YAML config values
- Performance threshold enforcement driven by `max_response_time` from YAML

### 1.2 Out of Scope
- Authentication or OAuth flows (both APIs are public and unauthenticated)
- Write operations (POST, PUT, PATCH, DELETE) — neither API exposes mutation endpoints under test
- UI or browser-level testing
- Load testing or sustained throughput/stress testing beyond single-request performance assertions
- Contract testing against a provider schema registry (e.g., Pact)
- Database or persistence layer validation
- CI/CD pipeline configuration and infrastructure provisioning
- Third-party data accuracy (e.g., verifying that a country's population figure is geopolitically current)
- WebSocket or GraphQL endpoints
- API versioning upgrade paths beyond v3.1 (Countries) and v1 (Open-Meteo)

---

## 2. Approach

### 2.1 Testing Methodology

This framework applies a **black-box functional testing** methodology augmented with **non-functional quality gates** (performance, reliability, security). All test logic is driven by externalized configuration; no base URLs, timeouts, thresholds, or environment-specific values are hardcoded in test files.

**Test Design Techniques applied across both APIs:**

| Technique | Application |
|---|---|
| Boundary Value Analysis (BVA) | Min/max temperature limits, population lower bound of 1, region count boundary at 40, field-filter edge cases |
| Equivalence Partitioning (EP) | Valid region names vs. invalid strings; valid city coordinates vs. out-of-range lat/lon; valid vs. missing query params |
| Positive Testing | Happy-path requests that must return 200 and well-formed payloads |
| Negative Testing | Malformed inputs, unknown resources, empty strings, special characters — must return appropriate 4xx |
| State-Based Testing | Sequential multi-call flows: data retrieved in step 1 is used as input in step 2 (cross-reference tests) |
| Error Handling | Simulated 404, timeout injection via `pytest-timeout`, malformed response structure assertions |
| Performance Testing | Every test records `response.elapsed` and asserts it is below `max_response_time` loaded from YAML |
| Reliability Testing | Retry decorator wraps requests; asserts successful resolution after transient 5xx (mocked via `responses` library) |
| Security Testing | Assert `https://` scheme on all request URLs; assert no API keys, tokens, or credentials appear in log output |
| Compatibility Testing | All file I/O uses `pathlib.Path`; tests verified on macOS, Linux, and Windows via CI matrix |

### 2.2 Environment Abstraction Strategy

All environment-specific configuration lives in `environments.yaml`. A `conftest.py` fixture reads the active environment (selected via `--env` CLI flag, defaulting to `dev`) and exposes a typed config object to all tests. Tests reference only config keys — never literal strings or numbers.

```
environments.yaml
  └── dev
        base_url_countries: https://restcountries.com/v3.1
        base_url_weather:   https://api.open-meteo.com/v1
        max_response_time:  3.0          # seconds
        retry_attempts:     3
        retry_backoff:      0.5          # seconds
        timeout:            10           # request timeout in seconds
  └── staging
        ...overrides...
  └── production
        ...overrides...
```

No test file imports a URL string directly. Every fixture and helper function receives the config object and reads `config.base_url_countries` or `config.base_url_weather`.

### 2.3 Parametrization Approach

**Cities parametrization (Open-Meteo):** `test_data/cities.json` contains an array of 5 city objects. A `conftest.py` session-scoped fixture reads this file using `pathlib.Path` and exposes the list. `@pytest.mark.parametrize` decorators consume this fixture to generate one test node per city. City records include: `name`, `latitude`, `longitude`, `timezone`, and `expected_temp_unit`.

**Field-filter parametrization (Countries):** The `GET /all?fields=` test is parametrized over multiple field combinations defined in `test_data/field_combinations.json` to validate filtering behavior without hardcoding query strings.

**Technique-level parametrization:** Boundary and equivalence partition inputs are defined in `test_data/countries_inputs.json` and `test_data/weather_inputs.json` so that adding new partitions requires only data file edits, not test code changes.

### 2.4 Assertion Strategy

- **Schema validation:** `jsonschema` library validates payload structure against schemas stored in `schemas/`. Schemas are loaded via `pathlib.Path` and validated on every relevant response.
- **Performance gate:** Every test asserts `response.elapsed.total_seconds() < config.max_response_time`. Failures are reported as separate assertion errors, not test skips.
- **Retry validation:** The `tenacity` library (or a custom decorator) wraps HTTP calls with `retry_attempts` and `retry_backoff` from config. Reliability tests mock a 503 response for the first N-1 attempts and assert the final attempt succeeds.
- **Security assertion:** A custom `assert_security` helper checks that the request URL scheme is `https` and scans captured log output for credential patterns using regex.

---

## 3. Test Cases

### 3.1 REST Countries API Test Cases

| ID | Endpoint | Technique | Description | Input | Expected Result | Priority |
|---|---|---|---|---|---|---|
| TC-C-001 | GET /region/europe | Positive | Verify European region returns more than 40 countries | region = `europe` | HTTP 200; `len(response) > 40` | P1 |
| TC-C-002 | GET /region/europe | BVA — Lower Boundary | Assert count is strictly greater than boundary value of 40, not equal | region = `europe` | `len(response) >= 41` | P1 |
| TC-C-003 | GET /region/europe | Performance | Response time is within configured SLA | region = `europe` | HTTP 200; `elapsed < config.max_response_time` | P1 |
| TC-C-004 | GET /region/americas | EP — Valid Partition | A different valid region returns a non-empty list | region = `americas` | HTTP 200; `len(response) > 0` | P2 |
| TC-C-005 | GET /region/nonexistentregion | Negative / Error Handling | Invalid region name returns 404 | region = `nonexistentregion` | HTTP 404; error body is JSON | P1 |
| TC-C-006 | GET /region/ (empty) | BVA — Empty Input | Empty region string returns 4xx error | region = `` (empty path) | HTTP 404 or 400 | P2 |
| TC-C-007 | GET /region/EUROPE | EP — Case Variation | Region name in uppercase is handled gracefully | region = `EUROPE` | HTTP 200 or HTTP 404 (documented behavior asserted) | P2 |
| TC-C-008 | GET /name/germany | Positive / Schema Validation | Germany response contains all required schema fields | name = `germany` | HTTP 200; payload contains `name`, `capital`, `population`, `currencies`, `languages` | P1 |
| TC-C-009 | GET /name/germany | Schema — Data Types | Schema fields carry correct data types | name = `germany` | `name` is object; `capital` is array; `population` is integer > 0; `currencies` is object; `languages` is object | P1 |
| TC-C-010 | GET /name/germany | State-Based / Cross-Reference | Country returned by /name appears in /region/europe results | Step 1: GET /name/germany; Step 2: GET /region/europe | Germany's `cca3` or `name.common` found in region results list | P1 |
| TC-C-011 | GET /name/unknowncountryxyz | Negative / Error Handling | Unknown country name returns 404 with meaningful error | name = `unknowncountryxyz` | HTTP 404; response body is valid JSON | P1 |
| TC-C-012 | GET /name/germany | Security | Request is made over HTTPS; no credentials appear in logs | name = `germany` | Request URL scheme is `https`; log output contains no token/key patterns | P1 |
| TC-C-013 | GET /name/germany | Reliability | Retries on 5xx and eventually succeeds | Mocked: first 2 attempts return 503; third returns 200 | Final response is HTTP 200; retry count equals 2 | P1 |
| TC-C-014 | GET /name/!@#$%special | Negative / Error Handling | Special characters in name parameter return 4xx gracefully | name = `!@#$%` | HTTP 400 or 404; no unhandled server exception (no 500) | P2 |
| TC-C-015 | GET /all?fields=name,population | Positive | All countries have population > 0 | fields = `name,population` | HTTP 200; every item in response has `population > 0` | P1 |
| TC-C-016 | GET /all?fields=name,population | BVA — Population Lower Bound | No country has population of exactly 0 or negative | fields = `name,population` | `all(c['population'] >= 1 for c in response)` | P1 |
| TC-C-017 | GET /all?fields=name,population | EP — Field Filter Completeness | Response items contain only the requested fields | fields = `name,population` | Each item has keys `name` and `population` only (no extra fields like `capital`) | P2 |
| TC-C-018 | GET /all?fields=name | EP — Single Field Filter | Single-field filter returns items with only that field | fields = `name` | HTTP 200; each item has `name` key; no `population` key present | P2 |
| TC-C-019 | GET /all?fields=invalidfield | Negative / Error Handling | Invalid field name in filter parameter handled gracefully | fields = `invalidfield` | HTTP 200 with empty objects, or HTTP 400; no 500 error | P3 |
| TC-C-020 | GET /all?fields=name,population | Compatibility | File paths in test helpers use pathlib.Path; test runs on Windows and Unix | N/A (framework-level) | Test passes on both path separator conventions; no hardcoded `/` or `\\` separators | P2 |

### 3.2 Open-Meteo API Test Cases

| ID | Endpoint | Technique | Description | Input | Expected Result | Priority |
|---|---|---|---|---|---|---|
| TC-W-001 | GET /forecast | Positive / Parametrized | Forecast returns HTTP 200 for all 5 cities in cities.json | lat/lon from cities.json (5 cities) | HTTP 200 for each city; response is valid JSON | P1 |
| TC-W-002 | GET /forecast | BVA — Temperature Min | Hourly temperatures are above absolute minimum of -80°C | hourly = `temperature_2m`; all 5 cities | `all(t >= -80 for t in hourly_temps)` | P1 |
| TC-W-003 | GET /forecast | BVA — Temperature Max | Hourly temperatures are below absolute maximum of 60°C | hourly = `temperature_2m`; all 5 cities | `all(t <= 60 for t in hourly_temps)` | P1 |
| TC-W-004 | GET /forecast | BVA — Boundary Coordinates | Latitude at exact boundary value (90.0) is handled | latitude = `90.0`, longitude = `0.0` | HTTP 200 or 422; no unhandled 500 | P2 |
| TC-W-005 | GET /forecast | BVA — Out-of-Range Coordinate | Latitude beyond valid range returns error | latitude = `91.0`, longitude = `0.0` | HTTP 400 or 422; error message references invalid parameter | P1 |
| TC-W-006 | GET /forecast | Positive | Hourly entry count is greater than 0 for each city | hourly = `temperature_2m`; all 5 cities | `len(response['hourly']['temperature_2m']) > 0` | P1 |
| TC-W-007 | GET /forecast | Positive / Schema | Timezone field is present in response for each city | All 5 cities | `'timezone' in response` and value is a non-empty string | P1 |
| TC-W-008 | GET /forecast | EP — Valid Temperature Unit | Celsius unit parameter returns temperatures in expected range | temperature_unit = `celsius` | HTTP 200; `timezone` present; temps in [-80, 60] | P1 |
| TC-W-009 | GET /forecast | EP — Invalid Temperature Unit | Invalid temperature unit parameter returns error | temperature_unit = `kelvin` | HTTP 400 or 422; error body references invalid parameter | P2 |
| TC-W-010 | GET /forecast | Negative / Error Handling | Missing required latitude parameter returns 422 | longitude = `13.4`, no latitude | HTTP 400 or 422; error message references missing `latitude` | P1 |
| TC-W-011 | GET /forecast | Negative / Error Handling | Non-numeric latitude value returns 422 | latitude = `abc`, longitude = `13.4` | HTTP 400 or 422; no unhandled 500 | P1 |
| TC-W-012 | GET /forecast | Performance | Response time is within configured SLA for each city | All 5 cities; `max_response_time` from config | `elapsed < config.max_response_time` for every parametrized case | P1 |
| TC-W-013 | GET /forecast | Reliability | Retries on 5xx and eventually succeeds | Mocked: first attempt returns 503; second returns 200 | Final response HTTP 200; retry mechanism triggered | P1 |
| TC-W-014 | GET /forecast | Security | All weather requests use HTTPS | Any valid city from cities.json | Request URL scheme is `https`; no credentials appear in captured logs | P1 |
| TC-W-015 | GET /forecast | State-Based | Hourly timestamps are sequential and cover a positive time span | Any valid city; hourly = `temperature_2m` | `hourly['time']` is a sorted list with at least 24 entries and contiguous hourly intervals | P2 |
| TC-W-016 | GET /forecast | Error Handling — Timeout | Request that exceeds configured timeout raises exception gracefully | Mocked delayed response exceeding `config.timeout` | `requests.Timeout` or equivalent exception caught; no crash; failure is reported | P1 |
| TC-W-017 | GET /forecast | EP — Extra/Unknown Parameters | Unknown query parameter is silently ignored or triggers 400 | latitude = `52.52`, longitude = `13.41`, unknownparam = `test` | HTTP 200 (param ignored) or HTTP 400; no 500 | P3 |
| TC-W-018 | GET /forecast | Compatibility | cities.json is loaded using pathlib.Path; test runs cross-platform | N/A (framework-level) | Test data loads successfully on macOS, Linux, and Windows path conventions | P2 |

### 3.3 Summary Statistics

| Category | Count |
|---|---|
| REST Countries test cases | 20 |
| Open-Meteo test cases | 18 |
| **Total test cases** | **38** |
| P1 (Critical) | 24 |
| P2 (High) | 11 |
| P3 (Medium) | 3 |

### 3.4 Technique Coverage Matrix

| Technique | Countries | Weather | Total Cases |
|---|---|---|---|
| Boundary Value Analysis | TC-C-002, TC-C-006, TC-C-016 | TC-W-002, TC-W-003, TC-W-004, TC-W-005 | 7 |
| Equivalence Partitioning | TC-C-004, TC-C-007, TC-C-017, TC-C-018, TC-C-019 | TC-W-008, TC-W-009, TC-W-017 | 8 |
| Positive Testing | TC-C-001, TC-C-008, TC-C-015 | TC-W-001, TC-W-006, TC-W-007 | 6 |
| Negative Testing | TC-C-005, TC-C-011, TC-C-014 | TC-W-010, TC-W-011, TC-W-017 | 7 |
| State-Based | TC-C-010 | TC-W-015 | 2 |
| Error Handling | TC-C-005, TC-C-011, TC-C-014, TC-C-019 | TC-W-010, TC-W-011, TC-W-016 | 7 |
| Performance | TC-C-003 | TC-W-012 | 2 |
| Reliability | TC-C-013 | TC-W-013 | 2 |
| Security | TC-C-012 | TC-W-014 | 2 |
| Compatibility | TC-C-020 | TC-W-018 | 2 |

---

## 4. Resources

### 4.1 Tools and Libraries

| Tool / Library | Version (Minimum) | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| pytest | 7.4+ | Test runner, parametrization, fixtures |
| pytest-timeout | 2.1+ | Timeout injection for error-handling tests |
| requests | 2.31+ | HTTP client for all API calls |
| responses | 0.23+ | HTTP mocking for reliability and timeout tests |
| jsonschema | 4.20+ | JSON schema validation against stored schema files |
| PyYAML | 6.0+ | Parsing `environments.yaml` |
| tenacity | 8.2+ | Retry decorator with configurable attempts and backoff |
| pathlib | stdlib | Cross-platform file path handling |
| pytest-html | 3.2+ | HTML test report generation |
| pytest-xdist | 3.3+ | Parallel test execution |
| allure-pytest | 2.13+ | (Optional) Rich reporting with step-level detail |

### 4.2 Test Data Files

| File | Purpose |
|---|---|
| `test_data/cities.json` | 5 city objects with lat, lon, timezone, name for parametrized weather tests |
| `test_data/countries_inputs.json` | Equivalence partition inputs for Countries API tests |
| `test_data/weather_inputs.json` | Boundary and partition inputs for weather coordinate tests |
| `test_data/field_combinations.json` | Field filter combinations for `/all?fields=` parametrization |
| `schemas/country_schema.json` | JSON Schema definition for a single country object |
| `schemas/forecast_schema.json` | JSON Schema definition for a weather forecast response |
| `environments.yaml` | All environment-specific configuration values |

### 4.3 Environments

| Environment | Purpose |
|---|---|
| `dev` | Local developer execution; lenient timeouts; verbose logging |
| `staging` | Pre-release validation; production-equivalent thresholds |
| `production` | Smoke validation only; read-only; stricter SLA thresholds |

### 4.4 Infrastructure

- Local machine: macOS / Linux / Windows (all supported via `pathlib.Path`)
- CI: GitHub Actions or equivalent; matrix across Python 3.10 / 3.11 / 3.12 on ubuntu-latest and windows-latest
- No private infrastructure required; both APIs are publicly accessible

---

## 5. Environment

### 5.1 environments.yaml Structure

The `environments.yaml` file is the single source of truth for all runtime configuration. Its schema is as follows:

```yaml
environments:
  dev:
    base_url_countries: "https://restcountries.com/v3.1"
    base_url_weather: "https://api.open-meteo.com/v1"
    max_response_time: 3.0        # SLA threshold in seconds
    timeout: 10                   # requests timeout in seconds
    retry_attempts: 3             # total attempts before failure
    retry_backoff: 0.5            # seconds between retries (exponential multiplier)
    log_level: "DEBUG"
    verify_ssl: true

  staging:
    base_url_countries: "https://restcountries.com/v3.1"
    base_url_weather: "https://api.open-meteo.com/v1"
    max_response_time: 2.0
    timeout: 8
    retry_attempts: 3
    retry_backoff: 1.0
    log_level: "INFO"
    verify_ssl: true

  production:
    base_url_countries: "https://restcountries.com/v3.1"
    base_url_weather: "https://api.open-meteo.com/v1"
    max_response_time: 1.5
    timeout: 5
    retry_attempts: 2
    retry_backoff: 1.0
    log_level: "WARNING"
    verify_ssl: true
```

### 5.2 How Configuration Flows Into Tests

1. `conftest.py` registers a `--env` CLI option (default: `dev`).
2. A session-scoped `config` fixture reads `environments.yaml` using `pathlib.Path(__file__).parent / "environments.yaml"`, parses the YAML, and returns a `SimpleNamespace` or typed dataclass for the active environment.
3. All test files and helper modules accept the `config` fixture via dependency injection. No test file imports a URL, timeout, or threshold value directly.
4. The `cities` fixture in `conftest.py` reads `test_data/cities.json` using `pathlib.Path`, ensuring cross-platform compatibility.

### 5.3 Environment Selection

```bash
# Run against dev (default)
pytest

# Run against staging
pytest --env staging

# Run against production (smoke tests only, tagged @production)
pytest --env production -m production
```

### 5.4 No Hardcoded Values Policy

The following values must never appear as literals in any `.py` test file:
- Base URLs or hostnames
- Numeric timeout or threshold values
- Retry counts or backoff delays
- File paths using string concatenation or os.path (use `pathlib.Path` only)
- Temperature boundary constants (must be sourced from config or a named constant module)

Violations are enforced at code review and optionally via a `flake8` plugin or pre-commit hook.

---

## 6. Deliverables

This test plan phase produces the following artifacts:

### 6.1 Source Files

| File | Description |
|---|---|
| `conftest.py` | Session and function-scoped fixtures: `config` (environment loader), `cities` (JSON parametrize source), `http_client` (requests Session with retry adapter), `assert_security`, `assert_performance` helpers |
| `test_countries.py` | All 20 REST Countries test cases (TC-C-001 through TC-C-020); imports only from `conftest.py` and schema/data files |
| `test_weather.py` | All 18 Open-Meteo test cases (TC-W-001 through TC-W-018); parametrized over `cities` fixture |
| `TEST_PLAN.md` | This document |

### 6.2 Configuration and Data Files

| File | Description |
|---|---|
| `environments.yaml` | Multi-environment configuration; single source of truth |
| `test_data/cities.json` | 5 city records used for weather parametrization |
| `test_data/countries_inputs.json` | Input partitions for equivalence and boundary tests |
| `test_data/weather_inputs.json` | Coordinate boundary inputs for weather tests |
| `test_data/field_combinations.json` | Field filter combinations for `/all?fields=` tests |
| `schemas/country_schema.json` | JSON Schema for single-country response validation |
| `schemas/forecast_schema.json` | JSON Schema for weather forecast response validation |
| `pytest.ini` or `pyproject.toml` | Pytest configuration: markers, default `--env`, HTML report path |
| `requirements.txt` | Pinned dependency list |

### 6.3 Reports (Generated on Execution)

| Artifact | Description |
|---|---|
| `reports/report.html` | pytest-html report with pass/fail/skip counts and captured output |
| `reports/allure-results/` | Allure raw results (if allure-pytest is enabled) |
| Exit code | 0 = all tests passed; non-zero = failures present (used by CI gate) |

### 6.4 cities.json Schema Reference

```json
[
  {
    "name": "Berlin",
    "latitude": 52.52,
    "longitude": 13.41,
    "timezone": "Europe/Berlin",
    "expected_temp_unit": "celsius"
  },
  {
    "name": "New York",
    "latitude": 40.71,
    "longitude": -74.01,
    "timezone": "America/New_York",
    "expected_temp_unit": "celsius"
  },
  {
    "name": "Tokyo",
    "latitude": 35.68,
    "longitude": 139.69,
    "timezone": "Asia/Tokyo",
    "expected_temp_unit": "celsius"
  },
  {
    "name": "Sydney",
    "latitude": -33.87,
    "longitude": 151.21,
    "timezone": "Australia/Sydney",
    "expected_temp_unit": "celsius"
  },
  {
    "name": "Cape Town",
    "latitude": -33.93,
    "longitude": 18.42,
    "timezone": "Africa/Johannesburg",
    "expected_temp_unit": "celsius"
  }
]
```

---

## 7. Risk & Mitigations

### 7.1 API Availability

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| REST Countries API is down during test run | High | Low | Retry logic (up to `retry_attempts` from config) with exponential backoff; tests marked with `@pytest.mark.flaky` for CI re-run; mock fallback for unit-level validation |
| Open-Meteo API is down during test run | High | Low | Same retry and mock strategy; `responses` library enables offline execution of non-live scenarios |
| Partial API outage (intermittent 5xx) | Medium | Medium | `tenacity` retry decorator absorbs transient errors; test explicitly asserts final success after retries |

### 7.2 Rate Limiting

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| REST Countries enforces undocumented rate limit during CI runs | Medium | Low | `pytest-xdist` worker count limited to 2 (not maximum parallelism); `time.sleep` backoff on 429 response; tests do not hammer the same endpoint in rapid succession |
| Open-Meteo free tier rate limit triggered by 5-city parametrization | Medium | Medium | Cities are tested sequentially by default; `--dist no` option used unless explicitly enabling parallelism; 429 is handled as a retriable error |

### 7.3 Flaky Network Conditions

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| High latency causes performance tests to fail on slow CI runners | Medium | Medium | `max_response_time` is environment-specific; CI uses `staging` profile with relaxed thresholds; performance failures are reported as warnings in dev, hard failures in production |
| DNS resolution failures cause connection errors | Low | Low | `requests.Session` is reused within a test session to benefit from connection pooling; retry logic covers `ConnectionError` as a retriable exception class |
| SSL certificate validation errors in restricted environments | Low | Low | `verify_ssl: true` is the default and must never be set to `false`; if a corporate proxy intercepts HTTPS, the proxy CA certificate must be added to the trust store at the OS level |

### 7.4 API Version Drift

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| REST Countries API changes field names or response structure between v3.1 and a future version | High | Low | Schema files (`schemas/country_schema.json`) are versioned in the repository; schema validation failures surface version drift immediately; base URL includes version (`/v3.1`) and is pinned in `environments.yaml` |
| Open-Meteo changes the `forecast` endpoint parameter names or response shape | High | Low | `schemas/forecast_schema.json` catches structural changes; a dedicated smoke test (`TC-W-001`) runs on every CI pipeline execution to detect regressions early |
| API deprecates a field tested by schema validation | Medium | Low | Schema uses `additionalProperties: true` to allow new fields without failure; only required fields are asserted; changelog monitoring recommended as a manual process |

### 7.5 Test Data Staleness

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| A city in `cities.json` becomes invalid (e.g., coordinate errors in upstream data) | Low | Very Low | Cities are defined by latitude/longitude (stable geographic facts), not by API-side city name lookups; coordinate values do not change |
| Country data (population, capital) changes significantly | Low | Low | Tests assert field presence and type, not exact values (e.g., `population > 0`, not `population == 83_200_000`); no test is brittle to real-world data changes |

### 7.6 Security Risks

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Future API key requirement added to a currently public API | Medium | Low | `assert_security` helper already checks that no credentials appear in logs; when a key is added, the framework is ready to load it from environment variables (never from `environments.yaml` or source control) |
| Accidental logging of sensitive headers in DEBUG mode | Medium | Low | HTTP client wrapper filters `Authorization`, `X-Api-Key`, and `Cookie` headers before writing to log; `log_level` in production is `WARNING` to reduce log verbosity |

### 7.7 Framework and Dependency Risks

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Dependency version conflict between `pytest`, `responses`, and `jsonschema` | Medium | Low | `requirements.txt` pins exact versions; `pip install --upgrade` is not run in CI without explicit approval |
| `pathlib.Path` behavior difference on Windows (case sensitivity, separators) | Low | Low | CI matrix includes `windows-latest`; all path operations use `/` operator (PurePosixPath behavior is abstracted by `pathlib`) |

---

*End of Test Plan — Version 1.0*
