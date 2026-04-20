# Rules & Skills Audit — 2026-04-20

## Verified Facts (grep-confirmed)

| Claim | Source | Actual |
|-------|--------|--------|
| Reflector threshold | `run-workflow.md` says 70 | `eval_loop.py:29` → `REFLECTOR_PASS_THRESHOLD = 95` |
| `--sample` flag | skills doc | `cli.py:423` → exists and implemented |
| MarkdownParser | `spec-parser.md` only shows PDFParser | `apitf/parsers/markdown_parser.py` exists but not registered in skill |
| CI run for bb8e155 | Latest main commit | Latest CI run is for SHA `2cc46168`, not `bb8e155` — no CI ran for the CI workflow change |

---

## Gap 1 — `run-workflow.md`: Stale reflector threshold

**File:** `.claude/skills/run-workflow.md`
**Issue:** Describes threshold as 70. Actual value is 95.
**Impact:** Any session reading this skill will set wrong expectations for pass/fail.
**Fix:** Update all references from 70 → 95.

---

## Gap 2 — `run-workflow.md`: Parallel pipeline not documented

**File:** `.claude/skills/run-workflow.md`
**Issue:** Skill describes only single-resource sequential workflow. The framework now runs parallel workers via `ThreadPoolExecutor(max_workers=min(n,4))`.
**Missing:**
- `--no-parallel` flag
- Per-resource bug report file naming (`bug_report_{resource}.md`)
- `scripts/merge_bug_reports.py` merge step
- `resource_name` field on `EndpointSpec`
**Impact:** AI sessions will generate sequential code when parallel is the production pattern.

---

## Gap 3 — `spec-parser.md`: Incomplete parser registry

**File:** `.claude/skills/spec-parser.md`
**Issue:** Only imports and registers `PDFParser`. `MarkdownParser` is fully implemented and should be registered.
**Missing:**
- `MarkdownParser` import and `ParserRegistry.register("markdown", MarkdownParser)`
- `EndpointSpec.resource_name` field (populated by all parsers via `_resource_from_path()`)
**Impact:** Markdown specs will silently fail in sessions that follow the skill verbatim.

---

## Gap 4 — `test-generator.md`: Incomplete technique coverage

**File:** `.claude/skills/test-generator.md`
**Issue:** Skill generates only 4 test types: positive, negative, boundary, performance.
**Missing techniques (all required by framework):**
- Equivalence partitioning
- State-based testing
- Error handling / fault injection
- Security (injection, auth bypass)
- Reliability (`@pytest.mark.flaky(reruns=2, reruns_delay=2)`)
- Schema contract validation via `BaseValidator`
**Impact:** Generated tests will be under-specified; framework completeness requirements not met.

---

## Gap 5 — `framework-rules.md`: Parallel pipeline has no codified rules

**File:** `.claude/rules/framework-rules.md`
**Issue:** 27 rules cover eval loop, CI, bug lifecycle, providers, code style — but nothing governs parallel execution.
**Missing rules:**
- All endpoints must have `resource_name` populated (enforced by parsers)
- Parallel workers: one worker per resource, max 4 concurrent
- Bug reports written to per-resource files (`bug_report_{resource}.md`)
- Merge step (`scripts/merge_bug_reports.py`) is required before final output
- `--no-parallel` flag must be available for debugging
**Impact:** Parallel pipeline behaviour is undocumented and unenforced.

---

## Gap 6 — CI coverage gap for `bb8e155`

**Commit:** `bb8e155` (CI workflow change — removed `paths-ignore` from PR trigger)
**Issue:** This commit was pushed directly to `main`. The push trigger has `branches-ignore: ["main"]`, so no CI ran. The latest CI run on main is for `2cc46168`.
**Risk:** The CI change itself was never validated by CI. Branch protection now requires Quality Gate on PRs, but this commit bypassed that.
**Fix options:**
1. Create a trivial PR from a scratch branch to re-run CI against a state that includes the workflow change
2. Accept the gap (the change is low-risk — it only removes a `paths-ignore` block)

---

## Gap 7 — Branch protection not documented in CLAUDE.md / DELIVERABLES.md

**Files:** `CLAUDE.md`, `DELIVERABLES.md`
**Issue:** Branch protection was configured (Quality Gate required, strict up-to-date, no force-push, no delete) but this is not reflected in either doc.
**Fix:** Add a note to CLAUDE.md's "Key files" section and tick the relevant DELIVERABLES.md checkbox.
