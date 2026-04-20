# Test Plan — `weather` environment

**Base URL:** `https://api.open-meteo.com/v1`
**Probe path:** `/forecast`
**Generated:** `apitf-run` scaffold step
**Framework rules:** testing-standards.md, framework-rules.md

---

## Table of Contents

1. [Scope](#1-scope)
2. [Approach & Techniques](#2-approach--techniques)
3. [Test Cases](#3-test-cases)
4. [Test Data & Configuration](#4-test-data--configuration)
5. [Environment & Infrastructure](#5-environment--infrastructure)
6. [Acceptance Criteria](#6-acceptance-criteria)
7. [Risk & Mitigations](#7-risk--mitigations)

---

## 1. Scope

### In Scope

| Method | Path | Key parameters |
|--------|------|----------------|
| `GET` | `/forecast` | `latitude`, `longitude`, `hourly=temperature_2m` |
| `GET` | `/forecast` | `latitude`, `longitude`, `current_weather=true` |
| `GET` | `/forecast` | `latitude`, `longitude`, `forecast_days=1` (boundary) |
| `GET` | `/forecast` | Missing `latitude` / `longitude` (negative tests) |
| `GET` | `/forecast` | `latitude=999` (out-of-range error handling) |

**All sampled response fields:** `timezone`, `hourly`, `hourly.temperature_2m` (list of floats)

### Out of Scope

- Write operations (POST / PUT / PATCH / DELETE) unless the spec requires them
- Authentication flows (API keys, OAuth) — covered by the security technique only at the HTTP layer
- Third-party downstream systems beyond `https://api.open-meteo.com/v1`
- Load / stress testing (> 1 concurrent request)

---

## 2. Approach & Techniques

| Technique | Priority | TC count | Rationale |
|-----------|----------|----------|-----------|
| Positive (happy path)      | P1 | 1 per endpoint | Valid request → HTTP 200 + JSON |
| Schema validation          | P1 | 1 per endpoint | `WeatherValidator().validate()` passes |
| Equivalence partitioning   | P2 | 1 per endpoint | Representative valid input → 200 |
| Boundary value analysis    | P2 | 2 per endpoint | Min/max identifier edge cases |
| Negative / error paths     | P1 | 2 fixed        | Unknown path 404, bad params 400 |
| Error handling             | P2 | 1 fixed        | Malformed input → 4xx, not 5xx |
| Performance / SLA          | P1 | 1 fixed        | `/forecast` < `max_response_time` (YAML) |
| Reliability                | P2 | 1 fixed        | `@pytest.mark.flaky(reruns=2)` |
| Security                   | P1 | 2 fixed        | HTTPS enforcement + OWASP headers |
| Compatibility              | P3 | 1 fixed        | Python 3.9 + 3.12 matrix |

---

## 3. Test Cases

### weather API Test Cases

| ID | Endpoint | Technique | Description | Input | Expected | Priority |
|----|----------|-----------|-------------|-------|----------|----------|
| TC-WEA-001 | `GET /forecast` | Positive | Valid forecast request returns 200 and JSON body | `latitude=52.52`, `longitude=13.41`, `hourly=temperature_2m` | HTTP 200, `Content-Type: application/json` | P1 |
| TC-WEA-002 | `GET /forecast` | Schema | `timezone`, `hourly.temperature_2m` present and typed correctly | Valid params | `WeatherValidator().validate()` passes | P1 |
| TC-WEA-003 | `GET /forecast` | Positive | `current_weather=true` returns current weather block | `latitude=52.52`, `longitude=13.41`, `current_weather=true` | HTTP 200, `current_weather` key present | P1 |
| TC-WEA-004 | `GET /forecast` | Positive | `forecast_days=1` returns single-day forecast | `latitude=52.52`, `longitude=13.41`, `forecast_days=1` | HTTP 200, `hourly.temperature_2m` list non-empty | P1 |
| TC-WEA-005 | `GET /forecast` | Equivalence | Berlin as representative valid coordinate pair | `latitude=52.52`, `longitude=13.41` | HTTP 200 | P2 |
| TC-WEA-006 | `GET /forecast` | Equivalence | Tokyo as second representative coordinate pair | `latitude=35.69`, `longitude=139.69` | HTTP 200 | P2 |
| TC-WEA-007 | `GET /forecast` | Boundary | Minimum valid latitude (-90) | `latitude=-90`, `longitude=0` | HTTP 200 | P2 |
| TC-WEA-008 | `GET /forecast` | Boundary | Maximum valid latitude (90) | `latitude=90`, `longitude=0` | HTTP 200 | P2 |
| TC-WEA-009 | `GET /forecast` | Boundary | Minimum valid longitude (-180) | `latitude=0`, `longitude=-180` | HTTP 200 | P2 |
| TC-WEA-010 | `GET /forecast` | Boundary | Maximum valid longitude (180) | `latitude=0`, `longitude=180` | HTTP 200 | P2 |
| TC-WEA-011 | `GET /forecast` | Negative | Missing `latitude` returns 400 | Omit `latitude` param | HTTP 400 | P1 |
| TC-WEA-012 | `GET /forecast` | Negative | Missing `longitude` returns 400 | Omit `longitude` param | HTTP 400 | P1 |
| TC-WEA-013 | `GET /forecast` | Error Handling | `latitude=999` (out of range) returns 400 | `latitude=999`, `longitude=13.41` | HTTP 400 | P2 |
| TC-WEA-014 | `GET /forecast` | Error Handling | `longitude=999` (out of range) returns 400 | `latitude=52.52`, `longitude=999` | HTTP 400 | P2 |
| TC-WEA-015 | `GET /forecast` | Error Handling | Non-numeric latitude returns 400 | `latitude=abc`, `longitude=0` | HTTP 400 | P2 |
| TC-WEA-016 | `GET /__apitf_nonexistent__` | Negative | Unknown path returns 404 | Invalid path | HTTP 404 exactly | P1 |
| TC-WEA-017 | `GET /forecast` | Negative | Missing required params returns 400 | Omit required param | HTTP 400 or 422 | P1 |
| TC-WEA-018 | `GET /forecast` | Error Handling | Malformed request does not trigger 5xx | Malformed query | HTTP 4xx, not 5xx | P2 |
| TC-WEA-019 | `GET /forecast` | Performance | Response within SLA threshold | Standard params | < `max_response_time` × 1000 ms (YAML, never hardcoded) | P1 |
| TC-WEA-020 | `GET /forecast` | Reliability | Transient failure retried and recovered | Network blip | Pass on retry ≤ 2; `@pytest.mark.flaky(reruns=2)` | P2 |
| TC-WEA-021 | `HttpClient('http://...')` | Security | HTTP (not HTTPS) is rejected at construction | Plain-HTTP base URL | `ValueError` raised, message contains `'HTTPS'` | P1 |
| TC-WEA-022 | `GET /forecast` | Security | OWASP security headers present in response | Standard request | `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` present | P1 |
| TC-WEA-023 | _(matrix)_ | Compatibility | Framework runs cleanly on Python 3.9 and 3.12 | CI matrix | All tests pass on ubuntu/3.9 + ubuntu/3.12 (Rule 26) | P3 |

**Total: 24 test cases**

---

## 4. Test Data & Configuration

- **Thresholds:** all numeric limits read from `config/environments.yaml` via `env_config` fixture — never hardcoded (Rule 1)
- **Coordinates / identifiers:** loaded from `test_data/` JSON files — never inline literals (Testing Standard 1)
- **Base URL:** `https://api.open-meteo.com/v1` (single source: `config/environments.yaml`)
- **Probe path:** `/forecast`
- **Sampled fields:** `_(sampled at scaffold time)_`

---

## 5. Environment & Infrastructure

| Item | Value |
|------|-------|
| Target API | `https://api.open-meteo.com/v1` |
| Python versions | 3.9, 3.11, 3.12 |
| CI runners | ubuntu-latest (smoke + versions), windows-latest, macos-latest (platform) |
| Report format | Allure HTML (`allure serve allure-results`) |
| Retry policy | `@pytest.mark.flaky(reruns=2, reruns_delay=2)` on all live-HTTP tests |
| SLA threshold | `env_config["thresholds"]["max_response_time"]` seconds |

```bash
# Run all tests for this environment
pytest --env weather -v --alluredir=allure-results

# Run by technique
pytest --env weather -m security -v
pytest --env weather -m performance -v
pytest --env weather -m compatibility -v
```

---

## 6. Acceptance Criteria

| Technique | Pass condition |
|-----------|---------------|
| Positive        | All endpoints return HTTP 200 with `Content-Type: application/json` |
| Schema          | `WeatherValidator().validate()` returns `passed=True` for every endpoint |
| Equivalence     | Representative valid input returns HTTP 200 |
| Boundary        | Edge identifiers return 200/404 — never 500 |
| Negative        | Exact 4xx status asserted (no ranges, no `>= 400`) |
| Error Handling  | Malformed requests produce 4xx, never 5xx |
| Performance     | Response time < YAML threshold on every run (Rule 1 — never hardcoded) |
| Reliability     | All live-API tests decorated `@pytest.mark.flaky(reruns=2)` |
| Security        | HTTPS guard raises `ValueError`; OWASP headers confirmed present |
| Compatibility   | CI gate green on Python 3.9 + 3.12 (Rule 26) |

Zero `STRUCTURAL_FAILURE` or `QUALITY_FAILURE` categories in the eval loop final report.

---

## 7. Risk & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Live API unavailable during CI | Medium | High | `@pytest.mark.flaky(reruns=2)` — classify as `ENV_FAILURE` after 2 retries; do not consume iteration budget (Rule 10) |
| R2 | SLA threshold exceeded consistently | Low | Medium | Classify as `SLA_VIOLATION`; file GitHub issue; mark `xfail(strict=True)` — never raise YAML threshold (Rule 21) |
| R3 | Schema change breaks `WeatherValidator` | Low | High | Schema validation TC (P1) surfaces mismatch immediately; file `QUALITY_FAILURE` bug |
| R4 | OWASP headers removed by API operator | Low | High | Security TC (P1) fails; file bug; `xfail(strict=True)` until resolved |
| R5 | Python version incompatibility | Low | Medium | Compatibility TC (P3) in CI matrix (ubuntu/3.9 + ubuntu/3.12); fails gate before merge (Rule 26) |
