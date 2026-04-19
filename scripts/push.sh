#!/usr/bin/env bash
# Use this instead of 'git push' on this project.
# Enforces Rule 18: CI is monitored to completion after every push.
set -euo pipefail

git push "$@"

RUN_ID=$(gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId -q '.[0].databaseId')
echo ""
echo "▶ Monitoring CI run $RUN_ID (Rule 18 — do not switch tasks)..."
gh run watch "$RUN_ID" --exit-status
