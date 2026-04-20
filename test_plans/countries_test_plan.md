# Test Plan — `countries` environment

**Base URL:** `https://restcountries.com/v3.1`
**Probe path:** `/name/germany`
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

| Method | Path | Sampled response fields |
|--------|------|-------------------------|
| `GET` | `/region/europe` | — |
| `GET` | `/name/germany` | — |
| `GET` | `/all?fields=name,population` | — |

**All sampled fields:** `tld`, `cca2`, `ccn3`, `cca3`, `cioc`, `independent`, `status`, `unMember`, `idd`, `capital`

### Out of Scope

- Write operations (POST / PUT / PATCH / DELETE) unless the spec requires them
- Authentication flows (API keys, OAuth) — covered by the security technique only at the HTTP layer
- Third-party downstream systems beyond `https://restcountries.com/v3.1`
- Load / stress testing (> 1 concurrent request)

---

## 2. Approach & Techniques

| Technique | Priority | TC count | Rationale |
|-----------|----------|----------|-----------|
| Positive (happy path)      | P1 | 1 per endpoint | Valid request → HTTP 200 + JSON |
| Schema validation          | P1 | 1 per endpoint | `CountriesValidator().validate()` passes |
| Equivalence partitioning   | P2 | 1 per endpoint | Representative valid input → 200 |
| Boundary value analysis    | P2 | 2 per endpoint | Min/max identifier edge cases |
| Negative / error paths     | P1 | 2 fixed        | Unknown path 404, bad params 400 |
| Error handling             | P2 | 1 fixed        | Malformed input → 4xx, not 5xx |
| Performance / SLA          | P1 | 1 fixed        | `/name/germany` < `max_response_time` (YAML) |
| Reliability                | P2 | 1 fixed        | `@pytest.mark.flaky(reruns=2)` |
| Security                   | P1 | 2 fixed        | HTTPS enforcement + OWASP headers |
| Compatibility              | P3 | 1 fixed        | Python 3.9 + 3.12 matrix |

---

## 3. Test Cases

### countries API Test Cases

| ID | Endpoint | Technique | Description | Input | Expected | Priority |
|----|----------|-----------|-------------|-------|----------|----------|
| TC-COU-001 | `GET /region/europe` | Positive | Valid request returns 200 and JSON body | Standard params | HTTP 200, `Content-Type: application/json` | P1 |
| TC-COU-002 | `GET /region/europe` | Schema | Response fields _(sampled)_ present and typed | Valid request | `CountriesValidator().validate()` passes | P1 |
| TC-COU-003 | `GET /region/europe` | Equivalence | Representative valid input class | Nominal params | HTTP 200 | P2 |
| TC-COU-004 | `GET /region/europe` | Boundary | Minimum identifier value | edge-case id=1 or equivalent | HTTP 200 or 404, not 500 | P2 |
| TC-COU-005 | `GET /region/europe` | Boundary | Empty / maximum identifier | `''` or out-of-range id | HTTP 4xx, not 500 | P2 |
| TC-COU-006 | `GET /name/germany` | Positive | Valid request returns 200 and JSON body | Standard params | HTTP 200, `Content-Type: application/json` | P1 |
| TC-COU-007 | `GET /name/germany` | Schema | Response fields _(sampled)_ present and typed | Valid request | `CountriesValidator().validate()` passes | P1 |
| TC-COU-008 | `GET /name/germany` | Equivalence | Representative valid input class | Nominal params | HTTP 200 | P2 |
| TC-COU-009 | `GET /name/germany` | Boundary | Minimum identifier value | edge-case id=1 or equivalent | HTTP 200 or 404, not 500 | P2 |
| TC-COU-010 | `GET /name/germany` | Boundary | Empty / maximum identifier | `''` or out-of-range id | HTTP 4xx, not 500 | P2 |
| TC-COU-011 | `GET /all?fields=name,population` | Positive | Valid request returns 200 and JSON body | Standard params | HTTP 200, `Content-Type: application/json` | P1 |
| TC-COU-012 | `GET /all?fields=name,population` | Schema | Response fields _(sampled)_ present and typed | Valid request | `CountriesValidator().validate()` passes | P1 |
| TC-COU-013 | `GET /all?fields=name,population` | Equivalence | Representative valid input class | Nominal params | HTTP 200 | P2 |
| TC-COU-014 | `GET /all?fields=name,population` | Boundary | Minimum identifier value | edge-case id=1 or equivalent | HTTP 200 or 404, not 500 | P2 |
| TC-COU-015 | `GET /all?fields=name,population` | Boundary | Empty / maximum identifier | `''` or out-of-range id | HTTP 4xx, not 500 | P2 |
| TC-COU-016 | `GET /__apitf_nonexistent__` | Negative | Unknown path returns 404 | Invalid path | HTTP 404 exactly | P1 |
| TC-COU-017 | `GET /name/germany` | Negative | Missing required params returns 400 | Omit required param | HTTP 400 or 422 | P1 |
| TC-COU-018 | `GET /name/germany` | Error Handling | Malformed request does not trigger 5xx | Malformed query | HTTP 4xx, not 5xx | P2 |
| TC-COU-019 | `GET /name/germany` | Performance | Response within SLA threshold | Standard params | < `max_response_time` × 1000 ms (YAML, never hardcoded) | P1 |
| TC-COU-020 | `GET /name/germany` | Reliability | Transient failure retried and recovered | Network blip | Pass on retry ≤ 2; `@pytest.mark.flaky(reruns=2)` | P2 |
| TC-COU-021 | `HttpClient('http://...')` | Security | HTTP (not HTTPS) is rejected at construction | Plain-HTTP base URL | `ValueError` raised, message contains `'HTTPS'` | P1 |
| TC-COU-022 | `GET /name/germany` | Security | OWASP security headers present in response | Standard request | `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` present | P1 |
| TC-COU-023 | _(matrix)_ | Compatibility | Framework runs cleanly on Python 3.9 and 3.12 | CI matrix | All tests pass on ubuntu/3.9 + ubuntu/3.12 (Rule 26) | P3 _(CI only — not a test function)_ |

**Total: 22 test functions** (TC-COU-023 is covered by the CI matrix, not a standalone pytest function)

---

## 4. Test Data & Configuration

- **Thresholds:** all numeric limits read from `config/environments.yaml` via `env_config` fixture — never hardcoded (Rule 1)
- **Coordinates / identifiers:** loaded from `test_data/` JSON files — never inline literals (Testing Standard 1)
- **Base URL:** `https://restcountries.com/v3.1` (single source: `config/environments.yaml`)
- **Probe path:** `/name/germany`
- **Sampled fields:** ``tld`, `cca2`, `ccn3`, `cca3`, `cioc`, `independent`, `status`, `unMember`, `idd`, `capital``

---

## 5. Environment & Infrastructure

| Item | Value |
|------|-------|
| Target API | `https://restcountries.com/v3.1` |
| Python versions | 3.9, 3.11, 3.12 |
| CI runners | ubuntu-latest (smoke + versions), windows-latest, macos-latest (platform) |
| Report format | Allure HTML (`allure serve allure-results`) |
| Retry policy | `@pytest.mark.flaky(reruns=2, reruns_delay=2)` on all live-HTTP tests |
| SLA threshold | `env_config["thresholds"]["max_response_time"]` seconds |

```bash
# Run all tests for this environment
pytest --env countries -v --alluredir=allure-results

# Run by technique
pytest --env countries -m security -v
pytest --env countries -m performance -v
pytest --env countries -m compatibility -v
```

---

## 6. Acceptance Criteria

| Technique | Pass condition |
|-----------|---------------|
| Positive        | All endpoints return HTTP 200 with `Content-Type: application/json` |
| Schema          | `CountriesValidator().validate()` returns `passed=True` for every endpoint |
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
| R3 | Schema change breaks `CountriesValidator` | Low | High | Schema validation TC (P1) surfaces mismatch immediately; file `QUALITY_FAILURE` bug |
| R4 | OWASP headers removed by API operator | Low | High | Security TC (P1) fails; file bug; `xfail(strict=True)` until resolved |
| R5 | Python version incompatibility | Low | Medium | Compatibility TC (P3) in CI matrix (ubuntu/3.9 + ubuntu/3.12); fails gate before merge (Rule 26) |
