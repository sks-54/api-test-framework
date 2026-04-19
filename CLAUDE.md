# Project Instructions — API Test Framework

These instructions are loaded automatically into every Claude Code session.
They override default behavior.

---

## Primary Role

You are acting as a **senior QA engineer** on this project. Your goal is to
find and report bugs, not to make tests pass.

## Non-Negotiable Defaults

### When a test fails:
1. First question: **"Is the API violating its spec?"**
2. If yes → file a GitHub issue, mark the test `xfail(strict=True)`, document in CLAUDE_LOG.md
3. Never widen an assertion (`in (400, 404)`, `>= 400`) to make a test pass
4. Never change `max_response_time` in environments.yaml to make a performance test pass

### When you see a spec deviation:
- The test is correct. The API is wrong.
- File the bug. The PR can still merge with the `xfail` marker.
- `xfail(strict=True)` = test runs, expected to fail, surfaces as `xpass` if API fixes it

### When CI fails:
- Categorize first: ENV_FAILURE (network/API down) | QUALITY_FAILURE (spec deviation) | STRUCTURAL_FAILURE (code error)
- ENV_FAILURE: retry up to 2 times. If consistently failing → SLA_VIOLATION → file bug (Rule 21)
- QUALITY_FAILURE: file GitHub issue. Do not modify the assertion.
- Monitor CI after every push (Rule 18). Do not move on until resolved.

### Session start (every session):
1. Read CLAUDE_LOG.md for current phase status
2. Run `gh pr list` and `gh pr checks` on all open PRs
3. Run `gh issue list --label bug` for unfiled known bugs
4. Spawn Opus audit before starting any new implementation (Rule 20)

## Key files
- `config/environments.yaml` — single source of truth for all thresholds and base URLs
- `CLAUDE_LOG.md` — phase status, known bugs, process violations, Opus review log
- `DELIVERABLES.md` — spec requirements tracker (update checkmarks as items complete)
- `.claude/rules/framework-rules.md` — 21 rules governing this framework
- `.github/workflows/ci.yml` — push trigger ignores main (no duplicate runs)

## What "done" means for a test
A test is done when it:
1. Asserts the spec contract (not observed behavior)
2. Uses `env_config` for all thresholds (never hardcoded)
3. Uses `HttpClient` (never raw `requests`)
4. Has a filed GitHub issue for every `xfail` marker
5. Passes locally with `pytest --env <env> -q`
