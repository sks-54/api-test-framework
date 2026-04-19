#!/usr/bin/env bash
# Install git hooks for this repo. Run once after cloning: bash scripts/setup_hooks.sh
set -euo pipefail

HOOKS_DIR="$(git rev-parse --git-dir)/hooks"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

cat > "$HOOKS_DIR/pre-push" << 'HOOK'
#!/usr/bin/env bash
# Auto-installed by scripts/setup_hooks.sh — do not edit directly
set -euo pipefail

echo "▶ pre-push: running verify_bug_markers.py (Rule 8 Step 6)..."
python3 scripts/verify_bug_markers.py || {
    echo ""
    echo "❌ Push blocked: open QUALITY_FAILURE bugs are missing xfail markers."
    echo "   Fix the markers, then push again."
    exit 1
}

echo ""
echo "✅ pre-push checks passed — push proceeding."
echo "   Rule 18: run 'gh run watch \$(gh run list --limit 1 --json databaseId -q .[0].databaseId)'"
echo "   to monitor CI. Do not move on until all checks complete."
HOOK

chmod +x "$HOOKS_DIR/pre-push"
echo "✅ pre-push hook installed at $HOOKS_DIR/pre-push"
