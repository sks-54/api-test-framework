"""
Pre-push guard: every OPEN bug in BUG_REPORT.md must have a matching
@pytest.mark.xfail(strict=True, ...) in tests/ whose reason references the bug ID.

Exit 0 = all open bugs have correct xfail markers (safe to push)
Exit 1 = one or more open bugs are missing or have malformed xfail markers (DO NOT push)

Run after every rebase/merge/cherry-pick (Rule 23) and before every push (Rule 8 Step 6).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BUG_REPORT = ROOT / "BUG_REPORT.md"
TESTS_DIR = ROOT / "tests"

_KNOWN_STATUSES = {"OPEN", "RESOLVED", "WONT_FIX"}
_KNOWN_CATEGORIES = {"QUALITY_FAILURE", "SLA_VIOLATION"}
_BUG_BLOCK = re.compile(r"###\s+(BUG-\d+).*?(?=###\s+BUG-|\Z)", re.DOTALL)
_STATUS = re.compile(r"\|\s*\*\*Status\*\*\s*\|\s*([^\|\n]+)")
_CATEGORY = re.compile(r"\|\s*\*\*Category\*\*\s*\|\s*([^\|\n]+)")
_TEST_ID = re.compile(r"\|\s*\*\*Test\*\*\s*\|\s*(TC-[A-Z]-\d+)")


def load_open_quality_bugs() -> list[tuple[str, str]]:
    """
    Return [(bug_id, test_id)] for every OPEN QUALITY_FAILURE bug.

    SLA_VIOLATION bugs are excluded: those manifest as ConnectionError/timeouts,
    not AssertionError, so xfail(raises=AssertionError) does not apply. SLA violations
    are tracked in BUG_REPORT.md and CLAUDE_LOG.md but remain as FAILED in CI until fixed.
    """
    text = BUG_REPORT.read_text(encoding="utf-8")
    open_bugs: list[tuple[str, str]] = []
    for match in _BUG_BLOCK.finditer(text):
        block = match.group(0)
        bug_id_m = re.match(r"###\s+(BUG-\d+)", block)
        status_m = _STATUS.search(block)
        category_m = _CATEGORY.search(block)
        test_m = _TEST_ID.search(block)
        if not (bug_id_m and status_m and test_m):
            continue
        raw_status = status_m.group(1).strip().upper()
        if raw_status not in _KNOWN_STATUSES:
            print(
                f"[ERROR] {bug_id_m.group(1)}: unknown status {raw_status!r}. "
                f"Allowed: {sorted(_KNOWN_STATUSES)}"
            )
            sys.exit(1)
        if raw_status != "OPEN":
            continue
        category = category_m.group(1).strip().upper() if category_m else "QUALITY_FAILURE"
        if category == "SLA_VIOLATION":
            print(f"  [SKIP] {bug_id_m.group(1)}: SLA_VIOLATION — xfail not applicable, tracked in CI as FAILED")
            continue
        open_bugs.append((bug_id_m.group(1), test_m.group(1)))
    return open_bugs


def _is_xfail_call(node: ast.expr) -> bool:
    """True if the decorator is pytest.mark.xfail(...)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "xfail"
    )


def load_xfail_index() -> dict[str, list[tuple[str, bool]]]:
    """
    Return {bug_id_lower: [(reason_text, has_strict_true), ...]} across all test files.
    Uses ast.parse — immune to decorator ordering and multi-line reason strings.
    """
    index: dict[str, list[tuple[str, bool]]] = {}

    for test_file in TESTS_DIR.glob("test_*.py"):
        try:
            tree = ast.parse(test_file.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            print(f"[ERROR] Syntax error in {test_file}: {exc}")
            sys.exit(1)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not _is_xfail_call(deco):
                    continue
                reason = ""
                strict = False
                for kw in deco.keywords:
                    if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
                        reason = str(kw.value.value)
                    if kw.arg == "strict" and isinstance(kw.value, ast.Constant):
                        strict = kw.value.value is True

                # Index by every BUG-NNN / Issue #N reference found in reason
                for ref in re.findall(r"BUG-\d+", reason, re.IGNORECASE):
                    key = ref.lower()
                    index.setdefault(key, []).append((reason, strict))

    return index


def main() -> int:
    if not BUG_REPORT.exists():
        print("[ERROR] BUG_REPORT.md not found — cannot verify bug markers.")
        return 1

    open_bugs = load_open_quality_bugs()
    if not open_bugs:
        print("[OK] No open bugs in BUG_REPORT.md — nothing to verify.")
        return 0

    xfail_index = load_xfail_index()
    failures: list[str] = []

    for bug_id, test_id in open_bugs:
        key = bug_id.lower()
        if key not in xfail_index:
            failures.append(
                f"  [MISSING] {bug_id} ({test_id}): "
                f"no @pytest.mark.xfail with reason referencing {bug_id}"
            )
            continue

        non_strict = [reason for reason, strict in xfail_index[key] if not strict]
        if non_strict:
            failures.append(
                f"  [MALFORMED] {bug_id} ({test_id}): "
                f"xfail found but strict=True is missing (Rule 19 requires strict=True)"
            )
        else:
            print(f"  [OK] {bug_id} ({test_id}): xfail(strict=True) present")

    if failures:
        print("\nXFAIL MARKER PROBLEMS — fix before pushing:")
        for f in failures:
            print(f)
        print(
            "\nFor each missing/malformed bug, add to the correct test:\n"
            "  @pytest.mark.xfail(\n"
            "      strict=True,\n"
            "      raises=AssertionError,\n"
            '      reason="Known API bug BUG-NNN / Issue #N: <description>",\n'
            "  )"
        )
        return 1

    print(f"\n[OK] All {len(open_bugs)} open bug(s) have xfail(strict=True) markers — safe to push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
