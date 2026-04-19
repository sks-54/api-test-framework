"""Reads DELIVERABLES.md and reports completion stats, pending items, and deviations."""

from __future__ import annotations

import re
from pathlib import Path

_TASK_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*[-*]\s+\[(?P<marker>[xX! ])\]\s+(?P<label>.+)$"
)
_MARKER_COMPLETE = frozenset({"x", "X"})
_MARKER_DEVIATION = "!"


def _parse_deliverables(deliverables_path: Path) -> list[tuple[str, str]]:
    if not deliverables_path.exists():
        raise FileNotFoundError(f"Deliverables file not found: {deliverables_path}")
    items: list[tuple[str, str]] = []
    for line in deliverables_path.read_text(encoding="utf-8").splitlines():
        match = _TASK_PATTERN.match(line)
        if match:
            items.append((match.group("marker"), match.group("label").strip()))
    return items


def get_completion_stats(deliverables_path: Path) -> dict:
    items = _parse_deliverables(deliverables_path)
    total = len(items)
    completed, pending, deviations = [], [], []
    for marker, label in items:
        if marker in _MARKER_COMPLETE:
            completed.append(label)
        elif marker == _MARKER_DEVIATION:
            deviations.append(label)
        else:
            pending.append(label)
    return {
        "total": total,
        "completed": len(completed),
        "percentage": round(len(completed) / total * 100, 2) if total > 0 else 0.0,
        "pending": pending,
        "deviations": deviations,
    }


def print_summary(deliverables_path: Path) -> None:
    stats = get_completion_stats(deliverables_path)
    w = 60
    print("=" * w)
    print(f"DELIVERABLES SUMMARY — {deliverables_path.name}")
    print("=" * w)
    print(f"{'Total items':<14}: {stats['total']}")
    print(f"{'Completed':<14}: {stats['completed']}   ({stats['percentage']} %)")
    print(f"{'Pending':<14}: {len(stats['pending'])}")
    print(f"{'Deviations':<14}: {len(stats['deviations'])}")
    if stats["pending"]:
        print("-" * w)
        print("PENDING")
        for item in stats["pending"]:
            print(f"  - {item}")
    if stats["deviations"]:
        print("-" * w)
        print("DEVIATIONS")
        for item in stats["deviations"]:
            print(f"  - {item}")
    print("=" * w)


def check_deviations(deliverables_path: Path) -> list[str]:
    return [label for marker, label in _parse_deliverables(deliverables_path)
            if marker == _MARKER_DEVIATION]
