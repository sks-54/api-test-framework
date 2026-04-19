# API Test Framework

[![CI](https://github.com/sks-54/api-test-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/sks-54/api-test-framework/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org)
[![pytest](https://img.shields.io/badge/pytest-8.x-green)](https://pytest.org)

Extensible multi-environment API test framework. Add a new API by editing config and adding a validator — zero framework changes required.

---

## Architecture

### 1. System Overview

```mermaid
graph TD
    subgraph APIs
        A1[REST Countries<br/>restcountries.com]
        A2[Open-Meteo<br/>api.open-meteo.com]
    end

    subgraph Framework
        HC[HttpClient<br/>retry · timing · logging]
        V[Validators<br/>CountryValidator<br/>WeatherValidator]
        R[Reporters<br/>BugReporter<br/>DeliverablesTracker]
    end

    subgraph Config
        YAML[environments.yaml<br/>base_url · thresholds]
        DATA[cities.json<br/>lat/lon test data]
    end

    subgraph Output
        AL[Allure Report<br/>per-env suites]
        BG[bugs/ directory<br/>structured markdown]
    end

    subgraph CI
        GH[GitHub Actions<br/>6-job pipeline]
    end

    YAML --> HC
    DATA --> V
    A1 --> HC
    A2 --> HC
    HC --> V
    V --> R
    R --> AL
    R --> BG
    Framework --> GH
```

### 2. Multi-Agent Review Workflow

```mermaid
sequenceDiagram
    participant U as User
    participant S as Claude Sonnet<br/>(Implementer)
    participant O as Claude Opus<br/>(Advisor)
    participant CI as GitHub Actions

    U->>S: Phase request
    S->>S: Generate code + tests
    S->>O: Agent(model="opus")<br/>diff + rules + requirements.txt
    O-->>S: Gaps, deviations, corrections
    S->>S: Apply corrections
    alt corrections needed
        S->>O: Re-review (max 5 iterations)
        O-->>S: Approved
    end
    S->>CI: bash scripts/push.sh
    CI-->>S: gh run watch (blocks terminal)
    CI-->>U: Green / Bug filed
```

### 3. Test Execution Flow

```mermaid
flowchart LR
    CLI["pytest --env countries"] --> OPT[pytest_addoption\nauto-discovers YAML keys]
    OPT --> CFX[conftest.py\nenv_config fixture]
    CFX --> YAML[environments.yaml\nbase_url · thresholds]
    YAML --> HC[HttpClient\nretry · timing]
    HC --> API[Live API endpoint]
    API --> HC
    HC --> RESP[ApiResponse\nstatus · json_body · response_time_ms]
    RESP --> VAL[Validator.validate\ncollects ALL errors]
    VAL --> PASS{passed?}
    PASS -- yes --> AL[Allure attachment]
    PASS -- no --> BUG[BugReporter\nbugs/TC-xxx.md]
    BUG --> XF[xfail marker\nGitHub issue filed]
```

### 4. Extensibility — Add a New API in 3 Steps

```mermaid
flowchart TD
    S1["Step 1\nAdd entry to\nconfig/environments.yaml"]
    S2["Step 2\nCreate src/validators/new_validator.py\nextending BaseValidator"]
    S3["Step 3\nCreate tests/test_new.py\nusing env_config fixture"]

    S1 --> S2 --> S3

    S3 --> FW[Framework\nHttpClient · Allure · BugReporter\nCI pipeline · verify_bug_markers.py]

    note1["Zero changes to:\n- conftest.py\n- HttpClient\n- CI workflow\n- BaseValidator"]
    S3 -.-> note1
```

### 5. CI Pipeline

```mermaid
flowchart TD
    PUSH[git push\nbash scripts/push.sh] --> TR{Trigger\npaths-ignore docs}

    TR --> SM[Stage 1 — Smoke\nubuntu / Python 3.11\ncountries + weather envs]

    SM -- pass --> PL[Stage 2 — Platform\nOS compatibility]
    SM -- fail --> GATE

    PL --> W[windows-latest / 3.11]
    PL --> M[macos-latest / 3.11]

    W -- pass --> VS
    M -- pass --> VS
    W -- fail --> GATE
    M -- fail --> GATE

    VS[Stage 3 — Versions\nPython boundary check] --> V9[ubuntu / 3.9]
    VS --> V12[ubuntu / 3.12]

    V9 -- pass --> GATE
    V12 -- pass --> GATE
    V9 -- fail --> GATE
    V12 -- fail --> GATE

    GATE[Quality Gate\nalways runs] -- all success --> GREEN[✓ Merge allowed]
    GATE -- any fail --> RED[✗ Merge blocked]

    SM -.-> ART[Allure artifact\nretention 7 days]
```

---

## Setup

```bash
git clone https://github.com/sks-54/api-test-framework.git
cd api-test-framework
pip install -r requirements.txt
bash scripts/setup_hooks.sh    # installs git pre-push hook (run once)
```

---

## Running Tests

```bash
# Single environment
python3 -m pytest --env countries -v --alluredir=allure-results
python3 -m pytest --env weather   -v --alluredir=allure-results

# All environments
python3 -m pytest -v --alluredir=allure-results

# View Allure report
allure serve allure-results
```

---

## Adding a New API

1. **`config/environments.yaml`** — add a new top-level key:
   ```yaml
   myapi:
     base_url: "https://api.example.com/v1"
     thresholds:
       max_response_time: 3.0
       min_results_count: 1
   ```

2. **`src/validators/myapi_validator.py`** — extend `BaseValidator`:
   ```python
   from src.validators.base_validator import BaseValidator, ValidationResult

   class MyApiValidator(BaseValidator):
       def validate(self, data: dict) -> ValidationResult:
           errors: list[str] = []
           if "id" not in data:
               errors.append("Missing required field: id")
           return self._pass() if not errors else self._fail(errors)
   ```

3. **`tests/test_myapi.py`** — use the `env_config` fixture:
   ```python
   import pytest, allure
   from src.http_client import HttpClient
   from src.validators.myapi_validator import MyApiValidator

   pytestmark = [pytest.mark.myapi, allure.suite("myapi")]

   def test_myapi_schema(env_config):
       cfg = env_config["myapi"]
       with HttpClient(cfg["base_url"]) as client:
           resp = client.get("/items/1")
       assert resp.status_code == 200
       result = MyApiValidator().validate(resp.json_body)
       assert result.passed, result.errors
   ```

No changes to `conftest.py`, `HttpClient`, the CI workflow, or any framework file.

---

## Bug Report Format

Failures auto-generate a structured markdown file in `bugs/`:

```markdown
# [FAIL] test_forecast_performance[Mumbai] — SLA violation

**Steps to Reproduce:**
pytest --env weather tests/test_weather.py::test_forecast_performance[Mumbai] -v
GET https://api.open-meteo.com/v1/forecast?latitude=19.08&longitude=72.88&...

**Expected:** response_time_ms < 3000ms (from environments.yaml max_response_time: 3.0)
**Actual:** ConnectionError — server closed connection after 30s

**Data:**
- request_url: https://api.open-meteo.com/v1/forecast?...
- status_code: N/A (connection reset)
- response_time_ms: N/A
- environment: weather
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| `env_config` auto-discovers YAML keys | Adding a new environment key is the only change needed — no code edits |
| `BaseValidator.validate()` collects all errors | Fail-fast hides multiple schema bugs behind the first one |
| `SLA_FAILURE_EXCEPTIONS` adapter in `src/sla_exceptions.py` | Platform-agnostic: requests normalises all OS transport errors; `AssertionError` covers slow-but-eventual responses. New platforms need zero xfail changes |
| `pytest-rerunfailures` over `pytest-retry` | `pytest-retry` silently ignores `reruns=` kwargs (uses `retries=` instead), breaking xfail in CI |
| 6-job CI instead of 3 OS × 4 Python = 12 | OS compat and Python version compat are independent dimensions — test each separately |
| `strict=False` xfail for SLA bugs | Test may pass if the API is fast enough from a nearby runner; `strict=True` would require consistent failure to avoid `xpass` surfacing |
| `xfail(strict=True)` for pure QUALITY_FAILURE | API returns wrong data per spec — should always fail until the API is fixed |
| `bash scripts/push.sh` enforces Rule 18 | Terminal blocks until CI completes — CI monitoring cannot be forgotten |
| Git pre-push hook runs `verify_bug_markers.py` | Push is blocked if any open QUALITY_FAILURE bug is missing an xfail marker |

---

## CI Pipeline Details

| Stage | Runner | Python | Purpose |
|-------|--------|--------|---------|
| Smoke | ubuntu-latest | 3.11 | Fast-fail: import errors, both API environments |
| Platform (windows) | windows-latest | 3.11 | OS path separators, encoding, tempfiles |
| Platform (mac) | macos-latest | 3.11 | OS path separators, encoding, tempfiles |
| Versions (3.9) | ubuntu-latest | 3.9 | Oldest supported — deprecated syntax, stdlib |
| Versions (3.12) | ubuntu-latest | 3.12 | Newest supported — stdlib changes, type hints |
| Quality Gate | ubuntu-latest | — | Blocks merge if any upstream stage failed |

Allure results uploaded as artifact (7-day retention) after every smoke run.
