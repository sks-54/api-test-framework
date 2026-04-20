# Troubleshooting

---

## Installation

### `pip install -e ".[test]"` fails with `BackendUnavailable` or `No module named setuptools`

```bash
pip install --upgrade pip setuptools wheel
pip install -e ".[test]"
```

Python 3.9 ships pip 21.x which does not support PEP 660 editable installs from `pyproject.toml`. Upgrading pip first resolves this.

### `ModuleNotFoundError: No module named 'apitf'`

You are running tests without the package installed. Either:

```bash
pip install -e ".[test]"    # install in editable mode
```

Or confirm the virtual environment is active before running pytest.

---

## Test Collection

### `pytest --collect-only` shows 0 tests or import errors

```bash
# Check what pytest is seeing
pytest --collect-only -v 2>&1 | head -30

# Common causes:
# 1. Missing apitf install
pip install -e ".[test]"

# 2. YAML parse error
python3 -c "import yaml; yaml.safe_load(open('config/environments.yaml'))" && echo OK

# 3. Syntax error in a test file
python3 -c "import py_compile; py_compile.compile('tests/test_countries.py')"
```

### `fixture 'env_config' not found`

`conftest.py` is missing or the `pytest_plugins` line is wrong. The fixture lives in the **repo root** `conftest.py` (not `tests/conftest.py`). Check:

```python
# conftest.py (repo root) must contain:
pytest_plugins = ["apitf.reporters.bug_reporter"]

@pytest.fixture(scope="session")
def env_config(request): ...
```

---

## Test Failures

### `ConnectionError` / `Timeout` on a live API test

This is `ENV_FAILURE`. The test will retry twice (`@pytest.mark.flaky(reruns=2, reruns_delay=2)`).

- If it passes on retry: transient — no action needed
- If it fails all 3 attempts: classify as `SLA_VIOLATION`, file bug, add `xfail`

### `AssertionError: Expected 405, got 415` (or similar wrong status)

This is `QUALITY_FAILURE`. The API is violating RFC 7231. Follow the [Bug Lifecycle](Bug-Lifecycle) process — file a GitHub issue, add `xfail(strict=True)`, push.

Do NOT widen the assertion to `in (405, 415)`.

### `XPASS` — test expected to fail but passed

The API fixed a bug. Remove the `xfail` marker (or YAML `known_violations` entry), update `BUG_REPORT.md` Status to `RESOLVED`, close the GitHub issue.

---

## Pre-Push Hook

### `python scripts/verify_bug_markers.py` fails with `[MISSING] BUG-NNN`

An open `QUALITY_FAILURE` bug in `BUG_REPORT.md` has no matching `xfail` marker. Either:

1. Add `@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Known API bug BUG-NNN / Issue #N: ...")` to the test function, OR
2. Add a `known_violations` entry to `config/environments.yaml` (for YAML-driven tests)

Then re-run the script — it must exit 0 before pushing.

### `[MALFORMED] BUG-NNN: strict=True is missing`

A `QUALITY_FAILURE` xfail has `strict=False` without co-referencing an `SLA_VIOLATION` bug. Either:
- Change to `strict=True` (correct for pure quality failures), or
- Add the SLA bug ID to the reason string if the same test covers both failure modes

---

## CI

### CI shows `XFAIL` as `SKIPPED` in Allure

This is a known limitation of `allure-pytest` ≤ 2.15.3. To distinguish from genuine skips, click the test and inspect `statusDetails.message` — xfail reasons start with `XFAIL` and include the bug ID.

### CI fails with `Node.js deprecated` warning

Update action versions in `.github/workflows/ci.yml`. Current correct versions:
```yaml
uses: actions/checkout@v6.0.2
uses: actions/setup-python@v6.2.0
uses: actions/cache@v5.0.5
uses: actions/upload-artifact@v7.0.1
```

### A CI job fails with `No module named 'apitf'`

CI uses `pip install --upgrade pip && pip install -e ".[test]"` in all stages. If you see this error, check that `pyproject.toml` is committed and the install step in `ci.yml` is correct.

---

## Platform-Specific

### Windows: `setup_hooks.py` installed hook does nothing on push

The hook is a Python script. Ensure `python` is on your `PATH` (not just `python3`). On Windows, `python` is the correct invocation.

### macOS: `allure serve` fails with `java` not found

Allure requires Java. Install it:

```bash
brew install java
# or
brew install --cask temurin
```

### Windows: `allure serve` not found

Download the Allure CLI from [github.com/allure-framework/allure2/releases](https://github.com/allure-framework/allure2/releases) and add `allure-X.Y.Z/bin` to your `PATH`.

---

## Import Errors After Adding a New Validator

```bash
# Check the validator can be imported cleanly
python3 -c "from apitf.validators.myapi_validator import MyApiValidator; print(MyApiValidator())"

# Check test collection picks it up
pytest --collect-only -q tests/test_myapi.py
```

Common causes: missing `from __future__ import annotations`, wrong class name, or `return self._pass()` missing at the end of `validate()`.
