# Installation Guide — macOS · Linux · Windows

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.9 – 3.12 |
| Git | any recent |
| GitHub CLI (`gh`) | 2.x+ (for push/CI monitoring) |
| `ANTHROPIC_API_KEY` | optional — enables AI test generation, eval loop, and Opus reflector |

### AI provider setup (optional but recommended)

`apitf-run` auto-discovers the AI provider in this priority order:

1. **Claude Code session** — zero config. If you run inside a Claude Code terminal (`CLAUDECODE=1`), the framework calls the authenticated `claude` CLI automatically.
2. **`ANTHROPIC_API_KEY` env var** — set once, persists across sessions.
3. **`.env` file** — add `ANTHROPIC_API_KEY=sk-ant-...` to `.env` in the project root (gitignored).

**Fastest setup inside Claude Code:** no configuration needed — just run `apitf-run`.

**When running outside Claude Code:**
```bash
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
# or
echo "ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE" >> .env
```

Without any AI provider, `apitf-run` still works: it generates a 5-test baseline stub and
skips AI generation, eval-loop structural fixes, and the Opus reflector review.

---

## Platform Compatibility

| Feature | macOS | Linux | Windows |
|---------|-------|-------|---------|
| Core test suite (`pytest --env countries/weather`) | ✅ | ✅ | ✅ |
| `HttpClient` / HTTPS enforcement | ✅ | ✅ | ✅ |
| Validators / `BaseValidator` | ✅ | ✅ | ✅ |
| `apitf-parse` / `apitf-scaffold` CLI | ✅ | ✅ | ✅ |
| Allure reporting (`allure-pytest`) | ✅ | ✅ | ✅ |
| `allure serve` (web UI) | ✅ via brew | ✅ via Java | ✅ via Java |
| Git pre-push hook (`setup_hooks.py`) | ✅ | ✅ | ✅ (no WSL needed) |
| `ClaudeCLIProvider` (zero-config AI) | ✅ Claude Code terminal | ✅ Claude Code terminal | ✅ Claude Code desktop app |
| `AnthropicProvider` (API key) | ✅ | ✅ | ✅ |

All Python code uses `pathlib.Path` (no `os.path`), no `shell=True`, and Python-only scripts. Signal handling differences between Unix and Windows are handled automatically.

---

## Quick Install (all platforms)

```bash
# 1. Clone the repo
git clone https://github.com/sks-54/api-test-framework.git
cd api-test-framework

# 2. Create and activate a virtual environment
#    macOS / Linux:
python3 -m venv .venv && source .venv/bin/activate
#    Windows (PowerShell):
python -m venv .venv; .\.venv\Scripts\Activate.ps1
#    Windows (CMD):
python -m venv .venv && .venv\Scripts\activate.bat

# 3. Install the package with all test dependencies
#    (upgrade pip first — Python 3.9 ships pip 21.x which may reject pyproject.toml)
pip install --upgrade pip && pip install -e ".[test]"

# 4. Install git hooks (pre-push bug-marker check)
python scripts/setup_hooks.py
```

---

## Running Tests

All commands work identically on macOS, Linux, and Windows.

```bash
# All environments (countries + weather)
pytest -v --alluredir=allure-results

# Single environment
pytest --env countries -v --alluredir=allure-results
pytest --env weather  -v --alluredir=allure-results

# Security + RFC tests only
pytest -m security -v --alluredir=allure-results

# Baseline tests only (HTTPS, 2xx, 404, performance)
pytest -m compatibility -v --alluredir=allure-results

# View Allure report (requires allure CLI — see below)
allure serve allure-results
```

---

## Platform Notes

### macOS

```bash
# Install Python via Homebrew (if not already installed)
brew install python@3.11

# Install Allure for HTML reports (optional — brew handles the Java dependency)
brew install allure

# Install GitHub CLI
brew install gh && gh auth login
```

**Claude Code session (zero-config AI):** Open this repo in the Claude Code terminal app. `ClaudeCLIProvider` is auto-detected — no API key needed.

**API key alternative:**
```bash
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

### Linux (Ubuntu / Debian)

```bash
# Install Python
sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip

# Install GitHub CLI
sudo apt-get install -y gh

# Install Allure CLI (optional — requires Java for `allure serve`)
sudo apt-get install -y default-jre
sudo snap install allure          # or download from github.com/allure-framework/allure2/releases
```

> **Allure note:** `allure-pytest` (installed via pip with `.[test]`) generates the
> `allure-results/` directory. The separate Allure CLI (`allure serve`) is only needed
> to open the interactive HTML report in a browser. The test suite runs without it.

**Claude Code session (zero-config AI):** Run this repo in a Claude Code terminal. `ClaudeCLIProvider` is auto-detected — no API key needed.

**API key alternative:**
```bash
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

### Windows (PowerShell)

```powershell
# Install Python from python.org or via winget
winget install Python.Python.3.11

# If venv activation is blocked by execution policy:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install GitHub CLI
winget install GitHub.cli
gh auth login

# Install Allure CLI (optional — requires Java)
# Download from https://github.com/allure-framework/allure2/releases and add allure/bin to PATH
# Without the CLI, allure-results/ is still generated; you just can't run `allure serve`

# All pytest commands work identically in PowerShell:
pytest -v --alluredir=allure-results
```

> **Git hooks:** `python scripts/setup_hooks.py` installs a Python pre-push hook — no WSL or Git Bash required.

> **Signal handling:** The framework handles the Windows vs Unix signal difference automatically — no configuration needed.

**Claude Code session (zero-config AI):** Open this repo in the Claude Code desktop app for Windows. `ClaudeCLIProvider` is auto-detected and the `claude` CLI is available inside that terminal. Alternatively, use WSL2 with the Linux Claude Code terminal.

**API key alternative (works without Claude Code):**
```powershell
# PowerShell — current session only:
$env:ANTHROPIC_API_KEY = "sk-ant-YOUR_KEY_HERE"
# PowerShell — persist across sessions (writes to user environment):
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY","sk-ant-YOUR_KEY_HERE","User")
```
```cmd
:: CMD — current session only:
set ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
:: CMD — persist across sessions:
setx ANTHROPIC_API_KEY "sk-ant-YOUR_KEY_HERE"
```

```text
# All platforms — .env file in project root (gitignored, loaded automatically):
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

---

## Verifying the Install

```bash
# Check imports
python -c "from apitf.http_client import HttpClient; print('OK')"

# Check test collection (should report 114+ tests, no import errors)
pytest --collect-only -q

# Run the bug-marker guard (used by the pre-push hook)
python scripts/verify_bug_markers.py
```

---

## Generating Tests for a New API (CLI Workflow)

Once the package is installed (`pip install -e ".[test]"`), two CLI commands are available
on all platforms: `apitf-run` (full pipeline) and `apitf-parse` (parse only).

### Step 1 — Place your spec file

```
specs/myapi_spec.pdf     # PDF
specs/myapi_spec.yaml    # OpenAPI 3.x
specs/myapi_spec.md      # Markdown
```

### Step 2 — Run the full pipeline

**macOS / Linux:**
```bash
# Zero-config inside a Claude Code session (no API key needed)
apitf-run specs/myapi_spec.pdf --env myapi --sample

# Outside Claude Code — set API key first
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
apitf-run specs/myapi_spec.pdf --env myapi --sample

# Override base URL when the spec has multiple hosts
apitf-run specs/myapi_spec.pdf \
  --env myapi \
  --base-url https://api.example.com/v1 \
  --probe-path /health \
  --sample

# Parse only — inspect what the parser extracts, no test generation
apitf-parse specs/myapi_spec.pdf --env myapi

# Force sequential mode (disable parallel workers — useful for debugging)
apitf-run specs/myapi_spec.pdf --env myapi --sample --no-parallel

# Custom AI models and iteration limit
apitf-run specs/myapi_spec.pdf --env myapi --sample \
  --model claude-sonnet-4-6 \
  --reflector-model claude-opus-4-7 \
  --max-iter 5
```

**Windows (PowerShell):**
```powershell
# Zero-config inside Claude Code desktop app
apitf-run specs\myapi_spec.pdf --env myapi --sample

# With API key
$env:ANTHROPIC_API_KEY = "sk-ant-YOUR_KEY_HERE"
apitf-run specs\myapi_spec.pdf --env myapi --sample

# Override base URL
apitf-run specs\myapi_spec.pdf `
  --env myapi `
  --base-url https://api.example.com/v1 `
  --probe-path /health `
  --sample

# Parse only
apitf-parse specs\myapi_spec.pdf --env myapi
```

**Windows (CMD):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
apitf-run specs\myapi_spec.pdf --env myapi --sample
```

### What the pipeline writes automatically

| File | Purpose |
|------|---------|
| `apitf/validators/myapi_validator.py` | Typed field-contract validator |
| `tests/test_myapi.py` | 5-test scaffold (positive, performance, schema, security, negative) |
| `config/environments.yaml` | New `myapi` block (base_url, probe_path, thresholds) |
| `pytest.ini` | `myapi` marker added |
| `test_plans/myapi_test_plan.md` | Test plan generated from spec |
| `bugs/BUG_REPORT_myapi_*.md` | Bug report per resource (parallel mode) |

### Step 3 — Run the generated tests

All commands work identically on macOS, Linux, and Windows:

```bash
# Run only the new environment
pytest --env myapi -v --alluredir=allure-results

# Run everything including new env
pytest -v --alluredir=allure-results

# Collect only — verify tests were generated correctly
pytest --env myapi --collect-only -q

# View Allure report
allure serve allure-results
```

### Step 4 — Extend beyond the scaffold (optional)

The scaffold produces 5 baseline tests. To reach full coverage (10 techniques),
use the Claude Code skills inside a Claude Code session:

```
/test-generator
  ENDPOINT_URL=https://api.example.com/v1
  ENDPOINT_PATH=/items/{id}
  HTTP_METHOD=GET
  RESPONSE_FIELDS=id,name,price
  ENV_NAME=myapi
  VALIDATOR_CLASS=MyapiValidator
  DATA_FILE=test_data/myapi_items.json
```

Or re-run the eval loop directly on the existing test file:

```bash
python scripts/advisor_review.py \
  --env myapi \
  --test-file tests/test_myapi.py \
  --max-iter 3
```

### Adding a New API Manually (3 steps, no CLI)

1. Add an entry to `config/environments.yaml` (base_url, probe_path, thresholds)
2. Add `apitf/validators/<new>_validator.py` extending `BaseValidator`
3. Add `tests/test_<new>.py` using the `env_config` fixture

Security, RFC, and baseline tests run automatically — no changes needed in
`test_security.py` or `test_baseline.py`.

---

## CI

The CI pipeline runs on every PR (all files) and on push to any branch except main (doc-only commits skipped as a resource optimization):

| Stage | Runner | Python |
|-------|--------|--------|
| Smoke | ubuntu-latest | 3.11 |
| Platform | windows-latest | 3.11 |
| Platform | macos-latest | 3.11 |
| Version (oldest) | ubuntu-latest | 3.9 |
| Version (newest) | ubuntu-latest | 3.12 |
| Gate | — | — |
