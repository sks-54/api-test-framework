"""Cross-platform push wrapper. Works on macOS, Linux, and Windows.

Use this instead of 'git push' on this project.
Enforces Rule 18: CI is monitored to completion after every push.

Usage:
  python scripts/push.py [extra git-push args]
"""

from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=False)


def main() -> int:
    extra = sys.argv[1:]
    run(["git", "push"] + extra)

    result = subprocess.run(
        ["gh", "run", "list", "--branch",
         subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
         "--limit", "1", "--json", "databaseId", "-q", ".[0].databaseId"],
        capture_output=True, text=True, check=True,
    )
    run_id = result.stdout.strip()

    print(f"\nMonitoring CI run {run_id} (Rule 18 — do not switch tasks)...")
    run(["gh", "run", "watch", run_id, "--exit-status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
