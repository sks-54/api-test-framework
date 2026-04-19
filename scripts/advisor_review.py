"""
advisor_review.py — Stub for Anthropic SDK Opus advisor reviews.

Requires ANTHROPIC_API_KEY — see ENHANCEMENTS.md E-04.
No network calls are made in this stub. Uncomment the SDK block to activate.
"""

from __future__ import annotations

# Uncomment when implementing E-04:
# import anthropic

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

ADVISOR_MODEL: str = "claude-opus-4-7"
MAX_RESPONSE_TOKENS: int = 1024
STUB_DEFAULT_SCORE: int = -1

ReviewResult = dict[str, Any]


def _build_prompt(phase: str, diff: str, rubric: dict[str, Any]) -> str:
    return f"""You are a senior QA architect reviewing phase "{phase}".

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
}}""".strip()


def _parse_response(raw_text: str) -> ReviewResult:
    required = ("score", "passed", "deviations", "corrections", "category")
    try:
        result: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Advisor returned non-JSON: {raw_text!r}") from exc
    missing = [k for k in required if k not in result]
    if missing:
        raise ValueError(f"Advisor response missing keys: {missing}")
    return result


def review_phase(phase: str, diff: str, rubric: dict[str, Any]) -> ReviewResult:
    """Submit a diff to claude-opus-4-7 for rubric-based review.

    Requires ANTHROPIC_API_KEY — see ENHANCEMENTS.md E-04.
    Currently a stub — see E-04 implementation block below.

    Args:
        phase:  Phase label, e.g. "phase-3-tests"
        diff:   Output of `git diff`
        rubric: Dict with "pass_threshold" (int) and "rules" (list[str])

    Returns:
        ReviewResult with score, passed, deviations, corrections, category.
    """
    prompt = _build_prompt(phase, diff, rubric)
    logger.info("[advisor_review] STUB — would send %d-char prompt to %s", len(prompt), ADVISOR_MODEL)

    # ------------------------------------------------------------------
    # E-04 IMPLEMENTATION BLOCK — uncomment when ready
    # ------------------------------------------------------------------
    # client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    # message = client.messages.create(
    #     model=ADVISOR_MODEL,
    #     max_tokens=MAX_RESPONSE_TOKENS,
    #     system="You are a senior QA architect. Return structured JSON only.",
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # return _parse_response(message.content[0].text)
    # ------------------------------------------------------------------

    return {
        "score":       STUB_DEFAULT_SCORE,
        "passed":      False,
        "deviations":  ["Stub active — no real evaluation performed."],
        "corrections": ["Implement E-04 to enable live advisor reviews."],
        "category":    "style",
    }
