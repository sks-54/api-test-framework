"""
apitf.eval_loop — automated eval loop and Opus reflector.

Requires ANTHROPIC_API_KEY for:
  - AI-assisted structural fix (re-generates broken test code)
  - Opus reflector review (scores the final test file)

Key resolution order (detect_ai_mode):
  1. Explicit key passed via --api-key flag
  2. ANTHROPIC_API_KEY environment variable
  3. .env file in the project root (KEY=VALUE format, no quotes needed)

Without a key all AI steps are skipped and a stub result is returned.
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


def _load_dotenv(project_root: Path | None = None) -> str | None:
    """Read ANTHROPIC_API_KEY from a .env file in the project root.

    Supports bare KEY=VALUE and KEY="VALUE" formats. Returns the value or None.
    Never raises — a malformed or missing .env is silently ignored.
    """
    root = project_root or Path(__file__).parent.parent
    dotenv = root / ".env"
    if not dotenv.exists():
        return None
    try:
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == "ANTHROPIC_API_KEY":
                return val.strip().strip('"').strip("'") or None
    except OSError:
        pass
    return None


def _claude_cli_available() -> bool:
    """True if the `claude` CLI is in PATH and responds (Claude Code authenticated session)."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _claude_cli_call(prompt: str, model: str) -> str:
    """Call the claude CLI with a prompt via stdin, returning the response text.

    Uses the authenticated Claude Code session — no API key needed.
    Passes the prompt via stdin rather than -p to avoid shell length limits
    and subprocess argument-list timeouts on long prompts.
    """
    result = subprocess.run(
        ["claude", "--model", model, "-p", "--allowedTools", "", "--output-format", "text", "-"],
        input=prompt,
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")
    return result.stdout.strip()


def detect_ai_mode(explicit_key: str | None = None) -> tuple[str | None, str]:
    """Detect which AI mode is available and return (api_key_or_sentinel, source_label).

    Priority:
      1. Claude CLI authenticated session (CLAUDECODE=1 + `claude` in PATH) — no key needed
      2. Explicit key passed via --api-key flag
      3. ANTHROPIC_API_KEY environment variable
      4. .env file in project root (ANTHROPIC_API_KEY=sk-ant-...)
      5. None — falls back to 5-test stub, no reflector

    Claude CLI is checked first because it requires zero configuration when running inside
    Claude Code — the user's account is already authenticated.

    Returns:
        (value, source) where source is one of:
          "claude_cli" — authenticated via Claude Code session (value = "__claude_cli__")
          "explicit"   — key supplied via --api-key
          "env"        — key found in ANTHROPIC_API_KEY env var
          "dotenv"     — key loaded from .env file
          "none"       — no key available
    """
    # Claude Code authenticated session — first priority, zero config required
    if os.environ.get("CLAUDECODE") == "1" and _claude_cli_available():
        return "__claude_cli__", "claude_cli"
    if explicit_key:
        return explicit_key, "explicit"
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key, "env"
    dotenv_key = _load_dotenv()
    if dotenv_key:
        return dotenv_key, "dotenv"
    return None, "none"


def _get_client(model: str | None = None, api_key: str | None = None):
    """Return (anthropic.Anthropic(), model) or (None, None) if unavailable.

    When source is claude_cli, returns (None, None) — callers must use _claude_cli_call().
    """
    key, source = detect_ai_mode(api_key)
    if not key or source == "claude_cli":
        return None, None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key), model or ADVISOR_MODEL
    except ImportError:
        logger.warning("[eval_loop] 'anthropic' package not installed — pip install anthropic")
        return None, None


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = "\n".join(text.split("\n")[:-1])
    return text.strip()


# ---------------------------------------------------------------------------
# Reflector (Opus review)
# ---------------------------------------------------------------------------

def _make_api_call(prompt: str, model: str, api_key: str | None) -> str:
    """Route an API call through anthropic SDK or claude CLI depending on auth mode."""
    _, source = detect_ai_mode(api_key)
    if source == "claude_cli":
        return _claude_cli_call(prompt, model)
    client, resolved_model = _get_client(model, api_key=api_key)
    if client is None:
        raise RuntimeError("No API client available")
    message = client.messages.create(
        model=resolved_model,
        max_tokens=MAX_RESPONSE_TOKENS,
        system="You are a senior QA architect. Return structured JSON only.",
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def review_phase(
    phase: str, diff: str, rubric: dict[str, Any], api_key: str | None = None
) -> ReviewResult:
    """Submit a code diff to Opus for rubric-based review.

    Returns a ReviewResult dict with: score, passed, deviations, corrections, category.
    Works with ANTHROPIC_API_KEY, .env file, or authenticated Claude Code session.
    Falls back to a stub result when no auth method is available.
    """
    resolved_key, source = detect_ai_mode(api_key)
    if not resolved_key:
        logger.info("[reflector] No auth available — returning stub result")
        return {
            "score": -1,
            "passed": False,
            "deviations": ["No ANTHROPIC_API_KEY — live review skipped."],
            "corrections": ["Set ANTHROPIC_API_KEY and re-run to get live Opus review."],
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

    logger.info("[reflector] Sending %d-char prompt to %s (via %s)", len(prompt), ADVISOR_MODEL, source)
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
    resolved_key, source = detect_ai_mode(api_key)
    if not resolved_key:
        print("[reflector] No auth available — skipping reflector review.", file=sys.stderr)
        return {
            "score": -1,
            "passed": False,
            "deviations": ["No ANTHROPIC_API_KEY — reflector skipped."],
            "corrections": ["Set ANTHROPIC_API_KEY or run inside Claude Code to enable live Opus review."],
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
{pytest_output[-3000:]}
```

## Scoring rubric (pass threshold = 70)
Score 0-100 across these dimensions (each worth up to ~15 pts):
- Technique coverage: equivalence, boundary, positive, negative, performance, security all present
- Zero hardcoded values — all thresholds and URLs from env_config
- HttpClient used as context manager (never raw requests)
- @pytest.mark.flaky on every live HTTP call; NOT on xfail or HTTPS-only tests
- xfail(strict=True) with SLA_FAILURE_EXCEPTIONS for documented API bugs
- assert result.passed, result.errors pattern for all validator calls

Return JSON only — no markdown fences:
{{
  "score": <int 0-100>,
  "passed": <bool>,
  "deviations": ["<missing technique or rule>", ...],
  "corrections": ["<specific actionable fix>", ...],
  "category": "test-coverage"
}}"""

    print(f"[reflector] Sending {test_file.name} to {ADVISOR_MODEL} for review (via {source}) …")
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
    client, effective_model = _get_client(model, api_key=api_key)
    if client is None:
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

    print(f"[eval-loop] Calling {effective_model} to fix structural failures …")
    try:
        message = client.messages.create(
            model=effective_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        src = _strip_fences(message.content[0].text)
        test_file.write_text(src, encoding="utf-8")
        print(f"[eval-loop] Test file rewritten: {test_file.name}")
        return True
    except Exception as exc:
        print(f"[eval-loop] AI fix failed: {exc}", file=sys.stderr)
        return False


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
    resolved_key, key_source = detect_ai_mode(api_key)
    if resolved_key:
        mode_label = {
            "claude_cli": "Claude Code session (auto-detected)",
            "explicit": "explicit --api-key",
            "env": "ANTHROPIC_API_KEY env var (auto-detected)",
            "dotenv": ".env file (auto-detected)",
        }.get(key_source, key_source)
        print(f"[eval-loop] AI mode: {mode_label}")
    else:
        print("[eval-loop] AI mode: none — structural fixes and reflector review disabled")
        print("            Set ANTHROPIC_API_KEY or pass --api-key to enable.")

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
            fixed = _ai_fix_structural(env, test_file, output, model, api_key=resolved_key)
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
            print(
                "\n  Action required:\n"
                "  1. File a GitHub issue for each deviation.\n"
                "  2. Add @pytest.mark.xfail(strict=True, reason='Bug #N: ...') to the test.\n"
                "  3. Re-run apitf-run (or pytest --env) to confirm xfailed state."
            )
            break
        else:
            break

    # ── Reflector + correction feedback loop ───────────────────────────────
    REFLECTOR_MAX_ITER = 2  # max rounds of Opus → apply corrections → re-score
    for reflector_round in range(1, REFLECTOR_MAX_ITER + 2):
        print(f"\n[reflector] ── Opus reflector review (round {reflector_round}) ──────────────")
        review = _reflect_test_file(env, test_file, last_output, reflector_model, api_key=resolved_key)
        score = review.get("score", -1)
        passed_review = review.get("passed", False)
        print(f"[reflector] Score   : {score}/100")
        print(f"[reflector] Passed  : {'✓ yes' if passed_review else '✗ no (threshold = 70)'}")
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
        if not corrections or not resolved_key:
            break

        # Apply Opus corrections via AI re-generation
        print(f"\n[reflector] Applying {len(corrections)} correction(s) via {model} …")
        current_src = test_file.read_text(encoding="utf-8")
        corrections_text = "\n".join(f"- {c}" for c in corrections)
        fix_prompt = f"""You are fixing a pytest test file based on a QA architect's review.

## Current file
```python
{current_src}
```

## Required corrections (apply ALL of these)
{corrections_text}

Framework rules (must not be broken):
- All thresholds/URLs from env_config — zero hardcoded numbers or hostnames
- HttpClient used as context manager
- @pytest.mark.flaky(reruns=2, reruns_delay=2) on every live HTTP call
- Negative tests assert EXACT status code (never `in (...)` or `>= 400`)
- assert result.passed, result.errors for all validator calls
- Full type hints on every function

Output ONLY the corrected Python source — no markdown fences, no prose."""

        try:
            fixed_src = _make_api_call(fix_prompt, model, resolved_key)
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
