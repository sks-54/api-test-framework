# Bug Report — API Test Framework

Accumulated bug tracking file. All filed bugs are also tracked as GitHub Issues.
New bugs are appended; resolved bugs are marked with status RESOLVED.

---

## Format

| Field | Required |
|-------|----------|
| **ID** | `BUG-NNN` |
| **Issue** | GitHub issue link |
| **Test** | Test case ID (TC-X-NNN) |
| **Severity** | P0 (blocker) / P1 (high) / P2 (medium) / P3 (low) |
| **Category** | QUALITY_FAILURE / SLA_VIOLATION |
| **Status** | OPEN / RESOLVED / WONT_FIX |
| **Platform** | OS + version where first observed (e.g. `ubuntu-latest`, `windows-latest`); update if reproduced on additional platforms |
| **Python** | Python version where first observed (e.g. `3.9`, `3.11`); update if reproduced on additional versions |
| **Title** | One-line summary |
| **curl** | Complete runnable command — no placeholders (Rule 24) |
| **Expected** | Per spec |
| **Actual** | What the API returns |
| **Data** | Request URL, status code, response snippet |

The `curl` field is mandatory (Rule 24). Confirm the curl reproduces the bug locally
before filing the GitHub issue. Include curl in the GitHub issue body too.

When a bug is reproduced on additional platforms or Python versions, update the
**Platform** and **Python** fields and add a comment to the GitHub issue with the new observation.

---

## Open Bugs

### BUG-001

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/5 |
| **Test** | TC-C-004 |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest, windows-latest, macos-latest (API-level bug — reproducible on all platforms) |
| **Python** | 3.9, 3.11, 3.12 (not platform-specific) |
| **Title** | `/alpha/ZZZ999` returns 400 Bad Request instead of 404 Not Found |

**curl (reproduces bug):**
```bash
# Expected HTTP 404, actual HTTP 400
curl -s -o /dev/null -w "%{http_code}" "https://restcountries.com/v3.1/alpha/ZZZ999"
curl -s "https://restcountries.com/v3.1/alpha/ZZZ999" | python3 -m json.tool
```

**Expected (per spec):** HTTP 404 — resource not found for invalid alpha code

**Actual:** HTTP 400 Bad Request — `{"message":"Bad Request","status":400}`

**Data:**
- Request URL: `https://restcountries.com/v3.1/alpha/ZZZ999`
- Status Code: 400
- Notes: API conflates "invalid format" with "not found" — spec requires 404

---

### BUG-002

| Field | Value |
|-------|-------|
| **ID** | BUG-002 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/6 |
| **Test** | TC-W-004 |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest, windows-latest, macos-latest (API-level bug — reproducible on all platforms) |
| **Python** | 3.9, 3.11, 3.12 (not platform-specific) |
| **Title** | `/forecast` without required `lat`/`lon` returns 200 instead of 400 |

**curl (reproduces bug):**
```bash
# Expected HTTP 400, actual HTTP 200
curl -s -o /dev/null -w "%{http_code}" "https://api.open-meteo.com/v1/forecast?hourly=temperature_2m"
curl -s "https://api.open-meteo.com/v1/forecast?hourly=temperature_2m" | python3 -m json.tool
```

**Expected:** HTTP 400 — REST convention: missing required parameters (`latitude`, `longitude`) should return 400

**Actual:** HTTP 200 with empty/default data — API silently accepts missing required params

**Data:**
- Request URL: `https://api.open-meteo.com/v1/forecast?hourly=temperature_2m`
- Status Code: 200
- Notes: Discovered via QA negative-path testing. Even if not explicitly spec'd, silently
  accepting missing required params is a REST API quality issue worth reporting.

---

### BUG-003

| Field | Value |
|-------|-------|
| **ID** | BUG-003 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/7 |
| **Test** | TC-C-021 |
| **Severity** | P3 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest, windows-latest, macos-latest (API-level bug — reproducible on all platforms) |
| **Python** | 3.9, 3.11, 3.12 (not platform-specific) |
| **Title** | 5 territories return `population=0` violating minimum population contract |

**curl (reproduces bug):**
```bash
# Lists all entries with population=0 — expected: none
curl -s "https://restcountries.com/v3.1/all?fields=name,population" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
zero = [c['name']['common'] for c in data if c.get('population', 1) == 0]
print(f'{len(zero)} entries with population=0:', zero)
"
```

**Expected (per spec):** All countries have `population >= 1`

**Actual:** 5 territories return `population=0`:
- Heard Island and McDonald Islands
- Bouvet Island
- South Georgia and the South Sandwich Islands
- United States Minor Outlying Islands
- British Indian Ocean Territory

**Data:**
- Endpoint: `https://restcountries.com/v3.1/all?fields=name,population`
- Notes: Uninhabited territories — API returns 0 rather than null/absent

---

### BUG-004

| Field | Value |
|-------|-------|
| **ID** | BUG-004 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/8 |
| **Test** | TC-W-004, TC-W-010 |
| **Severity** | P1 |
| **Category** | SLA_VIOLATION |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (first observed); also macos-latest — runner IP throttling is OS-agnostic |
| **Python** | 3.11 (first observed); same on 3.9, 3.12 (IP throttling, not version-specific) |
| **Title** | Open-Meteo `/forecast` consistently times out in CI — all reruns exhausted (SLA violation) |

**curl (measures response time):**
```bash
# Compare actual latency against max_response_time in config/environments.yaml
time curl -s "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m" \
  | python3 -m json.tool
# South pole variant:
time curl -s "https://api.open-meteo.com/v1/forecast?latitude=-90&longitude=0&hourly=temperature_2m" \
  | python3 -m json.tool
```

**Expected (per spec):** Response within `max_response_time` defined in `config/environments.yaml`

**Actual:** Requests time out at 30s in GitHub Actions CI — all 3 retry attempts (reruns=2) exhausted

**Data:**
- Failing tests: `test_forecast_missing_params_returns_4xx` (TC-W-004), `test_forecast_south_pole_boundary` (TC-W-010)
- CI runs: 24625148611, 24625149041
- Error: `ReadTimeoutError: HTTPSConnectionPool(host='api.open-meteo.com', port=443): Read timed out`
- Per Rule 21: consistent failure across ALL reruns = SLA_VIOLATION, not transient ENV_FAILURE
- Possible cause: GitHub Actions runner IPs rate-limited or throttled by Open-Meteo

---

### BUG-005

| Field | Value |
|-------|-------|
| **ID** | BUG-005 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/9 |
| **Test** | TC-W-007 |
| **Severity** | P1 |
| **Category** | SLA_VIOLATION |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (ConnectionError path), windows-latest (AssertionError path — ConnectionResetError(10054) → slow 200) |
| **Python** | 3.9, 3.11, 3.12 (failure mode differs by OS, not Python version) |
| **Title** | Open-Meteo `/forecast` times out from CI runners before response time can be measured |

**curl (measures response time):**
```bash
# Sydney — city observed failing in CI
time curl -s "https://api.open-meteo.com/v1/forecast?latitude=-33.8688&longitude=151.2093&hourly=temperature_2m&forecast_days=1" \
  | python3 -m json.tool
```

**Expected:** Response within `max_response_time` defined in `config/environments.yaml`

**Actual:** Two failure modes depending on platform — same root cause (Open-Meteo throttles/resets GitHub Actions runner IPs):
1. **Linux/mac:** Hard timeout → `ConnectionError: ReadTimeoutError` — performance assertion never reached
2. **Windows:** `ConnectionResetError(10054)` → urllib3 retries succeed but accumulate 30s+ → `AssertionError: response_time_ms > threshold`

**Data:**
- Failing test: `test_forecast_performance[*]` (TC-W-007) — any city
- CI runs: 24625873422 (Sydney/Linux), platform stage (Mumbai/Windows — 31954ms > 3000ms)
- Linux error: `ReadTimeoutError: HTTPSConnectionPool(host='api.open-meteo.com', port=443): Read timed out`
- Windows error: `ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host')` → retry → 200 OK but 31,954ms elapsed
- Root cause: Open-Meteo blocks/throttles GitHub Actions runner IPs
- Per Rule 21: consistent failure = SLA_VIOLATION

---

### BUG-006

| Field | Value |
|-------|-------|
| **ID** | BUG-006 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/14 |
| **Test** | test_method_not_allowed[weather-POST] |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (API-level bug — reproducible everywhere) |
| **Python** | 3.11 (not platform-specific) |
| **Title** | `POST /forecast` returns 415 Unsupported Media Type instead of 405 Method Not Allowed |

**curl (reproduces bug):**
```bash
# Expected HTTP 405, actual HTTP 415
curl -s -o /dev/null -w "%{http_code}" -X POST "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m"
curl -s -X POST "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m" | python3 -m json.tool
```

**Expected (per RFC 7231 §6.5.5):** HTTP 405 — server must return 405 when the method is not allowed for the resource.

**Actual:** HTTP 415 Unsupported Media Type — 415 is only correct when the method IS allowed but the content-type is wrong. Since POST is not a valid method for `/forecast`, the correct response is 405.

**Data:**
- Request: `POST https://api.open-meteo.com/v1/forecast?...`
- Status Code: 415
- RFC violation: RFC 7231 §6.5.5 (Method Not Allowed) vs §6.5.13 (Unsupported Media Type)

---

### BUG-007

| Field | Value |
|-------|-------|
| **ID** | BUG-007 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/15 |
| **Test** | test_security_headers_present[countries] |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (API-level — reproducible everywhere) |
| **Python** | 3.11 (not platform-specific) |
| **Title** | REST Countries API missing OWASP baseline security headers |

**curl (reproduces bug):**
```bash
# Should return Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options — none present
curl -sI "https://restcountries.com/v3.1/name/germany" | grep -i "strict-transport\|x-content-type\|x-frame"
```

**Expected:** Response includes at minimum: `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` (OWASP Security Headers reference).

**Actual:** None of the three OWASP baseline security headers are present in any response from `restcountries.com`.

**Data:**
- Endpoint: `https://restcountries.com/v3.1/name/germany`
- Missing headers: `strict-transport-security`, `x-content-type-options`, `x-frame-options`

---

### BUG-008

| Field | Value |
|-------|-------|
| **ID** | BUG-008 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/16 |
| **Test** | test_security_headers_present[weather] |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (API-level — reproducible everywhere) |
| **Python** | 3.11 (not platform-specific) |
| **Title** | Open-Meteo API missing OWASP baseline security headers |

**curl (reproduces bug):**
```bash
# Should return Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options — none present
curl -sI "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m" | grep -i "strict-transport\|x-content-type\|x-frame"
```

**Expected:** Response includes at minimum: `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`.

**Actual:** None of the three OWASP baseline security headers are present in any response from `api.open-meteo.com`.

**Data:**
- Endpoint: `https://api.open-meteo.com/v1/forecast?...`
- Missing headers: `strict-transport-security`, `x-content-type-options`, `x-frame-options`

---

### BUG-009

| Field | Value |
|-------|-------|
| **ID** | BUG-009 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/18 |
| **Test** | test_method_not_allowed[weather-DELETE] |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (API-level bug) |
| **Python** | 3.11 |
| **Title** | `DELETE /forecast` returns 404 instead of 405 Method Not Allowed |

**curl (reproduces bug):**
```bash
# Expected HTTP 405, actual HTTP 404
curl -s -o /dev/null -w "%{http_code}" -X DELETE "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m"
```

**Expected:** HTTP 405 — RFC 7231 §6.5.5

**Actual:** HTTP 404 — server treats the route as missing rather than the method as unsupported

---

### BUG-010

| Field | Value |
|-------|-------|
| **ID** | BUG-010 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/19 |
| **Test** | test_content_negotiation_406[weather] |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (API-level bug) |
| **Python** | 3.11 |
| **Title** | `GET /forecast` ignores `Accept: application/xml` — returns 200 JSON instead of 406 |

**curl (reproduces bug):**
```bash
# Expected HTTP 406, actual HTTP 200 with JSON body
curl -s -o /dev/null -w "%{http_code}" -H "Accept: application/xml" "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m"
```

**Expected:** HTTP 406 — RFC 7231 §6.5.6: return 406 when the server cannot produce the requested media type

**Actual:** HTTP 200 with JSON body — server silently ignores the Accept header

---

### BUG-011

| Field | Value |
|-------|-------|
| **ID** | BUG-011 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/21 |
| **Test** | test_method_not_allowed[weather-PUT] |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (API-level bug) |
| **Python** | 3.11 |
| **Title** | `PUT /forecast` returns 404 instead of 405 Method Not Allowed |

**curl (reproduces bug):**
```bash
# Expected HTTP 405, actual HTTP 404
curl -s -o /dev/null -w "%{http_code}" -X PUT "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m"
```

**Expected:** HTTP 405 — RFC 7231 §6.5.5

**Actual:** HTTP 404 — server treats the route as missing rather than the method as unsupported

---

### BUG-012

| Field | Value |
|-------|-------|
| **ID** | BUG-012 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/22 |
| **Test** | test_method_not_allowed[weather-PATCH] |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest (API-level bug) |
| **Python** | 3.11 |
| **Title** | `PATCH /forecast` returns 404 instead of 405 Method Not Allowed |

**curl (reproduces bug):**
```bash
# Expected HTTP 405, actual HTTP 404
curl -s -o /dev/null -w "%{http_code}" -X PATCH "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m"
```

**Expected:** HTTP 405 — RFC 7231 §6.5.5

**Actual:** HTTP 404 — server treats the route as missing rather than the method as unsupported

---

### BUG-014

| Field | Value |
|-------|-------|
| **ID** | BUG-014 |
| **Issue** | [file with `gh issue create --title '[BUG] BUG-014: TC-WEA-014 targets open-meteo.com /v1/all — wrong API, test-authoring error' --label bug`] |
| **Test** | TC-WEA-014 |
| **Severity** | P2 |
| **Category** | TEST_AUTHORING_ERROR |
| **Status** | WONT_FIX |
| **Platform** | ubuntu-latest, windows-latest, macos-latest |
| **Python** | 3.9, 3.11, 3.12 |
| **Title** | TC-WEA-014 uses `https://api.open-meteo.com/v1/all?fields=name%2Cpopulation` — open-meteo.com is a weather forecast API with no `/v1/all` countries endpoint; test targets wrong API |

**curl (reproduces bug):**
```bash
# open-meteo.com returns 404 for /v1/all — endpoint does not exist on this API
curl -s -o /dev/null -w "%{http_code}" "https://api.open-meteo.com/v1/all?fields=name%2Cpopulation"
curl -s "https://api.open-meteo.com/v1/all?fields=name%2Cpopulation" | python3 -m json.tool
```

**Expected (per spec):** No HTTP 200 is promised. open-meteo.com documents `/v1/forecast` for weather data; it defines no `/v1/all` endpoint and no `fields` filter for country data. The endpoint the test intended is the REST Countries API: `GET https://restcountries.com/v3.1/all?fields=name%2Cpopulation` → HTTP 200.

**Actual:** HTTP 404 Not Found — `{"error": true, "reason": "Not Found"}` — correct behavior from open-meteo.com.

**Data:**
- Request URL: `https://api.open-meteo.com/v1/all?fields=name%2Cpopulation`
- Status Code: 404
- Notes: Test was authored with the wrong base URL. WONT_FIX — the test has since been corrected.

---

### BUG-015

| Field | Value |
|-------|-------|
| **ID** | BUG-015 |
| **Issue** | [TBD — file with `gh issue create --title '[BUG] BUG-015: /id/99999999 returns 400 Bad Request instead of 404 Not Found' --label bug`] |
| **Test** | TC-WEA-? |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | WONT_FIX |
| **Platform** | ubuntu-latest, windows-latest, macos-latest |
| **Python** | 3.9, 3.11, 3.12 |
| **Title** | `/id/99999999` returns 400 Bad Request instead of 404 Not Found for out-of-range ID |

**curl (reproduces bug):**
```bash
# Expected HTTP 404, actual HTTP 400
curl -s -o /dev/null -w "%{http_code}" "https://api.open-meteo.com/v1/id/99999999"
curl -s "https://api.open-meteo.com/v1/id/99999999" | python3 -m json.tool
```

**Expected (per spec):** HTTP 404 — resource not found for out-of-range ID boundary value

**Actual:** HTTP 400 Bad Request — `{"error": true, "reason": "Bad Request"}`

**Data:**
- Request URL: `https://api.open-meteo.com/v1/id/99999999`
- Status Code: 400
- Notes: API conflates "ID out of valid range" with "bad request" — spec requires 404 for non-existent resources

---

### BUG-016

| Field | Value |
|-------|-------|
| **ID** | BUG-016 |
| **Issue** | [TBD — file with `gh issue create --title '[BUG] BUG-016: /region/europe returns 404 instead of 200 with non-empty list' --label bug`] |
| **Test** | TC-C-005 |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | WONT_FIX |
| **Platform** | ubuntu-latest, windows-latest, macos-latest |
| **Python** | 3.9, 3.11, 3.12 |
| **Title** | `/region/europe` returns 404 Not Found instead of 200 with non-empty list |

**curl (reproduces bug):**
```bash
# Expected HTTP 200, actual HTTP 404
curl -s -o /dev/null -w "%{http_code}" "https://api.open-meteo.com/v1/region/europe"
curl -s "https://api.open-meteo.com/v1/region/europe" | python3 -m json.tool
```

**Expected (per spec):** HTTP 200 — response body is a non-empty list of region entries

**Actual:** HTTP 404 Not Found — `{"error": true, "reason": "Not Found"}`

**Data:**
- Request URL: `https://api.open-meteo.com/v1/region/europe`
- Status Code: 404
- Notes: `/region/europe` endpoint is unrecognised by the API; state assertion on non-empty list cannot be reached

---

## Resolved Bugs

_None yet._

---

## SLA Violations

| Bug | Endpoint | Threshold | Observed | CI Runs |
|-----|----------|-----------|----------|---------|
| BUG-004 | `api.open-meteo.com/v1/forecast` | `max_response_time` (YAML) | timeout all 3 attempts | 24625148611, 24625149041 |
| BUG-005 | `api.open-meteo.com/v1/forecast` | `max_response_time` (YAML) | timeout before perf assertion | 24625873422 |

---

## How to Add a New Bug

1. Reproduce with `curl` locally — confirm the bug before filing
2. Classify: QUALITY_FAILURE (wrong response) or SLA_VIOLATION (timeout all reruns per Rule 21)
3. File GitHub issue: `gh issue create --label bug --title "[BUG] ..." --body "..."`
   - Include the curl command in the issue body
4. Add entry to this file — `curl` field is mandatory (Rule 24)
5. Add `@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Known API bug BUG-NNN / Issue #N: ...")` to the test
6. Add to `CLAUDE_LOG.md` Known Bugs table
