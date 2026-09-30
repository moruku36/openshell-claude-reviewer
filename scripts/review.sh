#!/usr/bin/env bash
# Run the Claude Code Reviewer against a GitHub repository in an ephemeral sandbox.
# Usage: scripts/review.sh <https://github.com/owner/repo | owner/repo> [--ref BRANCH] [--token] [--out FILE]
#   --token   also attach the read-only GitHub provider (needed for private repos)
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: review.sh <repo-url|owner/repo> [--ref BRANCH] [--token] [--out FILE]"
TARGET="$1"; shift
REF="" TOKEN=0 OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) REF="${2:?--ref needs a value}"; shift 2 ;;
    --token) TOKEN=1; shift ;;
    --out) OUT="${2:?--out needs a value}"; shift 2 ;;
    *) die "unknown option: $1" ;;
  esac
done

need openshell "Run scripts/setup.sh --install"
parse_repo "$TARGET"
[[ -z "$REF" || "$REF" =~ ^[A-Za-z0-9._/-]+$ ]] || die "invalid --ref"

TS="$(date +%Y%m%d-%H%M%S)"
NAME="reviewer-$(echo "$REPO" | tr '[:upper:]._' '[:lower:]--' | cut -c1-30)-$TS"
POLICY="$ROOT_DIR/.rendered/$NAME.yaml"
OUT="${OUT:-$ROOT_DIR/reports/$OWNER-$REPO-$TS.md}"
mkdir -p "$(dirname "$OUT")"
render_policy "$OWNER" "$REPO" "$TOKEN" "$POLICY"

URL="https://github.com/$OWNER/$REPO.git"
GIT="git"
PROVIDERS=(--provider "$PROVIDER_CLAUDE")
if [[ "$TOKEN" == "1" ]]; then
  # The env var holds an opaque placeholder; the sandbox proxy swaps in the real
  # token only for the bound github.com / api.github.com repo endpoints.
  # shellcheck disable=SC2016  # $GITHUB_TOKEN must expand inside the sandbox
  GIT='git -c "http.extraheader=Authorization: Bearer $GITHUB_TOKEN"'
  PROVIDERS+=(--provider "$PROVIDER_GITHUB")
fi
BRANCH_ARGS=""; [[ -n "$REF" ]] && BRANCH_ARGS="--branch $REF"

# OWNER/REPO/REF are regex-validated above, so this string is safe to interpolate.
INNER="set -eu; export GIT_TERMINAL_PROMPT=0
$GIT clone --depth 50 $BRANCH_ARGS $URL /sandbox/repo
cd /sandbox/repo
exec claude -p \"\$(cat /opt/reviewer/reviewer.md)\" \
  --allowedTools 'Read,Grep,Glob,Bash(git log:*),Bash(git diff:*),Bash(git show:*),Bash(git status:*)' \
  --disallowedTools 'Edit,Write,NotebookEdit,WebFetch,WebSearch'"

info "Sandbox: $NAME  target: $OWNER/$REPO${REF:+@$REF}  report: $OUT"
# Ephemeral (--no-keep): the sandbox and its injected credentials are deleted on exit.
openshell sandbox create --name "$NAME" --from "$IMAGE" --policy "$POLICY" \
  --label "$SANDBOX_LABEL" "${PROVIDERS[@]}" --no-keep -- sh -c "$INNER" | tee "$OUT"
info "Report written to $OUT"
