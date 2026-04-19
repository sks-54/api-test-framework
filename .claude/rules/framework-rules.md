# Framework Architecture Rules

These rules govern the architecture and constraints of this test framework.
They are specific to this codebase — not generic Python style.
Claude Code and Opus advisor must enforce these on every review.

---

## Rule 1 — Zero Hardcoded Values

- All URLs must live in `config/environments.yaml` — never in test files, fixtures, or src/
- All thresholds (`max_response_time`, `min_results_count`) must be read from `env_config` fixture — never hardcoded in test assertions
- `src/spec_parser/` parsers must return `thresholds={}` — callers resolve against `environments.yaml`
- **Violation example:** `assert response_time < 2.0` ← hardcoded; correct: `assert response_time < env["thresholds"]["max_response_time"]`

## Rule 2 — URL Atomicity

- URLs (`http://` or `https://`) are atomic units — never split across lines, string concatenations, f-strings spanning lines, or multiline expressions
- Always assign the complete URL to a named variable on a single line
- Parser chunks must not break mid-URL — page joins must use whitespace separators
- **Violation example:** `url = base + "/region/" + region` ← must use `urljoin` or be a single expression
- **Correct:** `base_url: https://restcountries.com/v3.1` (single line in YAML)

## Rule 3 — Validator Contract

- All validators must extend `src/validators/base_validator.BaseValidator`
- `validate()` must collect ALL errors — never short-circuit on first failure
- New API = new validator subclass. Framework code never handles per-API schema logic directly.

## Rule 4 — Test File Isolation

- Test files must not import from other test files
- All shared state flows through fixtures defined in `tests/conftest.py`
- `conftest.py` is the single source of `base_url` and `thresholds` — never re-read `environments.yaml` inside a test

## Rule 5 — Extensibility Contract

Adding a new API requires exactly these steps — no more, no fewer:
1. Add entry to `config/environments.yaml`
2. Add `src/validators/<name>_validator.py` extending `BaseValidator`
3. Add `tests/test_<name>.py` using the `env_config` fixture

Zero changes to: `conftest.py`, `http_client.py`, `ci.yml`, or any existing test file.

## Rule 6 — Dependency Management

- All packages beyond the 4 spec-required packages (`pytest`, `requests`, `allure-pytest`, `pyyaml`) must be documented with an inline comment explaining why they are needed
- Version ranges must be verified against PyPI before committing — use `pip install --dry-run -r requirements.txt`
- Upper bounds must be set on all packages to guard against major-version breakage
- **Root cause of past failure:** `pytest-retry>=0.6,<1.0` — no such version range exists. Caught by CI, missed by Opus because `requirements.txt` was excluded from review prompt.

## Rule 7 — Opus Review Completeness

Every Opus advisor review prompt MUST include:
- All modified source files
- `requirements.txt` (always — dependency issues are not caught by code review alone)
- `config/environments.yaml` (always)
- `.github/workflows/ci.yml` (when modified)
- The full eval rubric (not abbreviated)

Incomplete review inputs are a framework violation — they caused real CI failures (see CLAUDE_LOG.md).

## Rule 8 — Pre-Push Checklist (mandatory, automated)

Before every `git push`, the following must pass locally:

```bash
# 1. Dependency install check (catches bad version ranges)
pip install --dry-run -r requirements.txt

# 2. Test discovery check (catches import errors, missing fixtures)
pytest --collect-only -q

# 3. CI YAML syntax check (catches workflow errors before GitHub rejects them)
python3 -m py_compile .github/workflows/ci.yml 2>/dev/null || \
  python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && \
  echo "CI YAML OK"
```

All three must exit 0 (or exit 5 for pytest — "no tests collected" is valid in early phases).

## Rule 9 — Branch Protection

- `main` is protected — no direct pushes ever
- All changes arrive via PR, including hotfixes
- Every PR must pass the `Quality Gate` CI job before merge
- Force pushes to `main` are disabled
- PRs must not be merged with known failures unless root cause is documented in the PR description and labeled `known-env-issue`

## Rule 10 — Failure Categorization

The Opus advisor and CI gate classify failures into three tiers:

| Category | Description | Action |
|----------|-------------|--------|
| `ENV_FAILURE` | API server down, DNS failure, HTTP 5xx from upstream | Fail fast — skip review iterations, label PR, document root cause |
| `QUALITY_FAILURE` | Hardcoded values, missing coverage, wrong assertions, bad types | Loop — up to 3 iterations for test plans, 5 for code phases |
| `STRUCTURAL_FAILURE` | Import errors, syntax errors, missing files, bad deps | Fail fast on iteration 1 — fix before re-review |

## Rule 11 — Review Iteration Budgets

| Artifact | Max Opus iterations | Pass threshold |
|----------|--------------------|-|
| Test plans | 3 | Score ≥ 80/100 |
| Code phases | 5 | Score ≥ 80/100 |
| CI/config files | 2 | Score ≥ 80/100 |

If iteration cap is reached without passing: block merge, log in `CLAUDE_LOG.md`, require human decision.

## Rule 12 — Company Name Sanitization

Before any push to a public repo, scan all non-spec files for company-specific names:

```bash
grep -rin "panw\|palo alto\|palo-alto" \
  --include="*.py" --include="*.md" --include="*.yaml" \
  --include="*.yml" --include="*.json" --include="*.txt" \
  . | grep -v "specs/" | grep -v ".git/"
```

Must return zero matches. This is a hard gate — no exceptions.
