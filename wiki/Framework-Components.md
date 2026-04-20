# Framework Components

Detailed reference for every module in `apitf/`.

---

## HttpClient (`apitf/http_client.py`)

The only HTTP entry point in this framework. Tests must never import `requests` directly.

### Behaviors

| Behavior | Detail |
|----------|--------|
| HTTPS enforcement | `ValueError("Only HTTPS base URLs are supported")` raised at construction — no network call |
| Retry on 5xx | 500/502/503/504 → up to 3 retries, 0.5s exponential backoff via `urllib3.Retry` |
| Response timing | `time.monotonic()` — monotonic clock, immune to NTP drift |
| JSON parsing | `resp.json()` attempted; `None` if body is not JSON (no exception raised) |
| Context manager | `with HttpClient(url) as client:` — session closed on `__exit__` |
| Logging | Every request/response at DEBUG; no credentials or PII |

### HttpResponse Fields

| Field | Type | Description |
|-------|------|-------------|
| `status_code` | `int` | HTTP status |
| `json_body` | `Any \| None` | Parsed JSON; `None` if not JSON |
| `headers` | `dict[str, str]` | Response headers (lowercased keys) |
| `response_time_ms` | `float` | End-to-end wall time in milliseconds |
| `url` | `str` | Final URL after redirects |
| `raw_text` | `str` | Raw response body |

### Usage

```python
from apitf.http_client import HttpClient

# Basic GET
with HttpClient("https://restcountries.com/v3.1") as client:
    resp = client.get("/name/germany")

print(resp.status_code)       # 200
print(resp.response_time_ms)  # 284.3

# With query params
resp = client.get("/forecast", params={"latitude": 52.52, "longitude": 13.41, "hourly": "temperature_2m"})

# With custom headers (used by security tests)
resp = client.request("GET", "/forecast", extra_headers={"Accept": "application/xml"})

# Non-GET methods (used by security tests)
resp = client.request("POST", "/name/germany")

# HTTPS enforcement — raises immediately, no network call
with pytest.raises(ValueError, match="HTTPS"):
    HttpClient("http://insecure.example.com")
```

---

## BaseValidator (`apitf/validators/base_validator.py`)

Abstract base class enforcing a consistent validation contract.

### Contract

```python
class BaseValidator(ABC):
    def __init__(self) -> None:
        self._errors: list[str] = []
        self._warnings: list[str] = []

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult: ...

    def _fail(self, message: str) -> None:
        self._errors.append(message)   # accumulates — never raises, never stops

    def _warn(self, message: str) -> None:
        self._warnings.append(message)

    def _pass(self) -> ValidationResult:
        return ValidationResult(
            passed=len(self._errors) == 0,
            errors=list(self._errors),
            warnings=list(self._warnings),
        )
```

### Key Design Principle — Collect ALL Errors

```python
# Correct — every field checked regardless of previous failures
for field in REQUIRED_FIELDS:
    if field not in item:
        self._fail(f"Missing '{field}'")   # accumulates

# Wrong — stops at first error, hides other bugs
if "name" not in item:
    raise AssertionError("Missing 'name'")
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    passed: bool
    errors: list[str]    # empty if passed
    warnings: list[str]  # non-blocking observations

# Usage in tests
result = CountryValidator().validate(resp.json_body)
assert result.passed, result.errors
```

---

## CountryValidator (`apitf/validators/countries_validator.py`)

Validates REST Countries API response objects.

### Field Contracts

| Field | Type | Value |
|-------|------|-------|
| `name` | `dict` with `common: str` | `common` must be non-empty |
| `capital` | `list` | must be non-empty |
| `population` | `int` (not `bool`) | `>= 1` |
| `currencies` | `dict` | must be non-empty |
| `languages` | `dict` | must be non-empty |

### Usage

```python
from apitf.validators.countries_validator import CountriesValidator

result = CountriesValidator().validate(resp.json_body[0])  # single country object
assert result.passed, result.errors
```

---

## WeatherValidator (`apitf/validators/weather_validator.py`)

Validates Open-Meteo forecast API response objects.

### Field Contracts

| Field | Type | Value |
|-------|------|-------|
| `timezone` | `str` | non-empty |
| `hourly` | `dict` | must contain `temperature_2m` key |
| `hourly.temperature_2m` | `list` | `len >= 1` |
| each temperature | `int \| float` | `-80.0 <= t <= 60.0` |

---

## BugReporter (`apitf/reporters/bug_reporter.py`)

A pytest plugin registered via `pytest_plugins = ["apitf.reporters.bug_reporter"]` in `conftest.py`. Fires on every test failure via the `pytest_runtest_makereport` hook.

### What It Captures

```markdown
# [FAIL] test_name — AssertionError: <message>

**Date:** 2026-04-19 14:23:01 UTC
**Environment:** weather
**Category:** QUALITY_FAILURE

## Platform
- OS · Python version · Architecture

## Steps to Reproduce
1. pytest command
2. Request: GET https://...
3. Params: {...}

## Expected Result
response_time_ms < 3000ms

## Actual Result
response_time_ms = 31954.3ms

## Data
- Request URL · Status Code · Response Time · Response snippet
```

### Output Destinations

1. Written to `bugs/<timestamp>_<test_name>.md` on disk (gitignored)
2. Attached to Allure as a `Bug Report` text attachment on the failing test

### Failure Categories

| Category | Trigger | Next Action |
|----------|---------|-------------|
| `QUALITY_FAILURE` | Wrong status, schema mismatch, value out of range | File GitHub issue, add `xfail(strict=True)` |
| `ENV_FAILURE` | `ConnectionError`, `Timeout` | Retry (flaky marker), file bug if all retries fail |
| `STRUCTURAL_FAILURE` | `ImportError`, `FixtureError` | Fix framework code |

---

## SLA Failure Adapter (`apitf/sla_exceptions.py`)

Platform-agnostic exception tuple for SLA violation xfail markers.

```python
from apitf.sla_exceptions import SLA_FAILURE_EXCEPTIONS

@pytest.mark.xfail(
    strict=False,
    raises=SLA_FAILURE_EXCEPTIONS,   # (AssertionError, requests.exceptions.ConnectionError)
    reason="BUG-004: Open-Meteo SLA_VIOLATION",
)
def test_forecast_performance(...): ...
```

### Why Two Exception Types Are Exhaustive

| Platform | TCP failure mode | Exception |
|----------|-----------------|-----------|
| Linux/macOS | Read timeout — all retries exhaust | `ConnectionError` |
| Windows | `ConnectionResetError(10054)` — retries succeed but accumulate 30s+ | `AssertionError` (slow 200) |

Never inline the tuple — import from `sla_exceptions.py`. This is the single place to update if a new exception type is ever found.

---

## SpecParser (`apitf/spec_parser/`)

Parses spec documents into `EndpointSpec` dataclasses for test generation.

### EndpointSpec Fields

| Field | Type | Source |
|-------|------|--------|
| `env_name` | `str` | Inferred from hostname slug |
| `method` | `str` | GET / POST / etc. |
| `path` | `str` | `/name/{name}` |
| `base_url` | `str` | Full `https://` URL |
| `resource_name` | `str` | First non-template path segment (e.g. `name`, `forecast`) — used for parallel pipeline grouping |
| `description` | `str` | Extracted from spec text |
| `required_params` | `list[str]` | From spec |
| `thresholds` | `dict` | Always `{}` — filled by caller from YAML |

### Parser Registry

```python
from apitf.spec_parser.base_parser import SpecParserRegistry
from apitf.spec_parser.pdf_parser import PDFParser

registry = SpecParserRegistry()
registry.register(PDFParser())
specs = registry.parse(Path("specs/myapi.pdf"))
```

Dispatch is by `source.suffix` — each parser declares `supported_extensions`.

### Implemented / Stub Status

| Parser | Status | Notes |
|--------|--------|-------|
| `PDFParser` | Implemented | Uses pdfplumber; extracts method keywords + nearest `https://` URL |
| `MarkdownParser` | Implemented | Parses fenced code blocks and `METHOD /path` lines; registered via `ParserRegistry` |
| `OpenAPIParser` | Stub | Interface defined; see ENHANCEMENTS.md E-01 |
