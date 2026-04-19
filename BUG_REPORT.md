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
| **Title** | One-line summary |
| **Steps** | How to reproduce |
| **Expected** | Per spec |
| **Actual** | What the API returns |
| **Data** | Request URL, status code, response snippet |

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
| **Title** | `/alpha/ZZZ999` returns 400 Bad Request instead of 404 Not Found |

**Steps to Reproduce:**
```
pytest tests/test_countries.py::test_invalid_alpha_code_returns_404 -v
# or
curl "https://restcountries.com/v3.1/alpha/ZZZ999"
```

**Expected (per spec):** HTTP 404 — resource not found for invalid alpha code

**Actual:** HTTP 400 Bad Request

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
| **Title** | `/forecast` without required `lat`/`lon` returns 200 instead of 4xx |

**Steps to Reproduce:**
```
pytest tests/test_weather.py::test_forecast_negative_missing_coords -v
# or
curl "https://api.open-meteo.com/v1/forecast"
```

**Expected (per spec):** HTTP 4xx — required parameters `latitude` and `longitude` missing

**Actual:** HTTP 200 with either empty or default data

**Data:**
- Request URL: `https://api.open-meteo.com/v1/forecast`
- Status Code: 200
- Notes: API silently accepts missing required params; should return 400

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
| **Title** | 5 territories return `population=0` violating minimum population contract |

**Steps to Reproduce:**
```
pytest tests/test_countries.py::test_all_population_boundary -v
```

**Expected (per spec):** All countries have `population >= 1`

**Actual:** 5 territories return `population=0`:
- Heard Island and McDonald Islands
- Bouvet Island
- South Georgia and the South Sandwich Islands
- United States Minor Outlying Islands
- British Indian Ocean Territory

**Data:**
- Endpoint: `https://restcountries.com/v3.1/all`
- Notes: These are uninhabited/sparsely populated territories. API returns 0 rather than null/absent. Debatable whether spec covers them — filed for tracking.

---

## Resolved Bugs

_None yet._

---

## SLA Violations

Failures meeting all of: (a) performance assertion fails, (b) reruns=2 all fail, (c) not a transient ENV_FAILURE.

_None filed yet. Transient Open-Meteo timeouts during CI have been ENV_FAILUREs — all resolved with flaky markers._

---

## How to Add a New Bug

1. Run the failing test and confirm it is a QUALITY_FAILURE or SLA_VIOLATION (not ENV_FAILURE)
2. File a GitHub issue: `gh issue create --label bug --title "..." --body "..."`
3. Append a new entry to this file using the format above
4. Add `@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Known API bug #N: ...")` to the test
5. Reference the bug ID in `CLAUDE_LOG.md` Known Bugs table
