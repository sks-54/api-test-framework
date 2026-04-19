"""
Pre-push guard: every OPEN QUALITY_FAILURE bug in BUG_REPORT.md must have a matching
@pytest.mark.xfail in tests/ whose reason references the bug ID.

strict=True is required UNLESS the xfail reason also references an SLA_VIOLATION bug —
in that case strict=False is correct because a ConnectionError (SLA) and an AssertionError
(quality) can both appear on the same test, and strict=True would flip a ConnectionError
xpass into a test failure.

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


def load_bug_registry() -> dict[str, dict[str, str]]:
    """
    Return {bug_id_lower: {"status": ..., "category": ..., "test_id": ...}}
    for every bug in BUG_REPORT.md.
    """
    text = BUG_REPORT.read_text(encoding="utf-8")
    registry: dict[str, dict[str, str]] = {}
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
        category = category_m.group(1).strip().upper() if category_m else "QUALITY_FAILURE"
        registry[bug_id_m.group(1).lower()] = {
            "status": raw_status,
            "category": category,
            "test_id": test_m.group(1),
            "bug_id": bug_id_m.group(1),
        }
    return registry


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

                for ref in re.findall(r"BUG-\d+", reason, re.IGNORECASE):
                    key = ref.lower()
                    index.setdefault(key, []).append((reason, strict))

    return index


def _reason_covers_sla(reason: str, registry: dict[str, dict[str, str]]) -> bool:
    """
    True if the xfail reason string references at least one SLA_VIOLATION bug.
    Used to determine whether strict=False is acceptable for a given xfail marker.

    Rationale: a test that covers both a QUALITY_FAILURE (raises AssertionError) and
    an SLA_VIOLATION (raises ConnectionError) must use strict=False — otherwise an
    unexpected xpass on the SLA path would turn XPASS into a test failure, which is
    incorrect. When strict=False is used, the quality bug is still tracked; an evaluator
    watching for xpass must check both conditions.
    """
    for ref in re.findall(r"BUG-\d+", reason, re.IGNORECASE):
        info = registry.get(ref.lower(), {})
        if info.get("category") == "SLA_VIOLATION":
            return True
    return False


def main() -> int:
    if not BUG_REPORT.exists():
        print("[ERROR] BUG_REPORT.md not found — cannot verify bug markers.")
        return 1

    registry = load_bug_registry()

    # Collect OPEN QUALITY_FAILURE bugs — the ones that require xfail markers
    open_quality_bugs = [
        info for info in registry.values()
        if info["status"] == "OPEN" and info["category"] == "QUALITY_FAILURE"
    ]

    for info in registry.values():
        if info["status"] != "OPEN":
            continue
        if info["category"] == "SLA_VIOLATION":
            print(
                f"  [SKIP] {info['bug_id']}: SLA_VIOLATION — "
                "ConnectionError/timeout, not AssertionError; xfail(raises=AssertionError) "
                "does not apply. Tracked in BUG_REPORT.md + CI as FAILED."
            )

    if not open_quality_bugs:
        print("[OK] No open QUALITY_FAILURE bugs — nothing to verify.")
        return 0

    xfail_index = load_xfail_index()
    failures: list[str] = []

    for info in open_quality_bugs:
        bug_id = info["bug_id"]
        test_id = info["test_id"]
        key = bug_id.lower()

        if key not in xfail_index:
            failures.append(
                f"  [MISSING] {bug_id} ({test_id}): "
                f"no @pytest.mark.xfail with reason referencing {bug_id}"
            )
            continue

        entries = xfail_index[key]
        strict_entries = [(r, s) for r, s in entries if s]
        non_strict_entries = [(r, s) for r, s in entries if not s]

        if strict_entries:
            print(f"  [OK] {bug_id} ({test_id}): xfail(strict=True) present")
        elif non_strict_entries:
            # strict=False is acceptable ONLY when the reason also references an SLA bug
            sla_justified = any(
                _reason_covers_sla(reason, registry) for reason, _ in non_strict_entries
            )
            if sla_justified:
                print(
                    f"  [OK] {bug_id} ({test_id}): xfail(strict=False) present — "
                    "justified: reason references an SLA_VIOLATION bug (ConnectionError path)"
                )
            else:
                failures.append(
                    f"  [MALFORMED] {bug_id} ({test_id}): "
                    "xfail found but strict=True is missing and no SLA bug co-referenced "
                    "(Rule 19 requires strict=True for pure QUALITY_FAILURE bugs)"
                )
        else:
            failures.append(
                f"  [MISSING] {bug_id} ({test_id}): "
                f"no @pytest.mark.xfail with reason referencing {bug_id}"
            )

    if failures:
        print("\nXFAIL MARKER PROBLEMS — fix before pushing:")
        for f in failures:
            print(f)
        print(
            "\nFor a pure QUALITY_FAILURE bug, add:\n"
            "  @pytest.mark.xfail(\n"
            "      strict=True,\n"
            "      raises=AssertionError,\n"
            '      reason="Known API bug BUG-NNN / Issue #N: <description>",\n'
            "  )\n"
            "\nFor a test covering BOTH a QUALITY_FAILURE and an SLA_VIOLATION, use:\n"
            "  @pytest.mark.xfail(\n"
            "      strict=False,\n"
            "      raises=(AssertionError, requests.exceptions.ConnectionError),\n"
            '      reason="Known API bugs BUG-NNN (quality) and BUG-MMM (SLA): ...",\n'
            "  )"
        )
        return 1

    print(
        f"\n[OK] All {len(open_quality_bugs)} open QUALITY_FAILURE bug(s) have "
        "correct xfail markers — safe to push."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
