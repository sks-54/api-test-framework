"""
advisor_review.py — CLI wrapper around apitf.eval_loop.

Runs the eval loop + Opus reflector on an already-generated test file.
Requires ANTHROPIC_API_KEY for AI-assisted structural fixes and reflector review.

Usage:
  python scripts/advisor_review.py --env <env> --test-file tests/test_<env>.py
  python scripts/advisor_review.py --env cf_petstore --test-file tests/test_cf_petstore_full.py --max-iter 3

The full automated workflow (parse + scaffold + eval + reflect) is available via:
  apitf-run <spec.pdf> --env <env> --sample
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Re-export for backwards-compatibility with any scripts that imported directly
from apitf.eval_loop import (  # noqa: F401
    eval_loop,
    review_phase,
    EvalResult,
    FailureInfo,
    ReviewResult,
)


def main() -> None:
    p = argparse.ArgumentParser(
        prog="advisor_review",
        description="Run the eval loop + Opus reflector on an existing test file.",
    )
    p.add_argument("--env", required=True, metavar="ENV_NAME",
                   help="Environment key (must match environments.yaml and pytest marker)")
    p.add_argument("--test-file", required=True, type=Path, metavar="PATH",
                   help="Path to the test file to evaluate")
    p.add_argument("--max-iter", type=int, default=3, metavar="N",
                   help="Maximum eval-loop iterations (default: 3)")
    p.add_argument("--model", default="claude-sonnet-4-6", metavar="MODEL_ID",
                   help="Model for structural fix re-generation")
    p.add_argument("--reflector-model", default="claude-opus-4-7", metavar="MODEL_ID",
                   help="Model for Opus reflector review")
    args = p.parse_args()

    test_file = args.test_file.resolve()
    if not test_file.exists():
        print(f"[advisor_review] File not found: {test_file}", file=sys.stderr)
        sys.exit(1)

    results = eval_loop(
        env=args.env,
        test_file=test_file,
        max_iter=args.max_iter,
        model=args.model,
        reflector_model=args.reflector_model,
    )

    final = results[-1]
    sys.exit(0 if final.clean else 1)


if __name__ == "__main__":
    main()
