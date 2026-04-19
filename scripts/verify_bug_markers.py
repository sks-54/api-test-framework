"""
Pre-push guard — two-directional checks (Rule 8a: enforcement must be bidirectional):

  Forward:  every OPEN QUALITY_FAILURE bug in BUG_REPORT.md has a matching xfail in tests/
  Reverse:  every xfail marker in tests/ references a bug that exists in BUG_REPORT.md
            AND that bug has a non-empty GitHub issue link

Why both directions matter:
  Forward-only: adding an xfail that references a bug NOT in BUG_REPORT.md (and with no
  GitHub issue) is silently accepted — the script never sees the orphaned xfail.
  This was the exact gap that allowed BUG-P-001 and BUG-P-003 to be added as xfail
  references without ever filing a GitHub issue or BUG_REPORT.md entry.

strict=True is required UNLESS the xfail reason also references an SLA_VIOLATION bug —
in that case strict=False is correct because a ConnectionError (SLA) and an AssertionError
(quality) can both appear on the same test, and strict=True would flip a ConnectionError
xpass into a test failure.

Exit 0 = all checks pass (safe to push)
Exit 1 = one or more bugs missing xfail, xfails missing BUG_REPORT entry, or missing
         GitHub issue link (DO NOT push)

Run after every rebase/merge/cherry-pick (Rule 23) and before every push (Rule 8 Step 6).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
BUG_REPORT = ROOT / "BUG_REPORT.md"
TESTS_DIR = ROOT / "tests"
ENV_CONFIG = ROOT / "config" / "environments.yaml"

_KNOWN_STATUSES = {"OPEN", "RESOLVED", "WONT_FIX"}
_KNOWN_CATEGORIES = {"QUALITY_FAILURE", "SLA_VIOLATION"}
# Matches BUG-001, BUG-P-001, BUG-GP-001, etc. — any BUG-<segment>[-<digits>] pattern
_BUG_ID_PATTERN = re.compile(r"BUG-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE)
# Block stops at the next ### BUG- entry OR any ## section heading (prevents last block
# from consuming the rest of the file including SLA Violations / How to Add sections)
_BUG_BLOCK = re.compile(r"###\s+(BUG-[A-Z0-9]+(?:-[A-Z0-9]+)*).*?(?=^#{2,3}\s|\Z)", re.DOTALL | re.IGNORECASE | re.MULTILINE)
_STATUS = re.compile(r"\|\s*\*\*Status\*\*\s*\|\s*([^\|\n]+)")
_CATEGORY = re.compile(r"\|\s*\*\*Category\*\*\s*\|\s*([^\|\n]+)")
_TEST_ID = re.compile(r"\|\s*\*\*Test\*\*\s*\|\s*([^\|\n]+)")
_ISSUE_LINK = re.compile(r"\|\s*\*\*Issue\*\*\s*\|\s*([^\|\n]+)")
# Alias field is a single table row — extract only from there, not from the full block
_ALIAS_FIELD = re.compile(r"\|\s*\*\*Alias\*\*\s*\|\s*([^\|\n]+)")


def load_bug_registry() -> dict[str, dict[str, str]]:
    """
    Return {bug_id_lower: {"status": ..., "category": ..., "test_id": ..., "issue": ..., "aliases": [...]}}
    for every bug in BUG_REPORT.md. Alias IDs (BUG-P-001 etc.) from the Alias field are
    also indexed under their own key so reverse-lookup from xfail reasons works regardless
    of which ID format the developer used.
    """
    text = BUG_REPORT.read_text(encoding="utf-8")
    registry: dict[str, dict[str, str]] = {}
    for match in _BUG_BLOCK.finditer(text):
        block = match.group(0)
        bug_id_m = re.match(r"###\s+(BUG-[A-Z0-9]+(?:-[A-Z0-9]+)*)", block, re.IGNORECASE)
        status_m = _STATUS.search(block)
        category_m = _CATEGORY.search(block)
        test_m = _TEST_ID.search(block)
        issue_m = _ISSUE_LINK.search(block)
        if not (bug_id_m and status_m):
            continue
        raw_status = status_m.group(1).strip().upper()
        if raw_status not in _KNOWN_STATUSES:
            print(
                f"[ERROR] {bug_id_m.group(1)}: unknown status {raw_status!r}. "
                f"Allowed: {sorted(_KNOWN_STATUSES)}"
            )
            sys.exit(1)
        category = category_m.group(1).strip().upper() if category_m else "QUALITY_FAILURE"
        test_id = test_m.group(1).strip() if test_m else "(unknown)"
        issue = issue_m.group(1).strip() if issue_m else ""
        # Strip markdown link syntax to get the raw URL/text
        issue_url = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", issue).strip()

        # Collect alias IDs only from the explicit Alias table row — never from the full block
        # (full-block scan would pick up BUG-XXX references in curl commands or descriptions)
        primary = bug_id_m.group(1).upper()
        alias_m = _ALIAS_FIELD.search(block)
        raw_aliases = alias_m.group(1).strip() if alias_m else ""
        alias_ids = [
            m.group(0).upper()
            for m in _BUG_ID_PATTERN.finditer(raw_aliases)
            if m.group(0).upper() != primary
        ]
        entry = {
            "status": raw_status,
            "category": category,
            "test_id": test_id,
            "bug_id": primary,
            "issue": issue_url,
            "aliases": alias_ids,
        }
        registry[primary.lower()] = entry
        # Index alias IDs so xfail reasons using BUG-P-001 etc. resolve correctly
        for alias in alias_ids:
            registry[alias.lower()] = entry
    return registry


_KNOWN_VIOLATION_TYPES: frozenset[str] = frozenset({"method", "security_headers", "content_negotiation", "performance_sla"})
_KNOWN_VIOLATION_METHODS: frozenset[str] = frozenset({"POST", "DELETE", "PUT", "PATCH"})


def load_yaml_covered_bugs() -> set[str]:
    """
    Return a set of bug_id_lower values covered by environments.yaml known_violations.

    Bugs declared in the YAML security block are covered by config-driven xfail marks
    applied via pytest.param() at collection time — no function-level decorator needed.

    Validates that each entry's type/method will actually produce an xfail at collection
    time. A typo in `type:` or an out-of-set method would silently suppress the xfail
    while passing verification — the guard below makes that a hard exit instead.
    """
    covered: set[str] = set()
    if not ENV_CONFIG.exists():
        return covered
    data = yaml.safe_load(ENV_CONFIG.read_text(encoding="utf-8"))
    for env_name, env_cfg in data.items():
        if env_name == "version" or not isinstance(env_cfg, dict):
            continue
        sec = env_cfg.get("security", {})
        for violation in sec.get("known_violations", []):
            bug_id = violation.get("bug_id", "")
            vtype = violation.get("type", "")
            if not bug_id:
                continue
            if vtype not in _KNOWN_VIOLATION_TYPES:
                print(
                    f"[ERROR] {env_name} known_violation {bug_id!r}: unknown type {vtype!r}. "
                    f"Allowed: {sorted(_KNOWN_VIOLATION_TYPES)}"
                )
                sys.exit(1)
            if vtype == "method":
                method = violation.get("method", "")
                if method not in _KNOWN_VIOLATION_METHODS:
                    print(
                        f"[ERROR] {env_name} known_violation {bug_id!r}: method {method!r} "
                        f"is not iterated by _method_params(). "
                        f"Allowed: {sorted(_KNOWN_VIOLATION_METHODS)}"
                    )
                    sys.exit(1)
            covered.add(bug_id.lower())
    return covered


def _is_xfail_call(node: ast.expr) -> bool:
    """True if the decorator is pytest.mark.xfail(...)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "xfail"
    )


def load_xfail_index() -> dict[str, list[tuple[str, bool, str]]]:
    """
    Return {bug_id_lower: [(reason_text, has_strict_true, source_location), ...]} across all test files.
    Uses ast.parse — immune to decorator ordering and multi-line reason strings.
    Bug ID pattern matches BUG-001, BUG-P-001, BUG-GP-003, etc.
    """
    index: dict[str, list[tuple[str, bool, str]]] = {}

    for test_file in sorted(TESTS_DIR.glob("test_*.py")):
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

                location = f"{test_file.name}::{node.name}"
                for ref in _BUG_ID_PATTERN.findall(reason):
                    key = ref.lower()
                    index.setdefault(key, []).append((reason, strict, location))

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
    for ref in _BUG_ID_PATTERN.findall(reason):
        info = registry.get(ref.lower(), {})
        if info.get("category") == "SLA_VIOLATION":
            return True
    return False


def check_reverse_xfail_coverage(
    xfail_index: dict[str, list[tuple[str, bool, str]]],
    registry: dict[str, dict[str, str]],
    yaml_covered: set[str],
) -> list[str]:
    """
    Reverse check: every xfail marker must reference a bug that:
      1. Exists in BUG_REPORT.md (or environments.yaml known_violations)
      2. Has a non-empty GitHub issue link in BUG_REPORT.md

    This catches the exact failure mode where an xfail is added with a bug reference
    that was never filed as a GitHub issue or added to BUG_REPORT.md.
    """
    failures: list[str] = []
    for bug_id_lower, entries in xfail_index.items():
        if bug_id_lower in yaml_covered:
            continue  # YAML-covered bugs don't need a BUG_REPORT entry
        info = registry.get(bug_id_lower)
        for reason, strict, location in entries:
            if info is None:
                failures.append(
                    f"  [ORPHAN XFAIL] {location}: references {bug_id_lower.upper()!r} "
                    f"which has no entry in BUG_REPORT.md. "
                    f"Rule 19: file a GitHub issue and add a BUG_REPORT.md entry before pushing."
                )
            elif not info.get("issue") or info["issue"].strip() in ("", "—", "-", "N/A"):
                failures.append(
                    f"  [MISSING ISSUE] {location}: references {info['bug_id']!r} "
                    f"which exists in BUG_REPORT.md but has no GitHub issue link. "
                    f"Rule 19: file the issue with `gh issue create` and add the URL to BUG_REPORT.md."
                )
    return failures


def _load_flaky_violations() -> list[str]:
    """
    Return error strings for test functions that use HttpClient but lack
    @pytest.mark.flaky and @pytest.mark.xfail (Testing Standards Rule 10).

    Exempt: HTTPS enforcement tests — they call HttpClient only inside
    pytest.raises(ValueError) and never open a real socket.
    Exempt: xfail tests — pytest-rerunfailures doesn't retry xfail outcomes.
    """
    violations: list[str] = []

    for test_file in sorted(TESTS_DIR.glob("test_*.py")):
        try:
            source = test_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except SyntaxError as exc:
            print(f"[ERROR] Syntax error in {test_file}: {exc}")
            sys.exit(1)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            has_flaky = any(
                (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "flaky")
                or (isinstance(d, ast.Attribute) and d.attr == "flaky")
                for d in node.decorator_list
            )
            has_xfail = any(
                isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "xfail"
                for d in node.decorator_list
            )
            if has_flaky or has_xfail:
                continue

            func_src = ast.get_source_segment(source, node) or ""
            if "HttpClient" not in func_src:
                continue

            # Exempt HTTPS enforcement tests: pytest.raises(ValueError) + no live calls
            if "pytest.raises(ValueError" in func_src and "client.get(" not in func_src:
                continue

            violations.append(
                f"  [MISSING FLAKY] {test_file.name}::{node.name} — "
                "uses HttpClient but has no @pytest.mark.flaky(reruns=2, reruns_delay=2) "
                "(Testing Standards Rule 10)"
            )

    return violations


def main() -> int:
    if not BUG_REPORT.exists():
        print("[ERROR] BUG_REPORT.md not found — cannot verify bug markers.")
        return 1

    registry = load_bug_registry()

    # Collect OPEN QUALITY_FAILURE bugs — deduplicate by primary bug_id (aliases share the
    # same entry object so registry.values() would otherwise yield duplicates)
    open_quality_bugs = list({
        info["bug_id"]: info
        for info in registry.values()
        if info["status"] == "OPEN" and info["category"] == "QUALITY_FAILURE"
    }.values())

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
    yaml_covered = load_yaml_covered_bugs()
    failures: list[str] = []

    for info in open_quality_bugs:
        bug_id = info["bug_id"]
        test_id = info["test_id"]
        key = bug_id.lower()

        # Also check aliases (e.g. BUG-013 has alias BUG-P-001)
        alias_keys = [a.lower() for a in info.get("aliases", [])]
        all_keys = [key] + alias_keys

        if key in yaml_covered or any(k in yaml_covered for k in alias_keys):
            print(
                f"  [OK] {bug_id} ({test_id}): covered by environments.yaml known_violations "
                "(xfail applied via pytest.param at collection time)"
            )
            continue

        matched_entries = []
        for k in all_keys:
            matched_entries.extend(xfail_index.get(k, []))

        if not matched_entries:
            failures.append(
                f"  [MISSING] {bug_id} ({test_id}): "
                f"no @pytest.mark.xfail with reason referencing {bug_id} (or aliases: {alias_keys})"
            )
            continue

        strict_entries = [(r, s, loc) for r, s, loc in matched_entries if s]
        non_strict_entries = [(r, s, loc) for r, s, loc in matched_entries if not s]

        if strict_entries:
            print(f"  [OK] {bug_id} ({test_id}): xfail(strict=True) present")
        elif non_strict_entries:
            # strict=False is acceptable ONLY when the reason also references an SLA bug
            sla_justified = any(
                _reason_covers_sla(reason, registry) for reason, _, _loc in non_strict_entries
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

    # --- Reverse check: every xfail must reference a known, filed bug ---
    reverse_failures = check_reverse_xfail_coverage(xfail_index, registry, yaml_covered)
    failures.extend(reverse_failures)

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

    flaky_violations = _load_flaky_violations()
    if flaky_violations:
        print("\nMISSING FLAKY MARKERS — fix before pushing (Testing Standards Rule 10):")
        for v in flaky_violations:
            print(v)
        print(
            "\nAdd to each listed test:\n"
            "  @pytest.mark.flaky(reruns=2, reruns_delay=2)\n"
            "Exempt: xfail tests and HTTPS enforcement tests (no live network call)."
        )
        return 1

    print(
        f"\n[OK] All {len(open_quality_bugs)} open QUALITY_FAILURE bug(s) have "
        "correct xfail markers, and all xfail markers reference filed bugs — safe to push."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
