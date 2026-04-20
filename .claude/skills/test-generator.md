# Skill: Generate Pytest Test File From Endpoint Spec

## Purpose
Given an endpoint spec, generate a complete, runnable pytest test file that
follows all framework conventions (testing-standards.md + code-style.md).

## Modes of Operation

**Scaffold mode (this skill's primary use):** Generates a single-endpoint starter file.
- Filename: `tests/test_{ENV_NAME}_{endpoint_slug}.py` (scaffold mode — multi-endpoint files use `tests/test_{ENV_NAME}.py`)
- Produces exactly 4 tests: positive, negative, boundary, performance

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
VALIDATOR_CLASS:  <e.g. CountryValidator>
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

1. Filename: tests/test_{ENV_NAME}_{endpoint_slug}.py

2. pytestmark = [pytest.mark.{ENV_NAME}, allure.suite("{ENV_NAME}")]

3. Load test data from {DATA_FILE} using pathlib.Path at module level.

4. Generate exactly these 4 tests:
   a. test_{endpoint_slug}_positive — valid input, assert status 200 + schema valid
   b. test_{endpoint_slug}_negative — invalid input, assert specific 4xx status code
   c. test_{endpoint_slug}_boundary — edge case, document which boundary and why
   d. test_{endpoint_slug}_performance — assert response_time_ms < env_config threshold

5. Rules (non-negotiable):
   - Full type hints including -> None return types
   - Use HttpClient exclusively — never import requests
   - pathlib.Path for all file I/O
   - No print() — use allure.attach or logger
   - Catch only specific exceptions
   - assert result.passed, result.errors pattern for validators
   - All thresholds from env_config — never hardcoded numbers

Emit only the Python source file. No prose.
```
