# API Test Framework — Wiki

Production-grade, config-driven multi-environment API test framework with 88 tests across REST Countries and Open-Meteo. New APIs added in 3 steps via YAML config — zero framework changes.

## Navigation

| Page | Contents |
|------|----------|
| [Framework Components](Framework-Components) | HttpClient, BaseValidator, validators, BugReporter, SpecParser internals |
| [Claude Code Skills](Claude-Code-Skills) | `/spec-parser`, `/validator-generator`, `/test-generator` — full reference |
| [Allure Report Guide](Allure-Report-Guide) | Suites, attachments, xfail/xpass, CI artifact download |
| [Bug Lifecycle](Bug-Lifecycle) | From failure → GitHub issue → xfail → resolution |
| [Test Design Techniques](Test-Design-Techniques) | Boundary, equivalence, state-based, performance, security — with code |
| [Design Decisions](Design-Decisions) | Key architectural choices and trade-offs |
| [Rules Reference](Rules-Reference) | 27 framework rules with enforcement mechanism |
| [Troubleshooting](Troubleshooting) | Common errors, platform-specific issues, CI debugging |

## Quick Links

```bash
# Install
pip install --upgrade pip && pip install -e ".[test]"

# Run all tests
pytest -v --alluredir=allure-results

# Run specific environment
pytest --env countries -v --alluredir=allure-results
pytest --env weather   -v --alluredir=allure-results

# View Allure report
allure serve allure-results

# Check CI on a PR
gh pr checks <N> --watch
```

## Test Suite Summary

| Suite | File | Tests | Collected Nodes |
|-------|------|-------|-----------------|
| countries | `test_countries.py` | 21 | 21 |
| weather | `test_weather.py` | 10 | 26 (5-city parametrize) |
| security | `test_security.py` | RFC 7231 + OWASP | ~48 (env × violation type) |
| baseline | `test_baseline.py` | 4 generic per env | ~8 (2 envs × 4 checks) |
| **Total** | | | **88** |

## Known Bugs

| Bug | Category | API | Status |
|-----|----------|-----|--------|
| BUG-001 | QUALITY | Countries | `/alpha/ZZZ999` → 400 not 404 |
| BUG-002 | QUALITY | Weather | Missing params → 200 not 400 |
| BUG-003 | QUALITY | Countries | 5 territories have `population=0` |
| BUG-004 | SLA | Weather | /forecast timeout on CI runners |
| BUG-006..012 | QUALITY | Weather | RFC 7231 method/header/content violations |

See [BUG_REPORT.md](../BUG_REPORT.md) for curl reproduction commands and full details.
