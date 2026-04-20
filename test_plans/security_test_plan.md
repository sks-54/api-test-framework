# Test Plan — `security` suite (cross-environment)

**Scope:** All environments defined in `config/environments.yaml`
**Base URL:** All environments with `base_url` defined in YAML
**Design:** Fully config-driven — violations declared in YAML `known_violations` blocks;
parametrization auto-generates test nodes at collection time.
**Test functions:** 4 parametrized functions → 24 collected nodes (across countries + weather)

---

## Table of Contents

1. [Scope](#1-scope)
2. [Approach & Techniques](#2-approach--techniques)
3. [Test Cases](#3-test-cases)
4. [Acceptance Criteria](#4-acceptance-criteria)

---

## 1. Scope

### In Scope

This suite applies cross-environment security checks. Adding a new environment to
`config/environments.yaml` with a `security` block automatically extends this suite —
no code changes required.

| Category | What is tested |
|----------|---------------|
| RFC 7231 method enforcement | POST, PUT, DELETE, PATCH on read-only endpoints → 405 |
| Content negotiation | `Accept: application/xml` → 406 |
| OWASP security headers | `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` |
| OWASP injection safety | SQL injection, path traversal, XSS, null byte, CRLF, command injection |

### Out of Scope

- Authentication and authorization (no API key / OAuth flows in this suite)
- TLS certificate validity beyond HTTPS enforcement in `HttpClient`
- Rate limiting / DoS — single request per test

---

## 2. Approach & Techniques

| Technique | Test function | Collected nodes |
|-----------|---------------|-----------------|
| Negative — RFC 7231 method enforcement | `test_method_not_allowed` | 8 (countries/weather × POST/DELETE/PUT/PATCH) |
| Negative — content negotiation | `test_content_negotiation_406` | 2 (countries/weather) |
| Security — OWASP headers | `test_security_headers_present` | 2 (countries/weather) |
| Security — OWASP injection | `test_injection_safe` | 12 (countries/weather × 6 attack vectors) |

**Total: 24 collected test nodes** (parametrized from YAML at collection time)

---

## 3. Test Cases

### 3.1 Method Enforcement (`test_method_not_allowed`)

Parametrized via `known_violations` in YAML. Known violations marked `xfail(strict=True)`.

| ID | Method | Environment | Expected | Known violation? |
|----|--------|-------------|----------|-----------------|
| TC-SEC-001 | POST | countries | 405 | — |
| TC-SEC-002 | DELETE | countries | 405 | — |
| TC-SEC-003 | PUT | countries | 405 | — |
| TC-SEC-004 | PATCH | countries | 405 | — |
| TC-SEC-005 | POST | weather | 405 | BUG-006 (returns 415) — xfail |
| TC-SEC-006 | DELETE | weather | 405 | BUG-009 (returns 404) — xfail |
| TC-SEC-007 | PUT | weather | 405 | BUG-011 (returns 404) — xfail |
| TC-SEC-008 | PATCH | weather | 405 | BUG-012 (returns 404) — xfail |

### 3.2 Content Negotiation (`test_content_negotiation_406`)

| ID | Environment | Header sent | Expected | Known violation? |
|----|-------------|-------------|----------|-----------------|
| TC-SEC-009 | countries | `Accept: application/xml` | 406 | — |
| TC-SEC-010 | weather | `Accept: application/xml` | 406 | BUG-010 (returns 200) — xfail |

### 3.3 Security Headers (`test_security_headers_present`)

| ID | Environment | Headers checked | Expected | Known violation? |
|----|-------------|-----------------|----------|-----------------|
| TC-SEC-011 | countries | HSTS, X-Content-Type-Options, X-Frame-Options | All present | — |
| TC-SEC-012 | weather | HSTS, X-Content-Type-Options, X-Frame-Options | All present | BUG-008 — xfail |

### 3.4 Injection Safety (`test_injection_safe`)

| ID | Environment | Attack vector | Expected |
|----|-------------|---------------|----------|
| TC-SEC-013 | countries | SQL injection | 4xx or 200 with safe response (no 500) |
| TC-SEC-014 | countries | Path traversal | 4xx or 200 with safe response |
| TC-SEC-015 | countries | XSS | 4xx or 200 with safe response |
| TC-SEC-016 | countries | Null byte | 4xx or 200 with safe response |
| TC-SEC-017 | countries | CRLF injection | 4xx or 200 with safe response |
| TC-SEC-018 | countries | Command injection | 4xx or 200 with safe response |
| TC-SEC-019 | weather | SQL injection | 4xx or 200 with safe response |
| TC-SEC-020 | weather | Path traversal | 4xx or 200 with safe response |
| TC-SEC-021 | weather | XSS | 4xx or 200 with safe response |
| TC-SEC-022 | weather | Null byte | 4xx or 200 with safe response |
| TC-SEC-023 | weather | CRLF injection | 4xx or 200 with safe response |
| TC-SEC-024 | weather | Command injection | 4xx or 200 with safe response |

---

## 4. Acceptance Criteria

| Technique | Pass condition |
|-----------|---------------|
| Method enforcement | Write methods return 405 (or xfail if known YAML violation) |
| Content negotiation | `Accept: application/xml` returns 406 (or xfail if known) |
| Security headers | All 3 OWASP headers present in response |
| Injection safety | No 5xx response on any OWASP attack vector |

Known violations are declared in `config/environments.yaml` → `known_violations` block.
Adding a new violation requires only a YAML edit — no test file changes.

```bash
# Run only security suite
pytest tests/test_security.py -v --alluredir=allure-results
```
