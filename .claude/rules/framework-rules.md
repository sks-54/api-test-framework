# Framework Rules — Multi-Environment API Test Framework

These rules govern how phases are implemented, reviewed, committed, and merged.
Violations are tracked in CLAUDE_LOG.md as STRUCTURAL_FAILURE.

---

## Rule 1 — Zero Hardcoded Values

`config/environments.yaml` is the single source of truth for all thresholds,
base URLs, timeouts, and numeric limits. Module-level constants are only
permitted as cached/derived values loaded from YAML at import time — never as
primary definitions. Magic literals in test bodies are forbidden.

```python
# CORRECT — derived from YAML
MAX_RESP_MS = env_config["thresholds"]["max_response_time"] * 1000

# FORBIDDEN — primary definition outside YAML
MAX_RESP_MS = 2000
```

When a test reads `env_config`, it reads the loaded representation of
`config/environments.yaml`. The two names refer to the same data.

## Rule 2 — URL Atomicity (Framework-wide)

URLs (`https://`) are atomic units everywhere in this codebase.
Never split across lines, string concatenations, f-strings spanning lines,
or multiline expressions. Always assign the complete URL to a named variable
on a single line. See `document-parsing.md` Rule 1 for the parser-specific
implementation pattern (regex group extraction).

## Rule 3 — Validator Contract

All response validation must use a `BaseValidator` subclass. The contract:
- `validate()` collects ALL errors — never short-circuits mid-loop
- Returns `ValidationResult` via `self._pass()` at the end (always)
- Ad-hoc `assert "field" in response` inside test files is forbidden

## Rule 4 — Test Isolation and Fixture Scoping

Each test must be independently runnable. No test may depend on execution
order or shared mutable state.

Allowed fixture scopes:
- `function` (default) — stateful or write fixtures
- `session` — read-only config only (`env_config`)
- `module` / `class` — only for grouping related setup with no side-effects

Shared helpers (auth setup, custom request builders) belong in `src/` or
`tests/conftest.py`, never duplicated per test file.

## Rule 5 — Extensibility Gate

The three-step path is the minimum required to add a new API:
1. Add entry to `config/environments.yaml`
2. Add `src/validators/<new>_validator.py` extending `BaseValidator`
3. Add `tests/test_<new>.py` using the `environment` fixture

Auth, custom fixtures, and shared helpers are permitted only via shared
modules in `src/` or `conftest.py` — never as per-API scaffolding that
breaks the three-step contract. If the minimum drifts above three steps,
flag as STRUCTURAL_FAILURE.

## Rule 6 — Dependency Management (Dry-Run Before Install)

Before any `pip install`, run `pip install --dry-run -r requirements.txt` and
confirm no conflicts. Version ranges must be testable against Python 3.9–3.12.
When adding a new dependency, verify the version range exists on PyPI before
committing.

## Rule 7 — Opus Review Must Include requirements.txt

Every Opus advisor review prompt must include the current contents of
`requirements.txt` alongside the phase diff. Omitting it caused the
`pytest-retry` version bug (>=0.6 didn't exist — caught only after CI failed).

## Rule 8 — Pre-Push Checklist (Non-Negotiable)

Before any `git push`:
1. `pip install --dry-run -r requirements.txt` — no conflicts
2. `pytest --collect-only -q` — import errors surface here
3. `python -c "import yaml; yaml.safe_load(open('config/environments.yaml'))"` — YAML valid
4. Company name scan (see Rule 12)
5. `python -m mypy src/ tests/ --ignore-missing-imports` — no type errors
6. `python scripts/verify_bug_markers.py` — every open bug in BUG_REPORT.md has a matching `@pytest.mark.xfail`

Step 6 is the guard against xfail markers being silently dropped during rebases or merges.
If it exits non-zero, do not push — add the missing xfail before proceeding.

## Rule 9 — No Direct Pushes to Main

`main` is branch-protected. All changes arrive via PR. Direct commits to main
are forbidden. Hotfixes use `fix/<topic>` branches with a PR + Quality Gate.

## Rule 10 — Failure Categorization

Every CI failure must be categorized before investigation:
- `ENV_FAILURE` — network/API unavailability. Auto-retry up to 2 times with
  60s backoff. After 2 retries, mark quarantined in CLAUDE_LOG.md and skip
  review iterations. Do not consume iteration budget.
- `QUALITY_FAILURE` — assertion failed, schema mismatch, wrong status code.
- `STRUCTURAL_FAILURE` — import error, missing fixture, YAML parse error.

Only QUALITY_FAILURE and STRUCTURAL_FAILURE consume review iterations.

## Rule 11 — Review Iteration Budgets

- Test plans: max 3 Opus review iterations.
- Code phases: max 5 Opus review iterations.

Escalation after budget exhausted: add a CLAUDE_LOG.md entry, tag the PR
`needs-human-review`, and require user approval before merge proceeds.
Infinite retry loops on ENV_FAILUREs are prohibited.

## Rule 12 — Company Name Sanitization Scan

Before every PR push, run a case-insensitive grep for company-specific terms
across all tracked files. If found, fix before push — never push with them.

```bash
grep -ri "panw\|palo alto\|paloalto" . \
  --include="*.py" --include="*.yaml" --include="*.yml" \
  --include="*.md" --include="*.txt" --include="*.json"
```

## Rule 13 — Opus Advisor Review Is a Mandatory Pre-Commit Gate

Opus review is NOT optional and NOT triggered manually. It MUST run before
`git add` for every phase. The sequence is:

```
generate → Opus review → address deviations → Opus re-review (if needed)
         → only then: git add / git commit / git push
```

If Opus review is skipped, the phase is incomplete — do not commit.
This applies to: test plans, code phases, README, CI config, and rules files.

The advisor is invoked via `Agent(model="opus", prompt="...")`.

Include in every review prompt:
- Full diff of all changed files
- Current `requirements.txt`
- All rules files whose glob matches any changed file, plus framework-rules.md always
- Phase rubric (pass_threshold, rules list)

## Rule 14 — Secrets and Credentials

API keys, tokens, and credentials must never appear in source files, logs, or
CI output. Credentials are loaded exclusively from environment variables.

```python
# CORRECT
api_key = os.environ["ANTHROPIC_API_KEY"]

# FORBIDDEN
api_key = "sk-ant-..."  # hardcoded
```

`.env` files are gitignored. The pre-push checklist (Rule 8) must be extended
with a secret-pattern scan if new credential types are introduced.

## Rule 15 — Logging Standards

Use a named logger per module. Never log PII. Always use the `logging` module.

```python
import logging
logger = logging.getLogger(__name__)

# CORRECT
logger.warning("Parse error on line %d: %r", lineno, line)

# FORBIDDEN
print(f"Error: {line}")     # print in non-test code
logger.debug(f"{user_email}")  # PII in logs
```

Log level guidance: DEBUG for trace/parse detail, INFO for phase milestones,
WARNING for recoverable issues, ERROR for caught exceptions.

## Rule 16 — Tests Encode the Spec Contract, Not Observed API Behavior

Tests assert what the API **should** return per its specification, not what it
currently returns. When an API deviates from the spec, the test must fail and
the bug reporter captures it. Never widen an assertion to make a failing test
pass — a passing test that accepts a wrong response is worse than a failing one.

```python
# CORRECT — asserts specified contract; bug is surfaced on deviation
assert resp.status_code == 404, (
    f"Expected 404 (resource not found), got {resp.status_code}. "
    f"Spec deviation — report as bug."
)

# FORBIDDEN — hides the API bug
assert resp.status_code in (400, 404)
assert 400 <= resp.status_code < 500
```

The role of the QA engineer is to detect deviations and surface them as
structured bug reports. High pass rates achieved by accepting incorrect
responses provide false confidence.

## Rule 17 — Always Test Against Real Endpoints

Tests must always run against the real live API endpoints specified in
`config/environments.yaml`. Mocking, stubbing, or intercepting HTTP responses
in test files is forbidden.

Rationale: mocked tests caught a prod migration failure only after it shipped
(similar incident documented in Rule 6). If the live endpoint is unavailable,
classify the failure as ENV_FAILURE (Rule 10) and retry — do not substitute a
mock. Test doubles belong in unit tests of src/ internals only, never in
`tests/test_*.py` files that verify API contract.

```python
# CORRECT — HttpClient hits the real endpoint
resp = HttpClient(cfg["base_url"]).get("/name/germany")

# FORBIDDEN — mocked response bypasses the real contract
with responses.activate():
    responses.add(responses.GET, url, json=[...], status=200)
    resp = client.get("/name/germany")
```

## Rule 18 — Mandatory CI Monitoring After Every Push

After every `git push` or PR creation, immediately monitor CI until all checks
complete. Do NOT move to the next task while CI is running.

```bash
gh pr checks <PR_NUMBER> --watch   # blocks until all checks complete
gh pr checks <PR_NUMBER>           # one-shot status read
```

For every failed check:
1. Categorize the failure (ENV_FAILURE / QUALITY_FAILURE / STRUCTURAL_FAILURE)
2. If QUALITY_FAILURE or STRUCTURAL_FAILURE: file a GitHub issue (Rule 19)
3. Root-cause and fix before moving on
4. Do NOT merge a PR with an unresolved non-ENV failure

This rule exists because PRs were being pushed and abandoned without monitoring,
leaving failures undiscovered until the user asked.

## Rule 19 — Every CI Failure Must Become a GitHub Issue Before Merge

When CI fails with QUALITY_FAILURE or STRUCTURAL_FAILURE:
1. File a GitHub issue immediately using `gh issue create`
2. Label: `bug` + `quality-failure` or `structural-failure`
3. Title format: `[BUG] <test_name> — <one-line description>`
4. Body: 5-section format (Title, Steps, Expected, Actual, Data)
5. For known API bugs where test is correct: mark test `@pytest.mark.xfail(strict=True, reason="Known API bug #<issue>: ...")`
6. PR cannot be merged until every failure is either fixed or has an open GitHub issue with `xfail` marker

`xfail(strict=True)` means: test runs, expected to fail (bug documented), but if
the API fixes the bug the test becomes `xpass` which alerts us to remove the marker.

## Rule 20 — Session Start Protocol (Opus Project Audit)

Every new session MUST begin with an Opus audit before any implementation work.
This is the fix for Opus being a one-shot reviewer instead of an always-on overseer.

The session start protocol:
1. Read `CLAUDE_LOG.md` for current phase status
2. Run `gh pr list` and `gh pr checks` on all open PRs
3. Run `gh issue list --label bug` for unfiled known bugs
4. Spawn `Agent(model="opus")` with: DELIVERABLES.md, open PR status, open issues,
   CLAUDE_LOG.md, and ask: "What is the current project state vs spec? What must
   happen next? What gaps or process violations are you seeing?"
5. Act on Opus's direction before starting any new implementation

This rule exists because Opus has no persistent state — it only knows what is
in its prompt. The session start protocol ensures Opus always has full context
before advising.

## Rule 21 — SLA Violations Are Bugs, Not Flakiness

Response time SLAs are defined in `config/environments.yaml` under
`thresholds.max_response_time`. An endpoint that consistently exceeds this
threshold is violating its SLA contract — that is a bug, not transient noise.

**Distinction:**
- `@pytest.mark.flaky(reruns=2)` is for *transient* network issues (ENV_FAILURE:
  one-off timeout, DNS blip). A single retry is acceptable.
- If a test fails on **all reruns** (all 3 attempts), the failure is *consistent*
  and must be treated as a confirmed bug, not a flaky ENV_FAILURE.

**Protocol when a performance or timeout test exhausts all reruns:**
1. Categorize as `SLA_VIOLATION` (sub-type of QUALITY_FAILURE)
2. File a GitHub issue immediately:
   - Label: `bug`, `sla-violation`
   - Title: `[BUG] SLA: <endpoint> response time > <threshold>ms consistently`
   - Body: test name, measured times across all attempts, threshold, environment
3. Mark the test `@pytest.mark.xfail(strict=True, reason="SLA violation #<issue>...")`
   so CI can pass while the bug is tracked
4. Do NOT raise `max_response_time` in YAML to make the test pass — that hides the bug

```python
# CORRECT — SLA from config, never hardcoded
max_ms = env_config["thresholds"]["max_response_time"] * 1000
assert resp.response_time_ms < max_ms, (
    f"SLA violation: {resp.response_time_ms:.0f}ms > {max_ms:.0f}ms. "
    f"File as bug if consistently failing across reruns."
)

# FORBIDDEN — hiding the SLA
max_ms = 10_000  # raised to "fix" the test
```

## Rule 22 — Pre-Commit Assertion Integrity Check

Before every `git add` on test files, scan for forbidden assertion patterns that
hide spec deviations:

```bash
grep -n "status_code in (" tests/test_*.py && echo "FORBIDDEN: widened assertion"
grep -n ">= [0-9].*<" tests/test_*.py | grep "status_code" && echo "FORBIDDEN: range assertion on status"
```

If either grep returns a match, it is a pre-commit gate failure. Fix by:
1. Asserting the exact expected status code
2. Filing a GitHub issue for the spec deviation
3. Marking the test `xfail(strict=True, raises=AssertionError, reason="Bug #<issue>: ...")`

## Rule 23 — Post-Rebase Bug Marker Verification

After every `git rebase`, `git merge`, or `git cherry-pick` that resolves conflicts, before `git push`:
1. Run `python scripts/verify_bug_markers.py` immediately
2. Any conflict resolution that takes `--theirs` or `--ours` can silently drop xfail markers
   added in a later commit whose context conflicts with the resolved base
3. If markers are missing, re-add them manually — never skip this step
4. This rule applies equally to `git merge`, squash-merges from GitHub UI, and `git cherry-pick`

```bash
# After any rebase/merge/cherry-pick completes:
python scripts/verify_bug_markers.py  # catches missing markers immediately
# Non-zero exit → add missing @pytest.mark.xfail(strict=True, ...) to the test, commit, then push
```

This rule was added after xfail markers for BUG-001/002/003 were silently dropped
during a rebase, causing TC-C-004 to show as FAILED instead of XFAIL in CI.

## Rule 24 — Bug Reports Must Include curl Reproduction Command

Every entry in `BUG_REPORT.md` must include a `curl` command that reproduces the bug.
This allows any engineer to independently reproduce the issue without setting up the test framework.

```bash
# Format — paste this into the bug's Steps to Reproduce section:
curl -s "https://api.example.com/v1/endpoint?param=value" | python3 -m json.tool
```

Requirements:
- The curl URL must be complete and runnable as-is (no placeholder substitution needed)
- Include `-s` (silent) and pipe to `python3 -m json.tool` for readable JSON output
- If the bug requires request headers, include them with `-H "Header: value"`
- Add a one-line comment above the curl showing what the expected vs actual status code is

When adding a new bug entry, always include the curl command before filing the GitHub issue —
confirm the curl reproduces the bug locally first, then add both to BUG_REPORT.md and the issue body.

## Rule 25 — Acknowledged Changes Are Not Complete Until Written to a File

A change discussed or agreed upon in conversation is **not done** until it exists in a committed file.
There is no "I'll do that" — only "I did that (see commit X)."

This applies to:
- Rule changes (framework-rules.md, testing-standards.md, etc.)
- Protocol changes (CLAUDE.md, CI config)
- Bug report updates (BUG_REPORT.md, CLAUDE_LOG.md)
- Deliverable status changes (DELIVERABLES.md)

**Pattern that violates this rule:** A design decision is made in conversation (e.g., CI should skip doc-only pushes), acknowledged verbally, then omitted from the actual file. The commit goes out with the old behavior. Subsequent Opus reviews find the discrepancy.

**Enforcement:** After any verbal agreement on a change, the implementer must immediately:
1. Write the change to the appropriate file
2. Include it in the next commit
3. Reference the change in the commit message

No partial acknowledgements. If it wasn't committed, it didn't happen.

## Rule 26 — CI Matrix Design: Test Dimensions Independently, Not as a Cartesian Product

OS compatibility and Python version compatibility are independent dimensions. Testing every
OS × every Python version produces a cartesian product that grows quadratically and provides
almost no additional signal beyond testing each dimension separately.

**Why they are independent:**
- OS bugs (path separators, encoding, tempfile locations) do not change with Python minor version
- Python version bugs (deprecated syntax, stdlib removals, type-hint changes) do not change by OS

**The correct structure (6 jobs):**
```
Stage 1 — Smoke     : ubuntu / 3.11      → fast-fail on import errors; proves basic correctness
Stage 2 — Platform  : windows/3.11
                      mac/3.11           → proves OS compat on one stable Python version
Stage 3 — Versions  : ubuntu / 3.9
                      ubuntu / 3.12      → proves version-boundary compat on cheapest runner
Stage 4 — Gate      : always()           → blocks merge if any stage failed
```

**Why only 3.9 and 3.12 in the version stage:**
If code works on the oldest (3.9) and newest (3.12) supported Python, it works on every
intermediate version. Intermediate versions (3.10, 3.11) add no signal and double the cost.
3.11 is already covered by smoke and platform.

**Forbidden patterns:**
- Full cartesian product (3 OS × 4 Python = 12 jobs) — the default that GitHub suggests
- Running the version sweep on windows/mac (OS compat is already proven; just wastes budget)
- Adding 3.10 to the version matrix (intermediate version, no additional signal)

**When to revisit:** If a new OS-specific Python bug is found (e.g., a Windows-only issue on
3.12), add a targeted `exclude:` or a specific extra job — do not expand back to full cartesian.

## Rule 27 — Keep GitHub Actions on the Current Node.js Runtime

GitHub Actions deprecates Node.js runtimes on a published schedule. Running stale action
versions produces `##[warning]Node.js XX actions are deprecated` in every CI log and will
become hard failures when GitHub removes the old runtime from runners.

**Protocol:**
1. At session start, if any CI run contains a Node.js deprecation warning, update the
   affected actions before doing any other work.
2. Pin actions to the latest major version tag that ships the current Node.js runtime.
   Check latest versions with:
   ```bash
   gh api repos/actions/checkout/releases/latest --jq '.tag_name'
   gh api repos/actions/setup-python/releases/latest --jq '.tag_name'
   gh api repos/actions/cache/releases/latest --jq '.tag_name'
   gh api repos/actions/upload-artifact/releases/latest --jq '.tag_name'
   ```
3. Update `.github/workflows/ci.yml` immediately — do not defer.
4. Add the version bump to the same commit as any other CI change in progress.

**Why this matters:** The warning is a deadline, not a suggestion. GitHub publishes a
removal date. If the runner removes Node.js 20 and actions still pin to v4/v5 Node.js 20
builds, CI silently breaks on all branches simultaneously.

```yaml
# CORRECT — current Node.js 24-compatible versions (as of 2026-04-19)
uses: actions/checkout@v6.0.2
uses: actions/setup-python@v6.2.0
uses: actions/cache@v5.0.5
uses: actions/upload-artifact@v7.0.1

# STALE — triggers Node.js 20 deprecation warning
uses: actions/checkout@v4.2.2
uses: actions/setup-python@v5.5.0
uses: actions/cache@v4.2.3
uses: actions/upload-artifact@v4.6.2
```
