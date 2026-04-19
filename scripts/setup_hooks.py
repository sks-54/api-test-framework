"""Cross-platform git hook installer. Works on macOS, Linux, and Windows.

Run once after cloning:
  python scripts/setup_hooks.py
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def git_dir() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True, text=True, check=True, cwd=ROOT,
    )
    return Path(result.stdout.strip())


def main() -> int:
    hooks_dir = git_dir() / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # On Windows, git hooks must be executable scripts.
    # We use a Python hook so bash is not required.
    hook_body = """\
#!/usr/bin/env python3
\"\"\"Pre-push hook — auto-installed by scripts/setup_hooks.py.\"\"\"
import subprocess, sys
from pathlib import Path

root = Path(__file__).parent.parent.parent  # .git/hooks/ -> repo root
result = subprocess.run(
    [sys.executable, str(root / "scripts" / "verify_bug_markers.py")],
    cwd=root,
)
if result.returncode != 0:
    print()
    print("Push blocked: open QUALITY_FAILURE bugs are missing xfail markers.")
    print("Fix the markers, then push again.")
    sys.exit(1)

print()
print("pre-push checks passed — push proceeding.")
print("Rule 18: run 'python scripts/push.py' to monitor CI to completion.")
"""

    hook_path = hooks_dir / "pre-push"
    hook_path.write_text(hook_body, encoding="utf-8")

    current = hook_path.stat().st_mode
    hook_path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"pre-push hook installed at {hook_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
