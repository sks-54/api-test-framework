# Deliverables Tracker

> Extracted from: `specs/home_test.PDF` — 2026-04-18
> Monitored by: Opus Advisor on every phase PR review
> Format: `[ ]` pending · `[x]` complete · `[!]` deviation detected

---

## Core Framework

- [x] `config/environments.yaml` — two environments (countries, weather) with correct thresholds
- [x] Environment fixture in top-level `conftest.py`
- [x] `--env` CLI flag via `pytest_addoption` (accepts any key from YAML dynamically)
- [x] No hardcoded URLs or thresholds anywhere in test code
- [x] `test_data/cities.json` committed to repo (5 cities with lat/lon)

## Test Cases — Countries API

- [x] `GET /region/europe` — assert result count > 40
- [x] `GET /name/germany` — schema validation (name, capital, population, currencies, languages)
- [x] `GET /all?fields=name,population` — assert every country has population > 0
- [x] Cross-reference: country from `/name` must appear in `/region` results

## Test Cases — Weather API

- [x] 5 cities parametrized from `test_data/cities.json`
- [x] Temperature range validated (-80 to 60°C)
- [x] Hourly entry count > 0
- [x] `timezone` field present in response

## Test Coverage Techniques

- [x] Boundary value analysis (count edges, temp extremes, threshold = value)
- [x] Equivalence partitioning (valid inputs grouped)
- [x] Positive / Negative test cases (valid vs invalid inputs)
- [x] State-based testing (cross-reference: /name → /region)
- [x] Error handling (404, timeout, malformed response, out-of-range)
- [x] Performance (response_time < max_response_time from YAML — never hardcoded)
- [x] Reliability (retry on 5xx)
- [x] Security (HTTPS enforced, no credentials in logs)
- [x] Compatibility (pathlib.Path used, no platform-specific shell calls)

## Reporting

- [x] Combined Allure report with separate section per environment (`@allure.suite`)
- [x] Bug reporter: auto-generates structured markdown on test failure
  - Title, Steps to Reproduce, Expected, Actual, Data (url, status, time, snippet)
- [x] `DELIVERABLES.md` completion % reported by `deliverables_tracker.py`

## CI Pipeline

- [x] `.github/workflows/ci.yml` triggers on push to any branch
- [x] Python environment setup + `pip install --upgrade pip && pip install -e ".[test]"` (pyproject.toml)
- [x] Full test suite runs (both environments + security + baseline = 88 tests)
- [x] Test report uploaded as pipeline artifact
- [x] Pipeline fails if any test fails or quality gate breached
- [x] Bonus: test summary printed in job output
- [x] 3-stage matrix: smoke(ubuntu/3.11) → platform(windows+mac/3.11) → versions(ubuntu/3.9+3.12) — 6 jobs total

## Claude Code Artifacts

- [x] `.claude/rules/testing-standards.md` — project testing conventions (framework-specific)
- [x] `.claude/rules/code-style.md` — Python style rules for this framework
- [x] `.claude/rules/framework-rules.md` — architecture constraints (includes URL atomicity rule)
- [x] `.claude/rules/document-parsing.md` — chunking and URL integrity rules
- [x] `.claude/skills/test-generator.md` — endpoint → full pytest test file
- [x] `.claude/skills/validator-generator.md` — JSON response → typed validator class
- [x] `.claude/skills/spec-parser.md` — spec doc → EndpointSpec extraction
- [x] `CLAUDE_LOG.md` — parallel agents documented, decisions, corrections, rules impact
- [x] `scripts/advisor_review.py` — Opus advisor stub (SDK pattern, no key required)

## Extensibility

- [x] `apitf/validators/base_validator.py` — abstract `BaseValidator` contract
- [x] `apitf/spec_parser/base_parser.py` — abstract `EndpointSpec` + parser ABC
- [x] `apitf/spec_parser/pdf_parser.py` — fully implemented PDF spec parser
- [x] `apitf/spec_parser/openapi_parser.py` — extensible stub (v1.1)
- [x] `apitf/spec_parser/markdown_parser.py` — extensible stub (v1.1)
- [x] `apitf/http_client.py` — shared HTTP wrapper (retry, timing, platform-safe)

## Submission

- [x] GitHub repo: `sks-54/api-test-framework` (new, public)
- [x] Phased PRs (one per phase, each Opus-reviewed before merge)
- [x] `README.md` with setup, run instructions, 6 Mermaid architecture diagrams, design decisions
- [x] `INSTALL.md` — platform-specific guide (macOS/Linux/Windows)
- [x] `wiki/` — 6 reference pages (Components, Skills, Bug Lifecycle, Design Decisions, Rules, Troubleshooting)
- [x] `pyproject.toml` — installable package (`pip install -e ".[test]"`)
- [x] Tagged `v1.0.0` once all items above are checked
- [x] `ENHANCEMENTS.md` tracking post-v1.0.0 roadmap

---

## Deviation Log

| Date | Phase | Deviation | Resolution |
|------|-------|-----------|------------|
| 2026-04-18 | Phase 2 | Hardcoded `_DEFAULT_THRESHOLDS` in `pdf_parser.py` violated Rule 1 | Replaced with `_UNRESOLVED_THRESHOLDS = {}` — callers resolve against `environments.yaml` |
| 2026-04-19 | Phase 3 | xfail markers for BUG-001/002/003 silently dropped during rebase conflict resolution | Re-added manually; added Rule 23 (post-rebase verification) + `scripts/verify_bug_markers.py` pre-push guard |
| 2026-04-19 | Phase 3 | TC-W-010 used range assertion `in (200, 400)` violating Rule 16 | Fixed to `== 200` + WeatherValidator schema check |
| 2026-04-19 | Phase 3 | 4 boundary/negative weather tests missing `@pytest.mark.flaky(reruns=2)` | Added flaky markers to TC-W-004, TC-W-005, TC-W-009, TC-W-010 |
| 2026-04-19 | Phase 5 | CI triggered on doc-only commits (DELIVERABLES.md, CLAUDE_LOG.md) — wasted runner budget | Added `paths-ignore` to push trigger; doc files excluded |
| 2026-04-19 | Phase 5 | CI had 2-stage pipeline (smoke → matrix) instead of 3-stage (smoke → platform → matrix) | Added platform stage: windows/3.11 + macos/3.11 before full version matrix |
| 2026-04-19 | Phase 3 | TC-W-003 had widened assertion `400 <= status < 500` violating Rule 16 | Fixed to `== 400` (confirmed API returns 400 for lat=999 via curl) |
| 2026-04-19 | Phase 3 | `pytest-retry` used instead of `pytest-rerunfailures` — reruns=/reruns_delay= kwargs silently ignored | Swapped to `pytest-rerunfailures>=12.0,<16.0` in requirements.txt |
| 2026-04-19 | Phase 3 | TC-W-004 had both `@pytest.mark.flaky` and `@pytest.mark.xfail(strict=True)` — incoherent combination | Removed flaky from TC-W-004; xfail handles the known-bug case |
| 2026-04-19 | Framework | Changes discussed in conversation not written to files until next session | Added Rule 25 to framework-rules.md and CLAUDE.md |
