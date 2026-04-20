# CLI Quickstart — Testing a New API Spec

This page covers how to use the `apitf-run` and `apitf-parse` CLI commands to generate
and run tests for a new API spec, on any platform.

---

## Prerequisites

Install the package once (all platforms):

```bash
pip install --upgrade pip && pip install -e ".[test]"
```

After this, `apitf-run` and `apitf-parse` are on your PATH in any active virtual environment.

---

## AI Provider (controls test quality)

`apitf-run` auto-detects the best available AI provider in this order:

| Priority | Provider | How to activate |
|----------|----------|-----------------|
| 1 | Claude Code CLI | Open repo in Claude Code terminal — zero config |
| 2 | Anthropic API | Set `ANTHROPIC_API_KEY` in environment or `.env` |
| 3 | None | 5-test stub generated automatically, no reflector |

---

## macOS / Linux

```bash
# Full pipeline — AI generation + eval loop + Opus reflector
apitf-run specs/myapi_spec.pdf --env myapi --sample

# With explicit API key (if not in environment)
ANTHROPIC_API_KEY=sk-ant-... apitf-run specs/myapi_spec.pdf --env myapi --sample

# Override base URL (when spec contains multiple hosts)
apitf-run specs/myapi_spec.pdf \
  --env myapi \
  --base-url https://api.example.com/v1 \
  --probe-path /health \
  --sample

# Parse only — inspect EndpointSpec objects without generating tests
apitf-parse specs/myapi_spec.pdf --env myapi

# Debug mode — sequential workers, verbose output
apitf-run specs/myapi_spec.pdf --env myapi --sample --no-parallel

# Custom models and iteration cap
apitf-run specs/myapi_spec.pdf --env myapi --sample \
  --model claude-sonnet-4-6 \
  --reflector-model claude-opus-4-7 \
  --max-iter 5
```

---

## Windows (PowerShell)

```powershell
# Inside Claude Code desktop app — zero config
apitf-run specs\myapi_spec.pdf --env myapi --sample

# With API key set for this session
$env:ANTHROPIC_API_KEY = "sk-ant-YOUR_KEY_HERE"
apitf-run specs\myapi_spec.pdf --env myapi --sample

# Override base URL (PowerShell line continuation with backtick)
apitf-run specs\myapi_spec.pdf `
  --env myapi `
  --base-url https://api.example.com/v1 `
  --probe-path /health `
  --sample

# Parse only
apitf-parse specs\myapi_spec.pdf --env myapi

# Sequential / debug mode
apitf-run specs\myapi_spec.pdf --env myapi --sample --no-parallel
```

---

## Windows (CMD)

```cmd
:: Set API key for this session
set ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE

:: Full pipeline
apitf-run specs\myapi_spec.pdf --env myapi --sample

:: Parse only
apitf-parse specs\myapi_spec.pdf --env myapi
```

---

## What Gets Written

After `apitf-run` finishes, these files exist:

| File | Description |
|------|-------------|
| `apitf/validators/myapi_validator.py` | Typed `BaseValidator` subclass; field presence + type checks |
| `tests/test_myapi.py` | 5-test scaffold: positive, performance, schema, security, negative |
| `config/environments.yaml` | `myapi` block added: base_url, probe_path, thresholds |
| `pytest.ini` | `myapi` marker registered |
| `test_plans/myapi_test_plan.md` | Test plan generated from spec |
| `bugs/BUG_REPORT_myapi_*.md` | Per-resource bug report (parallel mode only) |

---

## Running the Generated Tests

All commands are identical on macOS, Linux, and Windows:

```bash
# Run new environment only
pytest --env myapi -v --alluredir=allure-results

# Run all environments including the new one
pytest -v --alluredir=allure-results

# Verify test collection (no import errors)
pytest --env myapi --collect-only -q

# Run only security tests for the new env
pytest --env myapi -m security -v

# Run only performance tests
pytest --env myapi -m performance -v

# Open Allure HTML report (requires allure CLI)
allure serve allure-results
```

---

## Extending Beyond the 5-Test Scaffold

The scaffold covers baseline correctness. To reach full 10-technique coverage:

### Option A — Claude Code skills (interactive)

Open the repo in a Claude Code session, then:

```
/test-generator
  ENDPOINT_URL=https://api.example.com/v1
  ENDPOINT_PATH=/items/{id}
  HTTP_METHOD=GET
  RESPONSE_FIELDS=id,name,price,active
  ENV_NAME=myapi
  VALIDATOR_CLASS=MyapiValidator
  DATA_FILE=test_data/myapi_items.json
```

### Option B — Re-run the eval loop on the existing file

```bash
# macOS / Linux
python scripts/advisor_review.py \
  --env myapi \
  --test-file tests/test_myapi.py \
  --max-iter 3

# Windows (PowerShell)
python scripts\advisor_review.py `
  --env myapi `
  --test-file tests\test_myapi.py `
  --max-iter 3
```

---

## Supported Spec Formats

| Format | Extension | Parser |
|--------|-----------|--------|
| PDF | `.pdf`, `.PDF` | `PDFParser` (pdfplumber) |
| OpenAPI 3.x | `.yaml`, `.yml`, `.json` | `OpenAPIParser` |
| Markdown | `.md`, `.markdown` | `MarkdownParser` |

The correct parser is selected automatically based on file extension.

---

## Full Workflow Example

```bash
# 1. Place spec
cp ~/Downloads/payments_api.pdf specs/

# 2. Generate tests (inside Claude Code — zero config)
apitf-run specs/payments_api.pdf --env payments --sample

# 3. Review what was generated
cat config/environments.yaml          # verify payments block added
cat apitf/validators/payments_validator.py
cat tests/test_payments.py

# 4. Run tests
pytest --env payments -v --alluredir=allure-results

# 5. If QUALITY failures appear → file GitHub issue + add xfail marker
gh issue create --label bug,quality-failure \
  --title "[BUG] payments: /charges returns 422 instead of 400"

# 6. View report
allure serve allure-results
```
