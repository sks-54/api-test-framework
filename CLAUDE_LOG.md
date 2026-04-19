# CLAUDE_LOG.md — API Test Framework

Persistent audit log for this project.
All entries are append-only. Resolved entries are marked but never deleted.

---

## Phase Status

| Phase | Name | Status | PR | Notes |
|-------|------|--------|----|-------|
| 1 | Scaffold + Config | MERGED | #1 | environments.yaml, cities.json, pytest.ini |
| 2 | Core Framework | MERGED | #2 | src/ — http_client, validators, spec_parsers, reporters |
| 3 | Tests | OPEN | #4 | test_countries.py (21 tests) + test_weather.py (10 tests) |
| 4 | Reporting | MERGED with Phase 2+3 | #4 | bug_reporter.py, deliverables_tracker.py, Allure config |
| 5 | CI Pipeline | MERGED | #3 | 3-OS × 4-Python matrix, artifact upload |
| 6 | Claude Code Artifacts | MERGED with Phase 2 | #2 | rules/, skills/, scripts/advisor_review.py |
| 7 | README + Tag | PENDING | — | README.md missing; v1.0.0 tag pending |

---

## Known Bugs

| Bug | Test | Severity | Category | Status | Title |
|-----|------|----------|----------|--------|-------|
| BUG-001 | TC-C-004 | P2 | QUALITY_FAILURE | OPEN | `/alpha/ZZZ999` returns 400 instead of 404 |
| BUG-002 | TC-W-004 | P2 | QUALITY_FAILURE | OPEN | `/forecast` without lat/lon returns 200 silently |
| BUG-003 | TC-C-021 | P3 | QUALITY_FAILURE | OPEN | 5 territories return `population=0` |
| BUG-004 | TC-W-004, TC-W-010 | P1 | SLA_VIOLATION | OPEN | Open-Meteo `/forecast` times out in CI consistently |

All bugs have filed GitHub issues. See `BUG_REPORT.md` for curl reproduction commands.

---

## Multi-Agent Workflow

This project uses a two-agent system:

- **Sonnet (Implementer)** — generates code, runs tests, monitors CI, files issues
- **Opus (Advisor)** — one-shot code review via `Agent(model="opus")` before each commit

Invocation pattern per Rule 13:
```python
Agent(
    model="opus",
    prompt=f"""
    Phase: {phase_name}
    Diff:
    {diff}
    Rules in scope: framework-rules.md, testing-standards.md, code-style.md
    Task: Score this implementation against the rules. List deviations. Required vs recommended fixes.
    """,
)
```

### Opus Review Log

| Date | Phase | Score | Required Fixes | Resolved |
|------|-------|-------|----------------|---------|
| 2026-04-18 | Phase 2+3+4+6 initial | — | pdf_parser hardcoded thresholds (Rule 1 violation) | Yes — `_UNRESOLVED_THRESHOLDS = {}` |
| 2026-04-19 | Phase 3 re-review | 72/100 | (1) verify_bug_markers regex broken by multi-line reasons (2) Rule 22/23 ordering wrong (3) CLAUDE.md dropped "act on Opus direction" step (4) TC-W-010 range assertion `in (200, 400)` violated Rule 16 | Yes — all 4 fixed; verify_bug_markers rewritten with ast.parse |

---

## Process Violations

| Date | Rule | Violation | Fix Applied |
|------|------|-----------|-------------|
| 2026-04-19 | Rule 23 | xfail markers for BUG-001/002/003 silently dropped during `git checkout --theirs tests/test_countries.py` in rebase | Re-added manually; `scripts/verify_bug_markers.py` created as pre-push guard (Rule 8 Step 6) |
| 2026-04-19 | Rule 16 | TC-W-010 asserted `resp.status_code in (200, 400)` — widened assertion hides spec deviation | Fixed to `assert resp.status_code == 200` + WeatherValidator schema check |
| 2026-04-19 | Rule 19 | BUG-004 filed in BUG_REPORT.md but GitHub issue not filed immediately | Filed as Issue #8 — label bug,sla-violation |
| 2026-04-19 | Rule 20 | Session start skipped Opus audit (Rule 20) on several iterations | Protocol re-added to CLAUDE.md; enforced going forward |

---

## Architectural Decisions

| Decision | Rationale | Alternative Rejected |
|----------|-----------|---------------------|
| `ast.parse` for xfail detection in verify_bug_markers.py | Regex broken by decorator ordering, multiline reason strings, `@` characters in adjacent decorators | Regex `@pytest.mark.xfail[^@]+?BUG-\d+` — too fragile |
| `xfail(strict=True, raises=AssertionError)` for QUALITY_FAILURE bugs | CI passes, xpass alerts if API fixes bug | Removing failing test — hides the bug |
| SLA_VIOLATION bugs NOT xfailed | Timeouts throw `ConnectionError`, not `AssertionError` — xfail(raises=AssertionError) would not catch them | xfailing SLA tests — wrong exception type silently passes |
| `@pytest.mark.flaky(reruns=2)` on weather tests | Open-Meteo has intermittent latency; 3 total attempts separate transient from consistent | No retry — too many false ENV_FAILUREs in CI |
| `BUG_REPORT.md` as accumulated file with curl field (Rule 24) | Curl lets any engineer reproduce without framework setup | Linking only to pytest output — not runnable without env |
| Rebase over merge for conflict resolution | Linear history; merge commits obscure phase progression | `git merge origin/main` — creates diamond graph in history |

---

## Rules Added This Session

| Rule | Added | Trigger |
|------|-------|---------|
| Rule 21 — SLA Violations Are Bugs | 2026-04-19 | Open-Meteo timeouts exhausted all reruns — needed protocol |
| Rule 22 — Pre-Commit Assertion Integrity Check | 2026-04-19 | TC-W-010 had `in (200, 400)` widened assertion |
| Rule 23 — Post-Rebase Bug Marker Verification | 2026-04-19 | xfail markers silently dropped during rebase |
| Rule 24 — Bug Reports Must Include curl | 2026-04-19 | User requested curl-reproducible bug reports |

---

## CI Observations

| Run | Commit | Result | Notes |
|-----|--------|--------|-------|
| 24625148611 | — | TC-W-004 timeout all reruns | SLA_VIOLATION filed as BUG-004 |
| 24625149041 | — | TC-W-010 timeout all reruns | Same root cause as BUG-004 |
| PR #4 latest | 5b3d60e | macOS: PASS; ubuntu/windows: pending | Smoke job: PASS |
