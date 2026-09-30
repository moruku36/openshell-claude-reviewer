#!/usr/bin/env bash
# Minimal secret scan over tracked + untracked (non-ignored) files. Used locally before
# commit/push and in CI. Exit 1 if anything credential-shaped is found.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PATTERN='sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|gh[ousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}'
FILES=$(git ls-files --cached --others --exclude-standard)
# shellcheck disable=SC2086
if grep -nEI -e "$PATTERN" $FILES scripts/scan-secrets.sh 2>/dev/null | grep -v 'scripts/scan-secrets.sh:'; then
  echo "secret scan: FOUND credential-like strings" >&2; exit 1
fi
if git ls-files --cached --others --exclude-standard | grep -E '(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_rsa.*)$'; then
  echo "secret scan: FOUND credential-like files" >&2; exit 1
fi
echo "secret scan: OK"
