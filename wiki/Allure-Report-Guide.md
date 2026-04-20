# Allure Report Guide

Allure is the primary reporting layer for this framework. Every test emits structured metadata (suite, title, step) captured during the pytest run and rendered into an interactive HTML report.

---

## Generating and Opening the Report

```bash
source .venv/bin/activate

# Run tests and collect results into allure-results/
pytest --env countries --env weather -q --alluredir=allure-results

# Generate the static HTML report
allure generate allure-results -o allure-report --clean

# Open in browser (starts a local server)
allure open allure-report

# Or serve directly without generating (requires allure CLI)
allure serve allure-results
```

> **Note:** `allure-pytest` (installed via `pip install -e ".[test]"`) writes the raw results. The `allure` CLI (separate install) renders the report. If the CLI is not available, upload the `allure-results/` directory to any Allure-compatible CI artifact viewer.

---

## Installing the Allure CLI

**macOS:**
```bash
brew install allure
```

**Linux:**
```bash
# Download the binary directly
curl -Lo allure.tgz https://github.com/allure-framework/allure2/releases/latest/download/allure-2.x.x.tgz
tar -xzf allure.tgz && sudo mv allure-*/bin/allure /usr/local/bin/
```

**Windows:**
```powershell
# Via Scoop
scoop install allure

# Or download the zip from https://github.com/allure-framework/allure2/releases
```

---

## Reading the Report

### Suites View

Each environment maps to an Allure suite. The `pytestmark` in every test file sets:
```python
pytestmark = [pytest.mark.countries, allure.suite("countries")]
```

In the report, navigate to **Suites** → **countries** or **weather** to see all tests grouped by environment. Parallel pipeline runs produce per-resource suites: `jsonplaceholder_posts`, `jsonplaceholder_users`, etc.

### Filtering by Environment

Use the **Categories** sidebar or the search bar to filter by suite name. The `@allure.title("TC-XXX: ...")` annotation provides human-readable test names.

### Test Status Indicators

| Status | Meaning |
|--------|---------|
| `PASSED` | Test assertion passed |
| `FAILED` | Assertion failed — likely a QUALITY_FAILURE |
| `SKIPPED` | Test skipped (env filter applied via `--env` flag) |
| `BROKEN` | Unexpected exception (STRUCTURAL_FAILURE) |
| `XFAILED` | Known API bug — test expected to fail, and it did |
| `XPASSED` | Expected to fail but passed — API fixed the bug, remove xfail |

### Reading xfailed Tests

`XFAILED` means the test ran, failed as expected, and CI counts it as passing. The failure reason shows:
```
Known API bug BUG-NNN / Issue #N: <description>
```

When an `XFAILED` test becomes `XPASSED`:
1. The API fixed the bug
2. Remove the `@pytest.mark.xfail(...)` decorator from the test
3. Confirm the test passes cleanly
4. Close the GitHub issue

---

## Uploading Allure Results in CI

The CI pipeline uploads `allure-results/` as a GitHub Actions artifact:

```yaml
- uses: actions/upload-artifact@v7.0.1
  with:
    name: allure-results
    path: allure-results/
```

Download the artifact from the Actions tab → run → **allure-results** → **Download**. Then run `allure generate` locally on the downloaded directory.

---

## Attaching Response Data

The `BugReporterPlugin` (in `apitf/reporters/bug_reporter.py`) automatically attaches failing response data to Allure when a test fails. To attach data manually in a test:

```python
import allure

allure.attach(
    resp.json_body,
    name="Response Body",
    attachment_type=allure.attachment_type.JSON,
)
```

---

## Common Issues

| Problem | Fix |
|---------|-----|
| `allure: command not found` | Install the Allure CLI separately (see above) |
| Report shows 0 tests | Check `--alluredir=allure-results` flag was passed to pytest |
| All tests show SKIPPED | Run without `--env` to collect all, or pass the right `--env` value |
| `allure serve` fails on port conflict | Use `allure serve -p 9090 allure-results` to specify a port |
