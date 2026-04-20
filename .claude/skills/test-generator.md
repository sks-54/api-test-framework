# Skill: Generate Pytest Test File From Endpoint Spec

## Purpose
Given an endpoint spec, generate a complete, runnable pytest test file that
follows all framework conventions (testing-standards.md + code-style.md).

## Modes of Operation

**Scaffold mode (this skill's primary use):** Generates a single-endpoint starter file.
- Filename: `tests/test_{ENV_NAME}.py` (single resource) or `tests/test_{ENV_NAME}_{resource_name}.py` (parallel pipeline, one resource group)
- Produces exactly **5 tests**: positive, performance, schema, security (HTTPS), negative (404)

**Full-environment mode (shipped reference implementations):** The 5 reference test files
(`test_countries.py`, `test_weather.py`, `test_jsonplaceholder.py`, `test_security.py`,
`test_baseline.py`) each cover all 10 testing techniques across multiple endpoints. They
were evolved through the eval_loop and parallel pipeline — they are not single scaffold-mode
outputs.

When generating tests for a brand-new API, start with scaffold mode (this skill), then
expand via the eval_loop to reach full-environment coverage.

---

## Invocation Inputs (all required)
```
ENDPOINT_URL:     <full base URL, e.g. https://restcountries.com/v3.1>
ENDPOINT_PATH:    <path, e.g. /name/{name}>
HTTP_METHOD:      <GET | POST | PUT | DELETE>
RESPONSE_FIELDS:  <comma-separated, e.g. name,capital,population>
ENV_NAME:         <e.g. countries | weather>
VALIDATOR_CLASS:  <e.g. CountriesValidator>
DATA_FILE:        <e.g. test_data/cities.json>
```

## Prompt Template

```
Generate a complete pytest test file for this endpoint:

  Base URL:        {ENDPOINT_URL}
  Path:            {ENDPOINT_PATH}
  Method:          {HTTP_METHOD}
  Response fields: {RESPONSE_FIELDS}
  Environment:     {ENV_NAME}
  Validator:       {VALIDATOR_CLASS}
  Data file:       {DATA_FILE}

### Requirements

1. Filename: tests/test_{ENV_NAME}.py

2. pytestmark = [pytest.mark.{ENV_NAME}, allure.suite("{ENV_NAME}")]

3. Load test data from {DATA_FILE} using pathlib.Path at module level.

4. Generate exactly these 5 tests:
   a. TC-001: test_{ENV_NAME}_positive_baseline — valid input, assert status 200
   b. TC-002: test_{ENV_NAME}_performance — assert response_time_ms < env_config threshold
   c. TC-003: test_{ENV_NAME}_schema — response passes {VALIDATOR_CLASS} contract
   d. TC-004: test_{ENV_NAME}_https_enforced — HttpClient rejects http:// base URL
   e. TC-005: test_{ENV_NAME}_not_found — unknown path returns 4xx

5. Rules (non-negotiable):
   - Full type hints including `-> None` return types
   - Use HttpClient exclusively — never import requests
   - pathlib.Path for all file I/O
   - No print() — use allure.attach or logger
   - Catch only specific exceptions
   - assert result.passed, result.errors pattern for validators
   - All thresholds from env_config — never hardcoded numbers
   - @pytest.mark.flaky(reruns=2, reruns_delay=2) on every live-API test (Testing Standard 10)
   - TC-004 has no flaky marker (no socket opened — raises ValueError before HTTP)

Emit only the Python source file. No prose.
```
