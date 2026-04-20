# Bug Lifecycle

From test failure to tracked GitHub issue to eventual resolution.

---

## Failure Categorization (Always First)

Before investigating any CI failure, categorize it:

| Category | Trigger | Action |
|----------|---------|--------|
| `ENV_FAILURE` | `ConnectionError`, `Timeout`, transient 5xx | Retry up to 2× (flaky marker). If all retries fail → `SLA_VIOLATION` |
| `QUALITY_FAILURE` | Wrong status code, schema mismatch, value out of range | File GitHub issue → `xfail(strict=True)` → push |
| `STRUCTURAL_FAILURE` | `ImportError`, `FixtureError`, `SyntaxError` | Fix framework code → push |
| `SLA_VIOLATION` | Consistent timeout across all reruns | File bug → `xfail(strict=False, raises=SLA_FAILURE_EXCEPTIONS)` → push |

---

## Step-by-Step: QUALITY_FAILURE

### 1. Look at the bug report

```bash
ls bugs/                            # one file per failure
cat bugs/<timestamp>_<test>.md      # URL · status · time · expected · actual
```

### 2. Reproduce with curl

Every bug report includes a `curl` command. Run it to confirm the failure is in the API, not the test:

```bash
curl -s "https://restcountries.com/v3.1/alpha/ZZZ999" | python3 -m json.tool
# Expected: HTTP 404 Not Found
# Actual: HTTP 400 Bad Request  ← API bug confirmed
```

### 3. Confirm: API is wrong, test is correct

The test asserts the spec contract. If the API deviates, the test is correct. Never widen the assertion.

```python
# Correct — test stays strict
assert resp.status_code == 404

# FORBIDDEN — hides the bug
assert resp.status_code in (400, 404)
```

### 4. File a GitHub issue

```bash
gh issue create \
  --label bug,quality-failure \
  --title "[BUG] TC-C-021: /alpha/ZZZ999 returns 400 instead of 404 (RFC 7231 §6.5.4)" \
  --body "$(cat bugs/<timestamp>_test_invalid_alpha_code_returns_404.md)"
```

### 5. Document in BUG_REPORT.md

Add a block to `BUG_REPORT.md` using the standard format:

```markdown
### BUG-NNN — Title

| Field | Value |
|-------|-------|
| **Status** | OPEN |
| **Category** | QUALITY_FAILURE |
| **Test** | TC-C-021 / test_invalid_alpha_code_returns_404 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/N |
| **Bug ID** | BUG-NNN |

**curl reproduction:**
```bash
# Expected: 404 Not Found
# Actual:   400 Bad Request
curl -s "https://restcountries.com/v3.1/alpha/ZZZ999" | python3 -m json.tool
```

**Steps to Reproduce:** ...  
**Expected:** 404 Not Found  
**Actual:** 400 Bad Request  
```

### 6. Add the xfail marker

```python
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Known API bug BUG-NNN / Issue #N: /alpha/ZZZ999 returns 400 instead of 404 (RFC 7231 §6.5.4)",
)
def test_invalid_alpha_code_returns_404(env_config):
    ...
```

`strict=True` means: if the API fixes the bug, the test flips from `xfail` → `xpass`, alerting you to remove the marker and close the issue.

### 7. Verify and push

```bash
python scripts/verify_bug_markers.py    # must exit 0
python scripts/push.py                  # push + watch CI
```

CI turns green because `xfail` is an expected outcome.

---

## Step-by-Step: SLA_VIOLATION

An SLA violation is a QUALITY_FAILURE where the failure mode is a timeout, not an assertion. The test runs but the API never responds (or responds too slowly) on all retries.

```python
@pytest.mark.xfail(
    strict=False,                        # strict=False because Windows raises AssertionError, Linux raises ConnectionError
    raises=SLA_FAILURE_EXCEPTIONS,       # (AssertionError, requests.exceptions.ConnectionError)
    reason="Known SLA_VIOLATION BUG-004 / Issue #8: Open-Meteo /forecast timeout on CI runners",
)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_forecast_performance(city, env_config): ...
```

Note: `@pytest.mark.flaky` is present but `pytest-rerunfailures` does not retry `xfail` outcomes — the two markers coexist because the test may also surface as a PASS on a fast network.

---

## YAML-Driven xfail (No Code Changes Needed)

For `test_security.py` and `test_baseline.py`, bugs are declared in `environments.yaml` and translated to `pytest.param(..., marks=[xfail])` at collection time:

```yaml
weather:
  security:
    known_violations:
      - type: method
        method: POST
        bug_id: BUG-006
        issue: https://github.com/sks-54/api-test-framework/issues/14
        reason: "POST /forecast returns 415 instead of 405 (RFC 7231 §6.5.5)"
```

No decorator needed in the test file. `verify_bug_markers.py` checks that every open `QUALITY_FAILURE` bug in `BUG_REPORT.md` has a corresponding marker — either a function decorator or a YAML entry.

---

## Resolution

When the API fixes a bug:

1. The test flips from `xfail` → `xpass` in CI output
2. Remove the `xfail` decorator (or YAML `known_violations` entry)
3. Update `BUG_REPORT.md` Status from `OPEN` → `RESOLVED`
4. Close the GitHub issue
5. Run `python scripts/verify_bug_markers.py` — should still exit 0
6. Push
