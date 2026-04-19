# Enhancements Roadmap

> Tracked post-`v1.0.0`. All items below are out of scope for the initial release but are architecturally prepared (stubs, hooks, or extension points exist in v1.0.0).

---

## v1.1 — Parser Expansion

| ID | Enhancement | Effort | Notes |
|----|-------------|--------|-------|
| E-01 | `OpenAPIParser` — full implementation | Medium | Stub in `apitf/spec_parser/openapi_parser.py`. REST Countries exposes OpenAPI spec; Open-Meteo does too. Auto-generates `environments.yaml` entries from spec. |
| E-02 | `MarkdownParser` — full implementation | Small | Stub in `apitf/spec_parser/markdown_parser.py`. Targets API docs in `.md` format (e.g., GitHub-hosted API docs). |
| E-03 | Spec ingestion CLI (`scripts/ingest_spec.py`) | Small | Parses a dropped spec doc → updates `environments.yaml` + generates test skeleton. |

## v1.2 — Advisor Integration

| ID | Enhancement | Effort | Notes |
|----|-------------|--------|-------|
| E-04 | `scripts/advisor_review.py` — full SDK implementation | Small | Stub exists. Requires `ANTHROPIC_API_KEY` env var. Sends git diff + phase label to `claude-opus-4-7` with extended thinking; returns structured JSON review. |
| E-05 | Opus advisor as optional CI gate | Medium | GitHub Actions job (`advisor-review`) that runs only when `ANTHROPIC_API_KEY` secret is set. Skipped gracefully if absent. |

## v1.3 — Coverage & Scale

| ID | Enhancement | Effort | Notes |
|----|-------------|--------|-------|
| E-06 | Expand cities dataset to 20+ cities | Trivial | Add more `test_data/cities.json` entries. |
| E-07 | Load / scale testing via `pytest-xdist` | Medium | Parallel test execution across workers. |
| E-08 | Contract testing layer | Medium | Validate API responses against stored JSON schemas (snapshot testing). |

## v1.4 — Platform & Mobile

| ID | Enhancement | Effort | Notes |
|----|-------------|--------|-------|
| E-09 | Browser/mobile compatibility layer | Large | Playwright-based tests for any web UI surfacing these APIs. |
| E-10 | Android/iOS API reachability tests | Large | Network-layer checks for mobile client environments. |

## v1.5 — Observability

| ID | Enhancement | Effort | Notes |
|----|-------------|--------|-------|
| E-11 | Prometheus metrics export from test runs | Medium | Expose response time histograms per environment. |
| E-12 | Slack/Teams failure notification hook | Small | Post bug reports to a channel on CI failure. |

---

## How to Contribute an Enhancement

1. Pick an item from this list (or propose a new one via PR).
2. Add an entry to `config/environments.yaml` if a new API is involved — **zero framework changes required**.
3. Add validator in `apitf/validators/`, tests in `tests/`, and update `DELIVERABLES.md`.
4. Run `pytest -v` locally to confirm all existing tests still pass.
5. Open a PR — the Opus advisor review gate applies.
