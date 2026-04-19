# Rules Reference

Summary of the 27 framework rules. Full text in `.claude/rules/framework-rules.md`.

## Enforcement Summary

| Mechanism | Rules |
|-----------|-------|
| Pre-push hook (blocks push) | Rule 8 Step 6 — `verify_bug_markers.py` |
| Push wrapper (blocks terminal) | Rule 18 — `scripts/push.py` calls `gh run watch` |
| CI quality gate (blocks merge) | Rule 19 — gate job requires all stages green |
| Checklist (run before push) | Rules 8 Steps 1-5, Rule 12 |

---

## Core Rules

| # | Rule | Enforcement |
|---|------|-------------|
| 1 | No hardcoded values — YAML is single source of truth | Code review + tests fail if hardcoded |
| 2 | URL atomicity — never split `https://` across lines | Code style review |
| 3 | Validator contract — collect ALL errors, never short-circuit | Code review |
| 4 | Test isolation — each test independently runnable | pytest by design |
| 5 | 3-step extensibility gate — adding API must not exceed 3 steps | Architectural review |
| 6 | Dry-run dependencies before install | Rule 8 Step 1 |
| 7 | Opus review must include requirements.txt | Process |
| 8 | Pre-push checklist (6 steps) | Git hook (Step 6), push wrapper (Rule 18) |
| 8a | Every rule must be enforced by a mechanism | Meta-rule |
| 9 | No direct pushes to main | Branch protection |
| 10 | Failure categorization before investigation | Process |
| 11 | Review iteration budgets (max 5 per phase) | Process |
| 12 | Company name scan before every push | Rule 8 checklist |
| 13 | Opus review is a mandatory pre-commit gate | Process |
| 14 | No secrets in source files | Code review |
| 15 | Named logger per module, no PII, no print() | Code review |
| 16 | Tests encode spec contract, not observed behavior | Code review — widened assertions are FORBIDDEN |
| 17 | Always test against real endpoints — no mocking | Code review |
| 18 | Mandatory CI monitoring after every push | `scripts/push.py` blocks terminal |
| 19 | Every CI failure → GitHub issue before merge | Branch protection + gate job |
| 20 | Session-start Opus project audit | Process |
| 21 | SLA violations are bugs, not flakiness | Bug categorization protocol |
| 22 | SLA xfail markers must use `SLA_FAILURE_EXCEPTIONS` | Code review |
| 23 | Pre-commit assertion integrity check | Grep scan |
| 23b | Post-rebase bug marker verification | Run `verify_bug_markers.py` after every rebase |
| 24 | Bug reports must include curl reproduction command | BUG_REPORT.md format |
| 25 | Acknowledged changes must be written to a file | Process |
| 26 | CI matrix: test dimensions independently | Architectural decision (6 jobs, not 12) |
| 27 | Keep GitHub Actions on current Node.js runtime | Update actions at session start if warnings present |

## Key Forbidden Patterns

```python
# FORBIDDEN: widened status assertion (Rule 16)
assert resp.status_code in (400, 404)
assert resp.status_code >= 400

# FORBIDDEN: hardcoded threshold (Rule 1)
assert resp.response_time_ms < 2000

# FORBIDDEN: direct requests import in test file (Code Style Rule 4)
import requests
resp = requests.get("https://...")

# FORBIDDEN: mocking the HTTP layer (Rule 17)
with responses.activate():
    responses.add(responses.GET, url, json=[...])

# FORBIDDEN: inline SLA exception tuple (Rule 22)
@pytest.mark.xfail(raises=(AssertionError, requests.exceptions.ConnectionError))
```
