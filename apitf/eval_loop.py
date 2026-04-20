"""
apitf.eval_loop — automated eval loop and Opus reflector.

AI provider is auto-discovered via apitf.providers.discover_provider():
  1. Claude Code CLI session (CLAUDECODE=1 + claude in PATH)
  2. Anthropic SDK (ANTHROPIC_API_KEY)
  3. None → 5-test stub, reflector skipped

Without any provider all AI steps are skipped and a stub result is returned.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ADVISOR_MODEL: str = "claude-opus-4-7"
MAX_RESPONSE_TOKENS: int = 2048
REFLECTOR_MAX_ITER: int = 3  # max Opus→correct→re-score rounds (test files and test plans)
REFLECTOR_PASS_THRESHOLD: int = 95  # minimum Opus score to accept generated test file/plan

ReviewResult = dict[str, Any]

_STRUCTURAL_PATTERNS: tuple[str, ...] = (
    "AttributeError",
    "ImportError",
    "ModuleNotFoundError",
    "FixtureError",
    "fixture",
    "SyntaxError",
    "IndentationError",
    "TypeError",
    "ERROR collecting",
)
_ENV_PATTERNS: tuple[str, ...] = (
    "ConnectionError",
    "Timeout",
    "SSLError",
    "ConnectionRefused",
    "HTTPSConnectionPool",
    "NewConnectionError",
)


@dataclass
class FailureInfo:
    test_name: str
    category: str  # STRUCTURAL | QUALITY | ENV
    error_msg: str


@dataclass
class EvalResult:
    iteration: int
    passed: int
    failed: int
    xfailed: int
    failures: list[FailureInfo] = field(default_factory=list)
    clean: bool = False


from apitf.providers import discover_provider, _NO_AI_MESSAGE
from apitf.providers.base import LLMProvider


def detect_ai_mode(explicit_key: str | None = None) -> tuple[str | None, str]:
    """Legacy shim — returns (sentinel_or_key, source) for backward compatibility.

    New code should use discover_provider() directly.
    """
    from apitf.providers.claude_cli import ClaudeCLIProvider
    from apitf.providers.anthropic import AnthropicProvider
    if ClaudeCLIProvider.available():
        return "__claude_cli__", "claude_cli"
    if AnthropicProvider.available(explicit_key=explicit_key):
        import os
        key = explicit_key or os.environ.get("ANTHROPIC_API_KEY")
        return key, "env"
    provider = discover_provider(explicit_key)
    if provider is not None:
        return "__provider__", type(provider).__name__.lower()
    return None, "none"


def _claude_cli_call(prompt: str, model: str) -> str:
    """Backward-compatible shim — routes through ClaudeCLIProvider."""
    from apitf.providers.claude_cli import ClaudeCLIProvider
    return ClaudeCLIProvider().generate(prompt, model)


def _strip_fences(text: str) -> str:
    """Extract code from a response, stripping markdown fences and any leading prose.

    Priority order:
    1. Extract content inside the first ```python ... ``` or ``` ... ``` block
    2. If no fences, find the first Python-module-opening line and take from there
    3. Fall back to stripped raw text
    """
    text = text.strip()
    # Try to extract from a fenced code block (```python or plain ```)
    fenced = re.search(r"```(?:python)?\s*\n([\s\S]*?)```", text)
    if fenced:
        return fenced.group(1).strip()
    # No fences — find first line that opens a Python module (skip all prose)
    _PYTHON_OPENERS = ("from __future__", "import ", "from ", "def ", "class ", "#!", "# -*-")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(p) for p in _PYTHON_OPENERS):
            return "\n".join(lines[i:]).strip()
    return text


# ---------------------------------------------------------------------------
# Reflector (Opus review)
# ---------------------------------------------------------------------------

def _make_api_call(prompt: str, model: str, api_key: str | None) -> str:
    """Route an API call through the discovered provider."""
    provider = discover_provider(api_key)
    if provider is None:
        raise RuntimeError("No LLM provider available")
    return provider.generate(prompt, model)


def review_phase(
    phase: str, diff: str, rubric: dict[str, Any], api_key: str | None = None
) -> ReviewResult:
    """Submit a code diff to Opus for rubric-based review.

    Returns a ReviewResult dict with: score, passed, deviations, corrections, category.
    Works with ANTHROPIC_API_KEY, .env file, or authenticated Claude Code session.
    Falls back to a stub result when no auth method is available.
    """
    provider = discover_provider(api_key)
    if provider is None:
        logger.info("[reflector] No provider available — returning stub result")
        return {
            "score": -1,
            "passed": False,
            "deviations": ["No LLM provider — live review skipped."],
            "corrections": ["Install a provider to enable live Opus review."],
            "category": "style",
        }

    prompt = f"""You are a senior QA architect reviewing phase "{phase}".

## Evaluation rubric
{json.dumps(rubric, indent=2)}

## Code diff under review
```diff
{diff}
```

Return JSON only — no markdown fences, no prose:
{{
  "score":       <int 0-100>,
  "passed":      <bool — true if score >= rubric["pass_threshold"]>,
  "deviations":  ["<rule violated>", ...],
  "corrections": ["<fix for each deviation>", ...],
  "category":    "<style | architecture | test-coverage | security>"
}}"""

    logger.info("[reflector] Sending %d-char prompt to %s", len(prompt), ADVISOR_MODEL)
    try:
        raw = _make_api_call(prompt, ADVISOR_MODEL, api_key)
    except Exception as exc:
        logger.warning("[reflector] API call failed: %s", exc)
        return {
            "score": -1,
            "passed": False,
            "deviations": [f"API call failed: {exc}"],
            "corrections": [],
            "category": "style",
        }
    text = _strip_fences(raw)
    try:
        result: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Reflector returned non-JSON: {raw!r}") from exc
    required = ("score", "passed", "deviations", "corrections", "category")
    missing = [k for k in required if k not in result]
    if missing:
        raise ValueError(f"Reflector response missing keys: {missing}")
    return result


def _trim_pytest_output(output: str, char_limit: int = 6000) -> str:
    """Trim pytest output without cutting inside a failure block or line.

    Aligns cuts to pytest block separators (lines of underscores/equals) so Opus
    never receives a traceback that starts mid-function or mid-class.
    Falls back to a newline-aligned tail slice if no block boundaries fit.
    """
    if len(output) <= char_limit:
        return output
    block_starts = [m.start() for m in re.finditer(r"^[_=]{10,}", output, re.MULTILINE)]
    for start in reversed(block_starts):
        candidate = output[start:]
        if len(candidate) <= char_limit:
            return candidate
    tail = output[-char_limit:]
    newline = tail.find("\n")
    return tail[newline + 1:] if newline != -1 else tail


def _reflect_test_file(
    env: str,
    test_file: Path,
    pytest_output: str,
    model: str = ADVISOR_MODEL,
    api_key: str | None = None,
) -> ReviewResult:
    """Opus reviews the final generated test file against the QA rubric.

    Routes through claude CLI (no key needed) when running inside Claude Code,
    otherwise uses the anthropic SDK with ANTHROPIC_API_KEY / .env key.
    """
    provider = discover_provider(api_key)
    if provider is None:
        print("[reflector] No provider available — skipping reflector review.", file=sys.stderr)
        return {
            "score": -1,
            "passed": False,
            "deviations": ["No LLM provider — reflector skipped."],
            "corrections": ["Install a provider (see apitf-run startup message) to enable reflector review."],
            "category": "n/a",
        }

    test_src = test_file.read_text(encoding="utf-8")
    prompt = f"""You are a senior QA architect performing a final review of an auto-generated test file.

## Test file: {test_file.name}  (env: {env})
```python
{test_src}
```

## Pytest run output
```
{_trim_pytest_output(pytest_output)}
```

## Scoring rubric (pass threshold = {REFLECTOR_PASS_THRESHOLD})
Score 0-100 across these dimensions (each worth up to ~15 pts):
- Technique coverage: equivalence, boundary, positive, negative, performance, security all present
- Zero hardcoded values — all thresholds and URLs from env_config
- HttpClient used as context manager (never raw requests)
- @pytest.mark.flaky on every live HTTP call; NOT on xfail or HTTPS-only tests
- xfail(strict=True, raises=SLA_FAILURE_EXCEPTIONS) ONLY when there is a confirmed documented bug (BUG-NNN ID known); do NOT deduct points if there are no confirmed bugs — adding xfail without a real bug causes XPASS failures
- assert result.passed, result.errors pattern for all validator calls

Return JSON only — no markdown fences:
{{
  "score": <int 0-100>,
  "passed": <bool>,
  "deviations": ["<missing technique or rule>", ...],
  "corrections": ["<specific actionable fix>", ...],
  "category": "test-coverage"
}}"""

    print(f"[reflector] Sending {test_file.name} to {ADVISOR_MODEL} for review …")
    try:
        raw = _make_api_call(prompt, ADVISOR_MODEL, api_key)
        text = _strip_fences(raw)
        result = json.loads(text)
        return result
    except Exception as exc:
        print(f"[reflector] Review call failed: {exc}", file=sys.stderr)
        return {"score": -1, "passed": False, "deviations": [str(exc)], "corrections": [], "category": "error"}


# ---------------------------------------------------------------------------
# Eval loop helpers
# ---------------------------------------------------------------------------

def _run_pytest(env: str, test_file: Path) -> tuple[str, int]:
    """Run pytest on test_file and return (combined output, exit_code)."""
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "--env", env,
        "--tb=short", "-q",
        "--no-header",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout + proc.stderr, proc.returncode


def _categorize_failure(error_text: str) -> str:
    for pat in _STRUCTURAL_PATTERNS:
        if pat in error_text:
            return "STRUCTURAL"
    for pat in _ENV_PATTERNS:
        if pat in error_text:
            return "ENV"
    return "QUALITY"


def _parse_failures(output: str) -> list[FailureInfo]:
    """Extract per-test failure info from pytest --tb=short output."""
    failures: list[FailureInfo] = []
    # Map test function name → surrounding error text
    sections = re.split(r"_{10,}", output)
    error_map: dict[str, str] = {}
    for sec in sections:
        m = re.search(r"(test_\w+)", sec)
        if m:
            error_map[m.group(1)] = sec

    for m in re.finditer(r"FAILED\s+[\w/\\]+\.py::(test_\w+)", output):
        test_name = m.group(1)
        error_text = error_map.get(test_name, "")
        failures.append(FailureInfo(
            test_name=test_name,
            category=_categorize_failure(error_text),
            error_msg=error_text.strip()[:500],
        ))
    return failures


def _ai_fix_structural(
    env: str,
    test_file: Path,
    failure_output: str,
    model: str,
    api_key: str | None = None,
) -> bool:
    """Re-generate the test file to fix structural errors. Returns True on success."""
    provider = discover_provider(api_key)
    if provider is None:
        return False

    current_src = test_file.read_text(encoding="utf-8")
    prompt = f"""The following pytest test file has structural errors (import errors, missing attributes, wrong method calls, etc.).

## Current file
```python
{current_src}
```

## Pytest failure output
```
{failure_output[:3000]}
```

Fix ONLY the structural errors. Do not change test logic, assertions, or techniques covered.
Output ONLY the corrected Python source — no markdown fences, no prose."""

    print(f"[eval-loop] Calling {model} to fix structural failures …")
    try:
        src = _strip_fences(provider.generate(prompt, model))
        test_file.write_text(src, encoding="utf-8")
        print(f"[eval-loop] Test file rewritten: {test_file.name}")
        return True
    except Exception as exc:
        print(f"[eval-loop] AI fix failed: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Bug report generator + reflector
# ---------------------------------------------------------------------------

_BUG_REPORT_GOLD_STANDARD = """\
### BUG-001

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Issue** | https://github.com/sks-54/api-test-framework/issues/5 |
| **Test** | TC-C-004 |
| **Severity** | P2 |
| **Category** | QUALITY_FAILURE |
| **Status** | OPEN |
| **Platform** | ubuntu-latest, windows-latest, macos-latest (API-level bug — reproducible on all platforms) |
| **Python** | 3.9, 3.11, 3.12 (not platform-specific) |
| **Title** | `/alpha/ZZZ999` returns 400 Bad Request instead of 404 Not Found |

**curl (reproduces bug):**
```bash
# Expected HTTP 404, actual HTTP 400
curl -s -o /dev/null -w "%{http_code}" "https://restcountries.com/v3.1/alpha/ZZZ999"
curl -s "https://restcountries.com/v3.1/alpha/ZZZ999" | python3 -m json.tool
```

**Expected (per spec):** HTTP 404 — resource not found for invalid alpha code

**Actual:** HTTP 400 Bad Request — `{"message":"Bad Request","status":400}`

**Data:**
- Request URL: `https://restcountries.com/v3.1/alpha/ZZZ999`
- Status Code: 400
- Notes: API conflates "invalid format" with "not found" — spec requires 404

---"""



def _generate_bug_entry(
    bug_id: str,
    env: str,
    base_url: str,
    failure: "FailureInfo",
    pytest_output: str,
    model: str,
    api_key: str | None,
) -> str:
    """Use the generation model to write one BUG_REPORT.md entry for a QUALITY_FAILURE."""
    traceback_snippet = _trim_pytest_output(pytest_output)
    prompt = f"""You are writing a bug report entry for an API test framework.

## Gold-standard entry format (copy this structure exactly):
{_BUG_REPORT_GOLD_STANDARD}

## Failure details
- Bug ID to assign: {bug_id}
- Environment: {env}
- Base URL: {base_url}
- Failing test: {failure.test_name}
- Error message: {failure.error_msg[:400]}

## Pytest output (extract the actual vs expected from this):
```
{traceback_snippet[-2000:]}
```

## Rules:
- Issue field: write exactly `[TBD — file with \`gh issue create --title '[BUG] {bug_id}: ...' --label bug\`]`
- Test field: derive TC ID from test name (e.g. test_get_todo_schema → TC-TOD-NNN) or write `{env.upper()[:3]}-?`
- curl commands MUST use the literal resolved URL — no placeholders like <base_url>
- Both curl variants required: status-only (`-o /dev/null -w "%{{http_code}}"`) AND full JSON (`| python3 -m json.tool`)
- Comment above curls: `# Expected HTTP NNN, actual HTTP MMM`
- Severity: P2 for QUALITY_FAILURE unless it's a 5xx (then P1)
- Platform: `ubuntu-latest, windows-latest, macos-latest (API-level bug — reproducible on all platforms)`
- Python: `3.9, 3.11, 3.12 (not platform-specific)`
- End the entry with a line containing only `---`

Output ONLY the markdown entry block starting with `### {bug_id}` — no prose, no extra text."""

    try:
        return _make_api_call(prompt, model, api_key)
    except Exception as exc:
        logger.warning("[bug-reporter] Entry generation failed: %s", exc)
        return ""


def _reflect_bug_entry(
    bug_id: str,
    entry_text: str,
    model: str = ADVISOR_MODEL,
    api_key: str | None = None,
) -> ReviewResult:
    """Opus reviews a generated bug report entry against the gold-standard rubric."""
    provider = discover_provider(api_key)
    if provider is None:
        return {"score": -1, "passed": False, "deviations": ["No provider"], "corrections": [], "category": "bug-report"}

    prompt = f"""You are reviewing a bug report entry for an API test framework.

## Entry under review
{entry_text}

## Gold-standard reference
{_BUG_REPORT_GOLD_STANDARD}

## Scoring rubric (pass threshold = {REFLECTOR_PASS_THRESHOLD})
Score 0–100 across these dimensions:
- All required fields present (ID, Issue, Test, Severity, Category, Status, Platform, Python, Title): 20 pts
- curl commands use the literal resolved URL — NO placeholders like <base_url> or <path>: 20 pts
- Expected field states the spec contract explicitly (not vague): 15 pts
- Actual field states observed behavior with status code and response snippet: 15 pts
- Title is specific — includes endpoint path + actual vs expected status: 15 pts
- Category correctly assigned (QUALITY_FAILURE vs SLA_VIOLATION): 10 pts
- Both curl variants present (status-only + full JSON) with comment above: 5 pts

Return JSON only — no markdown fences:
{{
  "score": <int 0-100>,
  "passed": <bool — true if score >= {REFLECTOR_PASS_THRESHOLD}>,
  "deviations": ["<specific issue>", ...],
  "corrections": ["<specific fix>", ...],
  "category": "bug-report"
}}"""

    print(f"[bug-reporter] Sending {bug_id} to {model} for review (via claude_cli) …")
    try:
        raw = _make_api_call(prompt, model, api_key)
        return json.loads(_strip_fences(raw))
    except Exception as exc:
        logger.warning("[bug-reporter] Reflect call failed: %s", exc)
        return {"score": -1, "passed": False, "deviations": [str(exc)], "corrections": [], "category": "error"}


def generate_bug_report_loop(
    env: str,
    base_url: str,
    failures: "list[FailureInfo]",
    pytest_output: str,
    project_root: Path,
    model: str,
    reflector_model: str = ADVISOR_MODEL,
    api_key: str | None = None,
    bug_report_path: Path | None = None,
) -> list[str]:
    """For each QUALITY_FAILURE: generate → Opus reflect → Sonnet correct → append to bug report.

    bug_report_path: where to write entries. Defaults to project_root/BUG_REPORT.md.
    Returns list of bug IDs written. Does NOT file GitHub issues or add xfail markers —
    those remain manual steps enforced by verify_bug_markers.py.
    """
    if discover_provider(api_key) is None:
        print("[bug-reporter] No provider — skipping auto bug report generation.", file=sys.stderr)
        return []

    report_path = bug_report_path if bug_report_path is not None else project_root / "BUG_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    written_ids: list[str] = []

    # Compute starting ID once; increment unconditionally so degenerate writes don't reuse IDs.
    _existing = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    next_n = max((int(i) for i in re.findall(r"BUG-(\d{3})", _existing)), default=0) + 1

    for failure in failures:
        bug_id = f"BUG-{next_n:03d}"
        next_n += 1
        print(f"\n[bug-reporter] ── Generating {bug_id} for {failure.test_name} ──")

        entry = _generate_bug_entry(bug_id, env, base_url, failure, pytest_output, model, api_key)
        entry = _strip_fences(entry)

        for round_num in range(1, REFLECTOR_MAX_ITER + 2):
            review = _reflect_bug_entry(bug_id, entry, model=reflector_model, api_key=api_key)
            score = review.get("score", -1)
            passed = review.get("passed", False) and score >= REFLECTOR_PASS_THRESHOLD
            if score >= 0:
                print(f"[bug-reporter] Score: {score}/100  passed={passed}")
            for dev in review.get("deviations", []):
                print(f"[bug-reporter]   deviation: {dev}")

            if passed or score < 0:
                break
            if round_num > REFLECTOR_MAX_ITER:
                print(f"[bug-reporter] Max correction rounds reached — accepting best effort entry.")
                break

            corrections = review.get("corrections", [])
            if not corrections:
                break

            print(f"[bug-reporter] Applying {len(corrections)} correction(s) …")
            fix_prompt = f"""You are correcting a bug report markdown entry.

## Current entry
{entry}

## Required corrections (apply ALL)
{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(corrections))}

Rules:
- curl commands must use the literal URL — no placeholders
- Both curl variants required: status-only and full JSON
- Issue field must contain the `gh issue create` instruction
- End with a line containing only `---`

Output ONLY the corrected markdown entry starting with `### {bug_id}` — no prose."""

            try:
                fixed = _make_api_call(fix_prompt, model, api_key)
                entry = _strip_fences(fixed)
            except Exception as exc:
                logger.warning("[bug-reporter] Correction failed: %s", exc)
                break

        # Append to BUG_REPORT.md
        if entry.strip():
            existing = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
            # Insert under "## Open Bugs" section if present, otherwise append
            if "## Open Bugs" in existing:
                insert_pos = existing.index("## Open Bugs") + len("## Open Bugs\n")
                updated = existing[:insert_pos] + "\n" + entry.strip() + "\n\n" + existing[insert_pos:]
            else:
                updated = existing.rstrip() + "\n\n" + entry.strip() + "\n"
            report_path.write_text(updated, encoding="utf-8")
            print(f"[bug-reporter] Wrote {bug_id} to BUG_REPORT.md")
            written_ids.append(bug_id)
        else:
            print(f"[bug-reporter] Empty entry for {failure.test_name} — skipping write.", file=sys.stderr)

    return written_ids


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def eval_loop(
    env: str,
    test_file: Path,
    max_iter: int = 3,
    model: str = "claude-sonnet-4-6",
    reflector_model: str = ADVISOR_MODEL,
    api_key: str | None = None,
    bug_report_path: Path | None = None,
) -> list[EvalResult]:
    """Run pytest in a loop, auto-fixing STRUCTURAL failures each iteration.

    After the loop converges (clean run or max_iter reached), the Opus
    reflector reviews the final test file and prints a scored report.

    Args:
        env:             Environment key matching environments.yaml and pytest marker.
        test_file:       Path to the generated test file.
        max_iter:        Maximum iterations before giving up (default 3).
        model:           Model for structural fix re-generation.
        reflector_model: Model for the final Opus review (default: claude-opus-4-7).

    Returns:
        List of EvalResult, one per iteration.
    """
    _provider = discover_provider(api_key)
    if _provider is not None:
        print(f"[eval-loop] AI provider: {_provider.models.label}")
    else:
        print("[eval-loop] AI provider: none — structural fixes and reflector review disabled")

    results: list[EvalResult] = []
    last_output = ""

    for iteration in range(1, max_iter + 1):
        print(f"\n[eval-loop] ── Iteration {iteration}/{max_iter} ──────────────────────")
        output, exit_code = _run_pytest(env, test_file)
        last_output = output
        print(output)

        # Parse counts from summary line
        passed = len(re.findall(r"\d+ passed", output))
        failed_count = sum(int(n) for n in re.findall(r"(\d+) failed", output))
        xfailed = len(re.findall(r"\d+ xfailed", output))
        failures = _parse_failures(output)

        er = EvalResult(
            iteration=iteration,
            passed=passed,
            failed=failed_count,
            xfailed=xfailed,
            failures=failures,
            clean=(exit_code == 0),
        )
        results.append(er)

        if er.clean:
            print(f"[eval-loop] ✓ All tests clean on iteration {iteration}.")
            break

        structural = [f for f in failures if f.category == "STRUCTURAL"]
        quality = [f for f in failures if f.category == "QUALITY"]
        env_fails = [f for f in failures if f.category == "ENV"]

        if env_fails and not structural and not quality:
            print(
                f"[eval-loop] All {len(env_fails)} failure(s) are ENV_FAILURE "
                "(network / API unavailable) — stopping, retry later."
            )
            break

        if structural and iteration < max_iter:
            print(f"[eval-loop] {len(structural)} STRUCTURAL failure(s) — auto-fixing …")
            fixed = _ai_fix_structural(env, test_file, output, model, api_key=api_key)
            if not fixed:
                print(
                    "[eval-loop] No API key — cannot auto-fix structural errors.\n"
                    "            Set ANTHROPIC_API_KEY or pass --api-key, or fix manually.",
                    file=sys.stderr,
                )
                break
            # Next iteration will re-run with the fixed file
        elif quality:
            print(f"[eval-loop] {len(quality)} QUALITY failure(s) — spec deviations (not auto-fixable):")
            for f in quality:
                print(f"  [{f.category}] {f.test_name}")
                print(f"    {f.error_msg[:120]}")

            # Derive project_root and base_url for bug report generation
            _project_root = test_file.parent.parent
            _base_url = ""
            try:
                import yaml as _yaml
                _env_data = _yaml.safe_load(
                    (_project_root / "config" / "environments.yaml").read_text(encoding="utf-8")
                ) or {}
                _base_url = _env_data.get(env, {}).get("base_url", "")
            except Exception:
                pass

            bug_ids = generate_bug_report_loop(
                env=env,
                base_url=_base_url,
                failures=quality,
                pytest_output=last_output,
                project_root=_project_root,
                model=model,
                reflector_model=reflector_model,
                api_key=api_key,
                bug_report_path=bug_report_path,
            )

            print("\n  Next steps for each bug:")
            for bug_id in bug_ids:
                print(f"  1. gh issue create --title '[BUG] {bug_id}: <title>' --label bug")
                print(f"     → Add the issue URL to BUG_REPORT.md under {bug_id}")
                print(f"  2. Add @pytest.mark.xfail(strict=True, reason='{bug_id} / Issue #N: ...') to the test")
            if not bug_ids:
                print(
                    "  1. File a GitHub issue for each deviation.\n"
                    "  2. Add @pytest.mark.xfail(strict=True, reason='Bug #N: ...') to the test.\n"
                    "  3. Re-run apitf-run (or pytest --env) to confirm xfailed state."
                )
            break
        else:
            break

    # ── Reflector + correction feedback loop ───────────────────────────────
    for reflector_round in range(1, REFLECTOR_MAX_ITER + 2):
        print(f"\n[reflector] ── Opus reflector review (round {reflector_round}) ──────────────")
        review = _reflect_test_file(env, test_file, last_output, reflector_model, api_key=api_key)
        score = review.get("score", -1)
        passed_review = review.get("passed", False) and score >= REFLECTOR_PASS_THRESHOLD
        print(f"[reflector] Score   : {score}/100")
        print(f"[reflector] Passed  : {'✓ yes' if passed_review else f'✗ no (threshold = {REFLECTOR_PASS_THRESHOLD})'}")
        if review.get("deviations"):
            print("[reflector] Deviations:")
            for d in review["deviations"]:
                print(f"  - {d}")
        if review.get("corrections"):
            print("[reflector] Corrections:")
            for c in review["corrections"]:
                print(f"  → {c}")

        if passed_review or score < 0:
            # Passed threshold, or no live review available — done
            break

        if reflector_round > REFLECTOR_MAX_ITER:
            print(f"[reflector] Max correction rounds ({REFLECTOR_MAX_ITER}) reached — stopping.")
            break

        corrections = review.get("corrections", [])
        if not corrections or discover_provider(api_key) is None:
            break

        # Apply Opus corrections via AI re-generation
        print(f"\n[reflector] Applying {len(corrections)} correction(s) via {model} …")
        current_src = test_file.read_text(encoding="utf-8")
        corrections_text = "\n".join(f"- {c}" for c in corrections)
        fix_prompt = f"""You are fixing a pytest test file. Output ONLY valid Python source code.

CRITICAL: Your response must begin with a Python statement (e.g. `from __future__ import annotations` or `import pytest`).
Do NOT write any prose, summary, explanation, or markdown fences. The first character of your output must be part of Python code.

## Current file
{current_src}

## Required corrections (apply ALL of these)
{corrections_text}

Framework rules (must not be broken):
- env_config is a PYTEST FIXTURE — never import from a module. Each test receives it as a parameter:
    def test_foo(env_config: dict) -> None:
        cfg = env_config["<env_name>"]
- HttpResponse: resp.json_body (not .json()), resp.response_time_ms (not .elapsed)
- All SLA thresholds from cfg["thresholds"]["max_response_time"] * 1000
- HttpClient context manager: with HttpClient(cfg["base_url"]) as client:
- @pytest.mark.flaky(reruns=2, reruns_delay=2) on every live HTTP call
- Negative tests assert EXACT status code (never `in (...)` or `>= 400`)
- Validator: result = ValidatorClass().validate(data); assert result.passed, result.errors
  (NEVER: ValidatorClass(data).validate() — data goes into validate(), NOT __init__)
- HTTPS security test: pytest.raises(ValueError, match="HTTPS") around HttpClient(http_url)
  where http_url = cfg["base_url"].replace("https://", "http://")
- Do NOT use cfg["boundaries"] or cfg["insecure_base_url"] — those keys don't exist
- Boundary IDs: use literal integers (id=1 minimum, id=9999 out-of-range)
- Full type hints on every function
- SLA_FAILURE_EXCEPTIONS import: `from apitf.sla_exceptions import SLA_FAILURE_EXCEPTIONS`
  NEVER `from apitf import SLA_FAILURE_EXCEPTIONS` (wrong path)
- NEVER add @pytest.mark.xfail to a performance test unless there is a confirmed bug with a BUG-NNN ID
  Adding xfail with no real bug causes XPASS (strict=True fails when the test passes) — this is worse than no xfail

BEGIN YOUR RESPONSE WITH PYTHON CODE NOW:"""

        try:
            fixed_src = _make_api_call(fix_prompt, model, api_key)
            fixed_src = _strip_fences(fixed_src)
            test_file.write_text(fixed_src, encoding="utf-8")
            print(f"[reflector] Test file updated — re-running pytest …")
            # Re-run pytest to confirm corrections didn't break anything
            last_output, exit_code = _run_pytest(env, test_file)
            print(last_output)
            if exit_code != 0:
                print("[reflector] Corrections introduced failures — reverting to previous source.")
                test_file.write_text(current_src, encoding="utf-8")
                break
        except Exception as exc:
            print(f"[reflector] Correction application failed: {exc}", file=sys.stderr)
            break

    return results


# ---------------------------------------------------------------------------
# Test plan reflector
# ---------------------------------------------------------------------------

_PLAN_REQUIRED_SECTIONS = [
    "## 1. Scope",
    "## 2. Approach",
    "## 3. Test Cases",
    "## 4. Test Data",
    "## 5. Environment",
    "## 6. Acceptance Criteria",
    "## 7. Risk",
]
_PLAN_REQUIRED_TECHNIQUES = [
    "Positive", "Schema", "Equivalence", "Boundary",
    "Negative", "Error Handling", "Performance", "Reliability", "Security", "Compatibility",
]
_PLAN_PASS_THRESHOLD = REFLECTOR_PASS_THRESHOLD


def _score_test_plan_structurally(plan_path: Path) -> dict[str, Any]:
    """Fast programmatic structural check — no AI call needed."""
    text = plan_path.read_text(encoding="utf-8")
    issues: list[str] = []

    missing_sections = [s for s in _PLAN_REQUIRED_SECTIONS if s not in text]
    if missing_sections:
        issues.append(f"Missing sections: {missing_sections}")

    missing_techniques = [t for t in _PLAN_REQUIRED_TECHNIQUES if t not in text]
    if missing_techniques:
        issues.append(f"Missing techniques: {missing_techniques}")

    import re as _re
    tc_ids = _re.findall(r"TC-[A-Z]{3}-\d{3}", text)
    if len(tc_ids) < 8:
        issues.append(f"Too few TC IDs ({len(tc_ids)} found, expected ≥ 8)")

    if not any(p in text for p in ("| P1 |", "| P2 |", "| P3 |")):
        issues.append("No priority column (P1/P2/P3) found in TC table")

    if "Risk" not in text:
        issues.append("Risk & Mitigations section missing")

    # Score: start at 100, deduct per issue
    deductions = {
        "Missing sections": 30,
        "Missing techniques": 25,
        "Too few TC IDs": 20,
        "No priority column": 15,
        "Risk": 10,
    }
    score = 100
    for issue in issues:
        for key, penalty in deductions.items():
            if key in issue:
                score -= penalty
                break
    score = max(0, score)
    passed = score >= _PLAN_PASS_THRESHOLD and not issues
    return {"score": score, "passed": passed, "issues": issues, "tc_count": len(tc_ids)}


def _reflect_test_plan(
    env: str,
    plan_path: Path,
    structural: dict[str, Any],
    model: str = ADVISOR_MODEL,
    api_key: str | None = None,
) -> ReviewResult:
    """Opus reviews the generated test plan against the gold-standard rubric."""
    provider = discover_provider(api_key)
    if provider is None:
        print("[plan-reflector] No provider — skipping plan review.", file=sys.stderr)
        return {"score": -1, "passed": False, "deviations": ["No provider"], "corrections": [], "category": "n/a"}

    plan_text = plan_path.read_text(encoding="utf-8")
    prompt = f"""You are a senior QA architect reviewing an auto-generated test plan for the `{env}` API environment.

## Generated test plan
```markdown
{plan_text}
```

## Structural pre-check (automated)
Score: {structural["score"]}/100  |  TC count: {structural["tc_count"]}
Issues found: {structural["issues"] or "none"}

## Scoring rubric (pass threshold = {_PLAN_PASS_THRESHOLD})
Score 0–100 across these dimensions (each worth up to ~14 pts):
- All 7 sections present: Scope, Approach, Test Cases, Test Data, Environment, Acceptance Criteria, Risk & Mitigations
- All 10 techniques covered: Positive, Schema, Equivalence, Boundary, Negative, Error Handling, Performance, Reliability, Security, Compatibility
- TC IDs sequential (TC-XXX-NNN format), ≥ 8 total
- Priority column (P1/P2/P3) present on every TC row
- Risk & Mitigations section with ≥ 3 risk rows
- Acceptance criteria tied to each technique
- Threshold note references YAML (never hardcoded numbers)

Return JSON only — no markdown fences:
{{
  "score": <int 0-100>,
  "passed": <bool>,
  "deviations": ["<missing or wrong element>", ...],
  "corrections": ["<specific actionable markdown edit>", ...],
  "category": "test-plan"
}}"""

    print(f"[plan-reflector] Sending {plan_path.name} to {model} for review …")
    try:
        raw = _make_api_call(prompt, model, api_key)
        text = _strip_fences(raw)
        return json.loads(text)
    except Exception as exc:
        print(f"[plan-reflector] Review call failed: {exc}", file=sys.stderr)
        return {"score": -1, "passed": False, "deviations": [str(exc)], "corrections": [], "category": "error"}


def reflect_test_plan_loop(
    env: str,
    plan_path: Path,
    model: str,
    reflector_model: str = ADVISOR_MODEL,
    api_key: str | None = None,
    max_iter: int = REFLECTOR_MAX_ITER,
) -> None:
    """Structural check → Opus review → AI correction loop for the test plan markdown.

    Mirrors the eval_loop reflector pattern but for markdown rather than pytest files.
    Up to `max_iter` rounds of: score → review → apply corrections → re-score.
    """
    structural = _score_test_plan_structurally(plan_path)
    print(
        f"[plan-reflector] Structural score: {structural['score']}/100 "
        f"({structural['tc_count']} TCs)"
    )
    if structural["issues"]:
        for issue in structural["issues"]:
            print(f"[plan-reflector]   ✗ {issue}")

    if structural["passed"]:
        print("[plan-reflector] Plan passed structural check — skipping Opus review.")
        return

    for round_num in range(1, max_iter + 2):
        review = _reflect_test_plan(env, plan_path, structural, model=reflector_model, api_key=api_key)
        score = review.get("score", -1)
        passed = review.get("passed", False) and score >= REFLECTOR_PASS_THRESHOLD

        if score >= 0:
            print(f"[plan-reflector] Opus score: {score}/100  passed={passed}")
        for dev in review.get("deviations", []):
            print(f"[plan-reflector]   deviation: {dev}")

        if passed or score < 0:
            break

        if round_num > max_iter:
            print(f"[plan-reflector] Max correction rounds ({max_iter}) reached — stopping.")
            break

        corrections = review.get("corrections", [])
        if not corrections or discover_provider(api_key) is None:
            break

        print(f"[plan-reflector] Applying {len(corrections)} correction(s) via {model} …")
        current_src = plan_path.read_text(encoding="utf-8")
        fix_prompt = f"""You are editing a markdown test plan file.

## Current test plan
```markdown
{current_src}
```

## Required corrections
{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(corrections))}

Output ONLY the corrected markdown — no prose, no fences."""

        try:
            fixed = _make_api_call(fix_prompt, model, api_key)
            fixed = _strip_fences(fixed)
            plan_path.write_text(fixed, encoding="utf-8")
            structural = _score_test_plan_structurally(plan_path)
            print(
                f"[plan-reflector] After corrections — structural score: "
                f"{structural['score']}/100 ({structural['tc_count']} TCs)"
            )
            if structural["passed"]:
                print("[plan-reflector] Plan now passes structural check.")
                break
        except Exception as exc:
            print(f"[plan-reflector] Correction failed: {exc} — reverting.", file=sys.stderr)
            plan_path.write_text(current_src, encoding="utf-8")
            break
