# Claude Code Skills Reference

Three skills in `.claude/skills/` generate framework-conformant code from a spec document, a JSON response, or an endpoint description. Invoke them in a Claude Code session (run `claude` at the repo root, or open the IDE extension).

---

## How Skills Work

Skills are prompt templates — they run inside Claude Code, not in your shell. Open a Claude Code session, then type the skill name prefixed with `/`:

```
/spec-parser
/validator-generator
/test-generator
```

Claude Code reads the skill file, applies your inputs, and generates the output inline in the session.

---

## `/spec-parser` — Extract endpoints from a spec document

**File:** `.claude/skills/spec-parser.md`

### Invocation

```
/spec-parser SPEC_PATH=specs/myapi_spec.pdf
```

### What It Does

1. Calls `SpecParserRegistry.parse(Path(SPEC_PATH))` with registered parsers
2. Prints every extracted `EndpointSpec` object
3. Updates `config/environments.yaml` with a new environment block (`base_url`, `probe_path`, and default `thresholds.max_response_time: 5`)
4. Prints the exact `/validator-generator` and `/test-generator` commands for each endpoint

### Sample Output

```
Extracted 2 specs from specs/myapi_spec.pdf

  EndpointSpec(env_name='myapi', method='GET', path='/items/{id}', base_url='https://api.example.com/v1')
  EndpointSpec(env_name='myapi', method='POST', path='/items',     base_url='https://api.example.com/v1')

environments.yaml updated — fill in thresholds:
  myapi:
    base_url: https://api.example.com/v1
    thresholds:
      max_response_time: 2.0    ← set based on SLA
      min_results_count: 1      ← set based on expected minimum

Next:
  /validator-generator SAMPLE_JSON=... CLASS_NAME=MyApiValidator OUTPUT_MODULE=myapi_validator
  /test-generator ENDPOINT_URL=https://api.example.com/v1 ENV_NAME=myapi ...
```

### What the PDF Parser Extracts

- Every `GET/POST/PUT/DELETE/PATCH` keyword in the text
- The nearest `https://` URL preceding each method keyword
- Environment name inferred from hostname (`restcountries` → `countries`, `open-meteo` → `weather`)
- Path extracted from the URL (everything after the third `/`)

### Supported Formats

| Format | Extension | Status |
|--------|-----------|--------|
| PDF | `.pdf`, `.PDF` | Implemented (pdfplumber) |
| Markdown | `.md`, `.markdown` | Implemented (fenced code blocks + `METHOD /path` lines) |
| OpenAPI 3.x | `.yaml`, `.yml`, `.json` | Stub — see ENHANCEMENTS.md E-01 |

---

## `/validator-generator` — Generate a typed validator

**File:** `.claude/skills/validator-generator.md`

### Invocation

```
/validator-generator
  SAMPLE_JSON={"id": 42, "name": "Widget", "price": 9.99, "active": true}
  ENDPOINT_NAME="MyAPI Item"
  CLASS_NAME=MyApiValidator
  OUTPUT_MODULE=myapi_validator
```

### What It Generates

`apitf/validators/myapi_validator.py`:

```python
from __future__ import annotations
from typing import Any
from apitf.validators.base_validator import BaseValidator, ValidationResult

REQUIRED_FIELDS: tuple[str, ...] = ("id", "name", "price", "active")

class MyApiValidator(BaseValidator):
    def validate(self, data: Any) -> ValidationResult:
        if not isinstance(data, dict):
            self._fail("Response root must be a dict")
            return self._pass()
        for field in REQUIRED_FIELDS:
            if field not in data:
                self._fail(f"Missing required field '{field}'")
        if "id" in data and not isinstance(data["id"], int):
            self._fail(f"'id' must be int, got {type(data['id']).__name__}")
        if "name" in data:
            if not isinstance(data["name"], str) or not data["name"].strip():
                self._fail("'name' must be a non-empty string")
        if "price" in data and not isinstance(data["price"], (int, float)):
            self._fail(f"'price' must be numeric, got {type(data['price']).__name__}")
        if "active" in data and not isinstance(data["active"], bool):
            self._fail(f"'active' must be bool, got {type(data['active']).__name__}")
        return self._pass()
```

### Guarantees of Generated Code

- `REQUIRED_FIELDS` is a module-level constant (Code Style Rule 8)
- All fields checked without short-circuiting (collect ALL errors)
- Full type hints (Code Style Rule 2)
- No `print()`, no `os.path`, no direct `requests`

---

## `/test-generator` — Generate a complete pytest test file

**File:** `.claude/skills/test-generator.md`

### Invocation

```
/test-generator
  ENDPOINT_URL=https://api.example.com/v1
  ENDPOINT_PATH=/items/{id}
  HTTP_METHOD=GET
  RESPONSE_FIELDS=id,name,price,active
  ENV_NAME=myapi
  VALIDATOR_CLASS=MyApiValidator
  DATA_FILE=test_data/myapi_items.json
```

### What It Generates

`tests/test_myapi.py` with five tests (scaffold mode):

| TC | Test | Technique | Assertion |
|----|------|-----------|-----------|
| TC-001 | `test_myapi_positive_baseline` | Positive | probe_path → 200 |
| TC-002 | `test_myapi_performance` | Performance | `response_time_ms < env_config threshold` |
| TC-003 | `test_myapi_schema` | Schema | response passes `{VALIDATOR_CLASS}` contract |
| TC-004 | `test_myapi_https_enforced` | Security | `http://` base URL → `ValueError` |
| TC-005 | `test_myapi_not_found` | Negative | Unknown path → 4xx |

Every generated test includes:
- `HttpClient` — never raw `requests`
- `@pytest.mark.flaky(reruns=2, reruns_delay=2)` — live-API reliability
- All thresholds from `env_config` — zero hardcoded numbers
- `@allure.title("TC-M-NNN: ...")` and `allure.suite("myapi")`

---

## Complete Workflow Example

```
# In a Claude Code session at repo root:

You:    /spec-parser SPEC_PATH=specs/payments_api.pdf

Claude: Extracted 2 specs. environments.yaml updated.
        EndpointSpec(env_name='payments', path='/charges/{id}', method='GET')
        EndpointSpec(env_name='payments', path='/charges', method='POST')
        Next:
          /validator-generator SAMPLE_JSON=... CLASS_NAME=ChargeValidator ...
          /test-generator ENDPOINT_URL=https://api.stripe.com/v1 ENV_NAME=payments ...

You:    /validator-generator
          SAMPLE_JSON={"id": "ch_123", "amount": 2000, "currency": "usd", "status": "succeeded"}
          CLASS_NAME=ChargeValidator
          OUTPUT_MODULE=charge_validator

Claude: [writes apitf/validators/charge_validator.py]

You:    /test-generator
          ENDPOINT_URL=https://api.stripe.com/v1
          ENDPOINT_PATH=/charges/{id}
          HTTP_METHOD=GET
          ENV_NAME=payments
          VALIDATOR_CLASS=ChargeValidator
          DATA_FILE=test_data/charge_ids.json

Claude: [writes tests/test_payments.py — 5 tests (scaffold mode)]
```

```bash
# Verify:
pytest --collect-only -q    # payments tests appear
python scripts/verify_bug_markers.py    # no new open bugs without xfail

# Run:
pytest --env payments -v --alluredir=allure-results
allure serve allure-results
```

**What you do NOT touch:**
- `conftest.py` (repo root) — `--env payments` auto-discovered from YAML; no changes needed
- `HttpClient` — works for any HTTPS endpoint
- `.github/workflows/ci.yml` — new tests run automatically on push
- `BugReporter` — attaches on any failure
- `test_security.py` / `test_baseline.py` — run automatically for the new env if a `security` block is added to YAML
