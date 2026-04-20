# Test Plan — `baseline` suite (cross-environment)

**Scope:** All environments defined in `config/environments.yaml`
**Design:** Fully config-driven — parametrized across all environments in YAML.
**Test functions:** 4 parametrized functions → 12 collected nodes (3 environments × 4 checks)

---

## Table of Contents

1. [Scope](#1-scope)
2. [Approach & Techniques](#2-approach--techniques)
3. [Test Cases](#3-test-cases)
4. [Acceptance Criteria](#4-acceptance-criteria)

---

## 1. Scope

### In Scope

The baseline suite provides a minimum-viable sanity check for every environment. It runs
against all environments defined in `config/environments.yaml`. Adding a new environment
automatically adds 4 baseline nodes — no code changes required.

| Check | What is verified |
|-------|-----------------|
| HTTPS enforcement | `HttpClient` raises `ValueError` on plain-HTTP base URL |
| Happy-path 2xx | Primary endpoint returns 200 |
| 404 for unknown path | `/__apitf_nonexistent__` returns 404 |
| Performance / SLA | Primary endpoint responds within YAML `max_response_time` threshold |

**Environments covered (v3.0.0):** `countries`, `weather`, `jsonplaceholder`

### Out of Scope

- Schema validation (covered per-environment in `test_countries.py`, `test_weather.py`, `test_jsonplaceholder.py`)
- Security headers and method enforcement (covered by `test_security.py`)

---

## 2. Approach & Techniques

| Technique | Test function | Collected nodes |
|-----------|---------------|-----------------|
| Security — HTTPS enforcement | `test_https_enforcement` | 3 (one per env) |
| Positive — happy path | `test_primary_endpoint_200` | 3 (one per env) |
| Negative — 404 for unknown path | `test_unknown_path_returns_404` | 3 (one per env) |
| Performance / SLA | `test_primary_endpoint_performance` | 3 (one per env) |

**Total: 12 collected test nodes** (parametrized from YAML at collection time)

---

## 3. Test Cases

| ID | Check | Environment | Input | Expected |
|----|-------|-------------|-------|----------|
| TC-BASE-001 | HTTPS enforcement | countries | `http://` base URL | `ValueError` with `"HTTPS"` in message |
| TC-BASE-002 | HTTPS enforcement | weather | `http://` base URL | `ValueError` with `"HTTPS"` in message |
| TC-BASE-003 | HTTPS enforcement | jsonplaceholder | `http://` base URL | `ValueError` with `"HTTPS"` in message |
| TC-BASE-004 | Happy path 2xx | countries | Primary endpoint | HTTP 200 |
| TC-BASE-005 | Happy path 2xx | weather | Primary endpoint | HTTP 200 |
| TC-BASE-006 | Happy path 2xx | jsonplaceholder | Primary endpoint | HTTP 200 |
| TC-BASE-007 | 404 unknown path | countries | `GET /__apitf_nonexistent__` | HTTP 404 |
| TC-BASE-008 | 404 unknown path | weather | `GET /__apitf_nonexistent__` | HTTP 404 |
| TC-BASE-009 | 404 unknown path | jsonplaceholder | `GET /__apitf_nonexistent__` | HTTP 404 |
| TC-BASE-010 | Performance / SLA | countries | Primary endpoint | `response_time_ms < max_response_time × 1000` |
| TC-BASE-011 | Performance / SLA | weather | Primary endpoint | `response_time_ms < max_response_time × 1000` (xfail BUG-004/005) |
| TC-BASE-012 | Performance / SLA | jsonplaceholder | Primary endpoint | `response_time_ms < max_response_time × 1000` |

**Total: 12 test cases** (3 environments × 4 checks)

---

## 4. Acceptance Criteria

| Technique | Pass condition |
|-----------|---------------|
| HTTPS enforcement | `ValueError` raised for `http://` base URL — no network call made |
| Happy path | Primary endpoint returns HTTP 200 with valid JSON body |
| 404 unknown path | `/__apitf_nonexistent__` returns exactly HTTP 404 |
| Performance | `response_time_ms < env_config["thresholds"]["max_response_time"] * 1000` |

All thresholds are read from `config/environments.yaml` — never hardcoded (Rule 1).
SLA violations are marked `xfail(strict=False, raises=SLA_FAILURE_EXCEPTIONS)` — see BUG-004/005.

```bash
# Run only baseline suite
pytest tests/test_baseline.py -v --alluredir=allure-results

# Run for a specific environment
pytest tests/test_baseline.py -k "countries" -v
```
