# Deliverables Tracker

> Extracted from: `specs/home_test.PDF` — 2026-04-18
> Monitored by: Opus Advisor on every phase PR review
> Format: `[ ]` pending · `[x]` complete · `[!]` deviation detected

---

## Core Framework

- [ ] `config/environments.yaml` — two environments (countries, weather) with correct thresholds
- [ ] Environment fixture in top-level `conftest.py`
- [ ] `--env` CLI flag via `pytest_addoption` (accepts any key from YAML dynamically)
- [ ] No hardcoded URLs or thresholds anywhere in test code
- [ ] `test_data/cities.json` committed to repo (5 cities with lat/lon)

## Test Cases — Countries API

- [ ] `GET /region/europe` — assert result count > 40
- [ ] `GET /name/germany` — schema validation (name, capital, population, currencies, languages)
- [ ] `GET /all?fields=name,population` — assert every country has population > 0
- [ ] Cross-reference: country from `/name` must appear in `/region` results

## Test Cases — Weather API

- [ ] 5 cities parametrized from `test_data/cities.json`
- [ ] Temperature range validated (-80 to 60°C)
- [ ] Hourly entry count > 0
- [ ] `timezone` field present in response

## Test Coverage Techniques

- [ ] Boundary value analysis (count edges, temp extremes, threshold = value)
- [ ] Equivalence partitioning (valid inputs grouped)
- [ ] Positive / Negative test cases (valid vs invalid inputs)
- [ ] State-based testing (cross-reference: /name → /region)
- [ ] Error handling (404, timeout, malformed response, out-of-range)
- [ ] Performance (response_time < max_response_time from YAML — never hardcoded)
- [ ] Reliability (retry on 5xx)
- [ ] Security (HTTPS enforced, no credentials in logs)
- [ ] Compatibility (pathlib.Path used, no platform-specific shell calls)

## Reporting

- [ ] Combined Allure report with separate section per environment (`@allure.suite`)
- [ ] Bug reporter: auto-generates structured markdown on test failure
  - Title, Steps to Reproduce, Expected, Actual, Data (url, status, time, snippet)
- [ ] `DELIVERABLES.md` completion % reported by `deliverables_tracker.py`

## CI Pipeline

- [ ] `.github/workflows/ci.yml` triggers on push to any branch
- [ ] Python environment setup + `pip install -r requirements.txt`
- [ ] Full test suite runs (both environments)
- [ ] Test report uploaded as pipeline artifact
- [ ] Pipeline fails if any test fails or quality gate breached
- [ ] Bonus: test summary printed in job output
- [ ] Matrix: `ubuntu-latest`, `windows-latest`, `macos-latest` × Python `3.9, 3.10, 3.11, 3.12`

## Claude Code Artifacts

- [ ] `.claude/rules/testing-standards.md` — project testing conventions (framework-specific)
- [ ] `.claude/rules/code-style.md` — Python style rules for this framework
- [ ] `.claude/rules/framework-rules.md` — architecture constraints (includes URL atomicity rule)
- [ ] `.claude/rules/document-parsing.md` — chunking and URL integrity rules
- [ ] `.claude/skills/test-generator.md` — endpoint → full pytest test file
- [ ] `.claude/skills/validator-generator.md` — JSON response → typed validator class
- [ ] `.claude/skills/spec-parser.md` — spec doc → EndpointSpec extraction
- [ ] `CLAUDE_LOG.md` — parallel agents documented, decisions, corrections, rules impact
- [ ] `scripts/advisor_review.py` — Opus advisor stub (SDK pattern, no key required)

## Extensibility

- [ ] `src/validators/base_validator.py` — abstract `BaseValidator` contract
- [ ] `src/spec_parser/base_parser.py` — abstract `EndpointSpec` + parser ABC
- [ ] `src/spec_parser/pdf_parser.py` — fully implemented PDF spec parser
- [ ] `src/spec_parser/openapi_parser.py` — extensible stub (v1.1)
- [ ] `src/spec_parser/markdown_parser.py` — extensible stub (v1.1)
- [ ] `src/http_client.py` — shared HTTP wrapper (retry, timing, platform-safe)

## Submission

- [ ] GitHub repo: `sks-54/api-test-framework` (new, public)
- [ ] Phased PRs (one per phase, each Opus-reviewed before merge)
- [ ] `README.md` with setup, run instructions, 5 Mermaid architecture diagrams, design decisions
- [ ] Tagged `v1.0.0` once all items above are checked
- [ ] `ENHANCEMENTS.md` tracking post-v1.0.0 roadmap

---

## Deviation Log

| Date | Phase | Deviation | Resolution |
|------|-------|-----------|------------|
| —    | —     | —         | —          |
