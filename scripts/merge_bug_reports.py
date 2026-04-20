"""Merge per-resource bug reports into the master BUG_REPORT.md.

Usage
-----
    python scripts/merge_bug_reports.py jsonplaceholder
    python scripts/merge_bug_reports.py jsonplaceholder --bug-dir bugs --output BUG_REPORT.md

Reads:  bugs/BUG_REPORT_<env>_*.md  (written by apitf-run parallel workers)
Writes: BUG_REPORT.md               (master — read by verify_bug_markers.py)

IDs are renumbered sequentially from the next free BUG-NNN slot in the master.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def merge_bug_reports(
    env: str,
    bug_dir: Path = Path("bugs"),
    output: Path = Path("BUG_REPORT.md"),
) -> int:
    """Merge bugs/BUG_REPORT_<env>_*.md into *output*.

    Returns the number of entries merged (0 if nothing to merge).
    """
    parts = sorted(bug_dir.glob(f"BUG_REPORT_{env}_*.md"))
    if not parts:
        print(f"[merge] No per-resource reports found in {bug_dir} for env '{env}'")
        return 0

    all_entries: list[str] = []
    for part in parts:
        text = part.read_text(encoding="utf-8")
        for raw in re.split(r"\n(?=### BUG-)", text):
            raw = raw.strip()
            if raw.startswith("### BUG-"):
                all_entries.append(raw)

    if not all_entries:
        print("[merge] No bug entries found in per-resource reports.")
        return 0

    existing = output.read_text(encoding="utf-8") if output.exists() else ""
    next_n = max((int(i) for i in re.findall(r"BUG-(\d{3})", existing)), default=0) + 1

    renumbered: list[str] = []
    for entry in all_entries:
        old_match = re.match(r"### (BUG-\d{3})", entry)
        new_id = f"BUG-{next_n:03d}"
        if old_match:
            entry = entry.replace(old_match.group(1), new_id)
        renumbered.append(entry)
        next_n += 1

    merged = "\n\n".join(renumbered)
    if "## Open Bugs" in existing:
        insert_pos = existing.index("## Open Bugs") + len("## Open Bugs\n")
        updated = existing[:insert_pos] + "\n" + merged + "\n\n" + existing[insert_pos:]
    else:
        updated = existing.rstrip() + "\n\n" + merged + "\n"

    output.write_text(updated, encoding="utf-8")
    print(f"[merge] Wrote {len(renumbered)} entry/entries to {output}")
    return len(renumbered)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Merge per-resource bug reports into BUG_REPORT.md")
    p.add_argument("env", help="Environment key (e.g. 'jsonplaceholder')")
    p.add_argument("--bug-dir", type=Path, default=Path("bugs"), metavar="DIR",
                   help="Directory containing per-resource reports (default: bugs/)")
    p.add_argument("--output", type=Path, default=Path("BUG_REPORT.md"), metavar="FILE",
                   help="Master output file (default: BUG_REPORT.md)")
    args = p.parse_args()

    count = merge_bug_reports(args.env, args.bug_dir, args.output)
    sys.exit(0 if count >= 0 else 1)
