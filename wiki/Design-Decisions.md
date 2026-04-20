# Design Decisions

Key architectural choices, the alternatives considered, and why this approach was chosen.

---

## 1. YAML-Driven Config (`environments.yaml` as Single Source of Truth)

**Decision:** All base URLs, thresholds, and security violation metadata live in `config/environments.yaml`. No hardcoded values in test files.

**Alternative:** Per-environment Python fixtures or `.env` files.

**Why YAML:** A new API is added by adding a YAML block — no Python changes. The `--env` flag, test parametrization, Allure suites, and the pre-push guard all auto-discover keys from the same file. Changing a threshold in one place changes it everywhere.

**Enforcement:** `verify_bug_markers.py` validates that `known_violations` entries have valid `type`/`method` values. Tests that read from `env_config` will fail to collect if the key is missing.

---

## 2. YAML-Driven xfail for Security/Baseline (No Code Changes Per New Bug)

**Decision:** Security and baseline test parametrization reads `known_violations` from YAML and applies `pytest.mark.xfail` at collection time via `pytest.param(..., marks=[...])`.

**Alternative:** Add `@pytest.mark.xfail` decorators to individual test functions.

**Why YAML-driven:** Adding a new known violation for a new API requires only a YAML edit — no test file changes. The `verify_bug_markers.py` guard checks YAML coverage as a valid alternative to function-level decorators.

---

## 3. HttpClient as the Only HTTP Entry Point

**Decision:** `apitf/http_client.py` wraps `requests.Session`. All tests use `HttpClient` — never `requests.get()` directly.

**Why:** HTTPS enforcement, retry logic, and response timing are encapsulated once. If a new retry strategy or timing mechanism is needed, it changes in one place. Mock tests (which bypass `HttpClient`) would miss production-level behaviours — this framework always tests against live endpoints (Rule 17).

---

## 4. BaseValidator Contract — Collect ALL Errors, Never Short-Circuit

**Decision:** `validate()` calls `self._fail()` (accumulates) rather than raising or returning early. Returns `self._pass()` exactly once, at the end.

**Why:** Short-circuiting hides multiple schema bugs. If a response is missing both `name` and `capital`, raising on the first missing field means the second bug is invisible until the first is fixed. Accumulating all errors gives a complete picture in one test run.

---

## 5. 4-Stage CI Pipeline (Not Full Cartesian Matrix)

**Decision:** 6 total jobs — 1 smoke (ubuntu/3.11), 2 platform (windows+mac/3.11), 2 versions (ubuntu/3.9+3.12), 1 gate.

**Alternative:** Full cartesian product — 3 OS × 4 Python = 12 jobs.

**Why:** OS bugs and Python version bugs are independent dimensions. Testing each dimension on its own is sufficient — a Windows Python 3.9 run adds no signal beyond Windows/3.11 + Ubuntu/3.9. 12 jobs would use 2× the runner budget for no additional bug detection. Rationale documented in Framework Rule 26.

---

## 6. `SLA_FAILURE_EXCEPTIONS` Adapter (Platform-Agnostic xfail)

**Decision:** SLA violation xfail markers import `SLA_FAILURE_EXCEPTIONS` from `apitf/sla_exceptions.py` rather than inlining `(AssertionError, requests.exceptions.ConnectionError)`.

**Why:** On Linux, a timeout exhausts urllib3 retries and raises `ConnectionError`. On Windows, a `ConnectionResetError` causes urllib3 to retry but accumulate 30s+, resulting in a 200 OK response that is too slow → `AssertionError`. Both are the same SLA violation. A single symbol captures both. If a third exception type is found on a new platform, one file changes — not every xfail decorator.

---

## 7. `verify_bug_markers.py` as Machine-Enforced Gate

**Decision:** `scripts/verify_bug_markers.py` is installed as a git pre-push hook by `python scripts/setup_hooks.py`. Every push is blocked if an open `QUALITY_FAILURE` bug lacks a matching `xfail` marker.

**Why:** A rule without enforcement is a suggestion. Earlier in the project, xfail markers were silently dropped during a rebase, causing CI to show `FAILED` instead of `XFAIL`. The pre-push hook makes that impossible — you cannot push without every open bug being marked. This is Framework Rule 8a.

---

## 8. `test_security.py` and `test_baseline.py` — Zero Code Changes for New APIs

**Decision:** Security (RFC 7231 + OWASP) and baseline (HTTPS/2xx/404/perf) tests are fully config-driven. Adding `base_url` to YAML is sufficient for baseline; adding a `security` block triggers security tests.

**Why:** The 3-step extensibility gate (Rule 5) mandates that adding a new API should require only: YAML entry + validator + test file. Security and baseline coverage should be free. These test files parametrize from YAML at collection time — no edits needed.

---

## 9. Installable Package (`apitf/` + `pyproject.toml`)

**Decision:** Framework code lives in the `apitf/` package. Installed via `pip install -e ".[test]"` (editable mode).

**Alternative:** `src/` layout with `PYTHONPATH` manipulation or `conftest.py` path insertion.

**Why:** An installable package is the correct Python packaging practice. `pip install -e ".[test]"` installs both the package and test dependencies in one command. `pyproject.toml` replaces the dual `requirements.txt`/`setup.py` pattern. CI uses the same install command as developers.

---

## 10. Cross-Platform Scripts (Python, Not Bash)

**Decision:** `scripts/push.py` and `scripts/setup_hooks.py` are Python, not shell scripts. The git hook is written as a Python script.

**Why:** Bash scripts require WSL on Windows. The framework targets all three platforms. A Python script works identically on macOS, Linux, and Windows (with Python installed, which is already a prerequisite).
