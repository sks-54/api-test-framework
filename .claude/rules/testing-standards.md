# Testing Standards — Multi-Environment API Test Framework

These rules apply exclusively to this framework. Generic pytest conventions are
secondary to anything stated here.

---

## 10. Every Live-API Test Must Have `@pytest.mark.flaky(reruns=2, reruns_delay=2)`

Any test function that makes a live HTTP call (uses `HttpClient`) must be decorated
with `@pytest.mark.flaky(reruns=2, reruns_delay=2)` **at authoring time**, not after the
first CI failure.

```python
# CORRECT — retry declared upfront
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_germany_schema(env_config):
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/name/germany")
    ...

# FORBIDDEN — no retry; a single CI runner fluke files a premature bug
@pytest.mark.equivalence
def test_germany_schema(env_config):
    ...
```

**Exceptions** (no live HTTP call, so no retry needed):
- Tests that only assert `pytest.raises(ValueError)` on `HttpClient` construction
  (HTTPS enforcement tests — they never connect to a remote server)

**Interaction with xfail:** `pytest-rerunfailures` does not retry tests whose outcome
is `xfail` — the outcome is already "expected failure", not "failed". Tests marked
`@pytest.mark.xfail` are therefore exempt from this rule because the xfail marker already
provides a stable CI outcome without retrying.

**Rationale:** A transient runner IP being throttled is indistinguishable from a real bug
if the test runs only once. Three attempts (1 initial + 2 reruns) provide enough evidence
to distinguish an ENV_FAILURE (passes on retry) from an SLA_VIOLATION (fails all three).
Filing a bug after one failure wastes a GitHub issue on noise.

**Enforcement:** `scripts/verify_bug_markers.py` scans all `test_*.py` files and exits
non-zero if any test using `HttpClient` lacks `@pytest.mark.flaky` and lacks
`@pytest.mark.xfail`. The git pre-push hook blocks the push.

---

## 1. Parametrize From JSON Files — Never Inline Test Data

All `@pytest.mark.parametrize` calls must load data from `test_data/`. Inline
literals in parametrize decorators are forbidden.

```python
# CORRECT
import json
from pathlib import Path
CITIES = json.loads((Path(__file__).parent.parent / "test_data" / "cities.json").read_text())

@pytest.mark.parametrize("city", CITIES)
def test_weather_forecast_positive(city, env_config): ...

# FORBIDDEN
@pytest.mark.parametrize("city", [{"name": "Berlin", "latitude": 52.52}])
```

## 2. Every Endpoint Needs a Schema Validation Test

Every endpoint covered by this framework requires at least one test that
instantiates the appropriate `BaseValidator` subclass and asserts `.passed`.

```python
from src.validators.country_validator import CountryValidator

def test_germany_schema(env_config):
    result = CountryValidator().validate(response.json_body[0])
    assert result.passed, result.errors
```

Ad-hoc `assert "field" in response` checks are not acceptable substitutes.

## 3. Response Time Assertions Must Use `env_config` Threshold

Never hardcode a numeric time value. Always read from `env_config`.

```python
# CORRECT
assert resp.response_time_ms < env_config["thresholds"]["max_response_time"] * 1000

# FORBIDDEN
assert resp.response_time_ms < 2000  # hardcoded
```

## 4. Test ID Naming Convention

```
test_<endpoint>_<technique>
```

Examples: `test_europe_region_count`, `test_germany_schema`, `test_all_population_boundary`, `test_forecast_negative_invalid_coords`

## 5. Weather Test Data — `test_data/cities.json` Is the Sole Source

All weather tests must source lat/lon from `test_data/cities.json`. No other
file, fixture value, or inline literal may supply coordinates.

## 6. Cross-Reference Tests Must Derive Data From a Prior API Call

When a test correlates two endpoints, the linking value must come from a live
API response — never from a hardcoded assertion.

```python
# CORRECT
country = http_client.get("/name/germany").json_body[0]
region = country["region"]
results = http_client.get(f"/region/{region}").json_body
assert any(c["name"]["common"] == "Germany" for c in results)

# FORBIDDEN
assert region == "Europe"  # hardcoded geographic fact
```

## 7. `@allure.suite` With Environment Name on Every Test File

Every test file must declare `pytestmark` with `allure.suite` using the
environment name and the appropriate `pytest.mark`.

```python
pytestmark = [pytest.mark.countries, allure.suite("countries")]
```

## 8. Negative Tests Must Assert the Specific HTTP Status Code

```python
# CORRECT
assert response.status_code == 404

# FORBIDDEN
assert response.status_code != 200
assert not response.ok
```

## 9. Skip Reasons Must Explain Why, Not Just What

Every `pytest.mark.skip` and `pytest.mark.skipif` reason must answer:
- **Why** this test doesn't run in this context
- **How** to run it if you want it

A reason that only names what is being skipped gives no actionable information to
someone reading the output cold.

```python
# CORRECT — answers why and how to run it
pytest.mark.skip(
    reason=(
        "--env weather selected: countries tests are environment-scoped and only run "
        "under --env countries. Run `pytest` (no --env flag) to execute all environments."
    )
)

# FORBIDDEN — says what, not why
pytest.mark.skip(reason="--env weather: skipping countries tests")
```

This applies to:
- `conftest.py` skip logic (`pytest_collection_modifyitems`)
- Inline `@pytest.mark.skip` decorators in test files
- `@pytest.mark.skipif` conditions

The test output is often the first thing a new engineer reads when onboarding.
A skip reason that explains context saves a debugging session.
