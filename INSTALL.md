# Installation Guide — macOS · Linux · Windows

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.9 – 3.12 |
| Git | any recent |
| GitHub CLI (`gh`) | 2.x+ (for push/CI monitoring) |
| `ANTHROPIC_API_KEY` | optional — enables AI test generation, eval loop, and Opus reflector |

### Setting up your Anthropic API key (optional but recommended)

`apitf-run` auto-detects your key in this priority order:

1. `--api-key sk-ant-...` flag (explicit, one-off)
2. `ANTHROPIC_API_KEY` environment variable
3. `.env` file in the project root

**Recommended — add to `.env`** (gitignored, persists across sessions):
```bash
echo "ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE" >> .env
```

**Or export for the current shell session:**
```bash
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

Without a key, `apitf-run` still works: it generates a 5-test baseline stub and skips the
AI generation, eval-loop structural fixes, and Opus reflector review.

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

# Install Allure for HTML reports (optional)
brew install allure

# Install GitHub CLI
brew install gh && gh auth login
```

### Linux (Ubuntu / Debian)

```bash
# Install Python
sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip

# Install GitHub CLI
sudo apt-get install -y gh

# Install Allure (optional)
sudo apt-get install -y default-jre
wget https://github.com/allure-framework/allure2/releases/latest/download/allure-commandline.zip
# Or via snap: sudo snap install allure
```

### Windows (PowerShell)

```powershell
# Install Python from python.org or via winget
winget install Python.Python.3.11

# Install GitHub CLI
winget install GitHub.cli
gh auth login

# Install Allure (optional — requires Java)
# Download from https://github.com/allure-framework/allure2/releases
# Add allure/bin to PATH

# All pytest commands work identically in PowerShell:
pytest -v --alluredir=allure-results
```

> **Windows note:** Git hooks installed by `python scripts/setup_hooks.py` use
> Python (not bash), so they work without WSL or Git Bash.

---

## Verifying the Install

```bash
# Check imports
python -c "from apitf.http_client import HttpClient; print('OK')"

# Check test collection (should report 88+ tests, no import errors)
pytest --collect-only -q

# Run the bug-marker guard (used by the pre-push hook)
python scripts/verify_bug_markers.py
```

---

## Adding a New API (3 steps)

1. Add an entry to `config/environments.yaml` (base_url, thresholds, security block)
2. Add `apitf/validators/<new>_validator.py` extending `BaseValidator`
3. Add `tests/test_<new>.py` using the `env_config` fixture

Security, RFC, and baseline tests run automatically — no changes needed in
`test_security.py` or `test_baseline.py`.

---

## CI

The CI pipeline runs on push to any branch (except main and doc-only changes):

| Stage | Runner | Python |
|-------|--------|--------|
| Smoke | ubuntu-latest | 3.11 |
| Platform | windows-latest | 3.11 |
| Platform | macos-latest | 3.11 |
| Version (oldest) | ubuntu-latest | 3.9 |
| Version (newest) | ubuntu-latest | 3.12 |
| Gate | — | — |
