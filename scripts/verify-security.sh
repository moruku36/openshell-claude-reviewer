#!/usr/bin/env bash
# Live security verification: creates a scratch sandbox and proves the boundaries hold
# (deny is observed, not assumed). Nothing here modifies any remote repository.
# Usage: scripts/verify-security.sh [owner/repo] [--skip-claude] [--keep]
# Default target: moruku36/multi-ai-workflow (public). Writes reports/verification-*.md
set -uo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need openshell "Run scripts/setup.sh --install"

TARGET="moruku36/multi-ai-workflow" SKIP_CLAUDE=0 KEEP=0
for a in "$@"; do
  case "$a" in
    --skip-claude) SKIP_CLAUDE=1 ;;
    --keep) KEEP=1 ;;
    -*) die "unknown option: $a" ;;
    *) TARGET="$a" ;;
  esac
done
parse_repo "$TARGET"

NAME="reviewer-verify-$(date +%H%M%S)"
POLICY="$ROOT_DIR/.rendered/$NAME.yaml"
REPORT="$ROOT_DIR/reports/verification-$(date +%Y%m%d-%H%M%S).md"
mkdir -p "$ROOT_DIR/reports"
render_policy "$OWNER" "$REPO" 0 "$POLICY"
URL="https://github.com/$OWNER/$REPO.git"

cleanup() { [[ "$KEEP" == "1" ]] || openshell sandbox delete "$NAME" >/dev/null 2>&1; }
trap cleanup EXIT

info "Creating scratch sandbox $NAME"
openshell sandbox create --name "$NAME" --from "$IMAGE" --policy "$POLICY" \
  --label "$SANDBOX_LABEL" --provider "$PROVIDER_CLAUDE" --detach -- sleep 3600 \
  || die "sandbox creation failed"

FAILS=0
{
  echo "# Security verification report"
  echo
  echo "- Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Host: $(uname -s) $(uname -m) $(sw_vers -productVersion 2>/dev/null || true)"
  echo "- Docker: $(docker --version 2>/dev/null)"
  echo "- OpenShell: $(openshell --version 2>&1 | head -1)"
  echo "- Claude Code: $(openshell sandbox exec -n "$NAME" -- claude --version 2>&1 | tail -1)"
  echo "- Target: $OWNER/$REPO"
  echo
  echo "| Test | Expected | Result |"
  echo "|---|---|---|"
} > "$REPORT"

x() { openshell sandbox exec -n "$NAME" -- "$@"; }
# record <label> <expected> <PASS|FAIL>
record() {
  printf '%-40s %-14s %s\n' "$1" "$2" "$3"
  echo "| $1 | $2 | $3 |" >> "$REPORT"
  [[ "$3" == "FAIL" ]] && FAILS=$((FAILS + 1))
  return 0
}
# verdict <label> <expected> <condition-exit-status: 0 = as expected>
verdict() { if [[ "$3" -eq 0 ]]; then record "$1" "$2" PASS; else record "$1" "$2" FAIL; fi; }
expect_ok()   { local l="$1"; shift; if "$@" >/dev/null 2>&1; then record "$l" ALLOWED PASS; else record "$l" ALLOWED FAIL; fi; }
expect_fail() { local l="$1"; shift; if "$@" >/dev/null 2>&1; then record "$l" DENIED FAIL; else record "$l" DENIED PASS; fi; }

# --- functionality
expect_ok "Claude Code starts" x claude --version
if [[ "$SKIP_CLAUDE" == "0" ]]; then
  if x claude -p 'reply with the single word OK' 2>/dev/null | grep -q OK; then
    record "Anthropic connectivity" ALLOWED PASS; else record "Anthropic connectivity" ALLOWED FAIL; fi
fi

# --- GitHub read
CLONE_OK=1
expect_ok "GitHub clone" x sh -c "rm -rf /tmp/v && git clone --depth 1 $URL /tmp/v" || CLONE_OK=0
x sh -c "test -d /tmp/v/.git" >/dev/null 2>&1 || CLONE_OK=0
expect_ok "GitHub fetch" x sh -c "cd /tmp/v && git fetch --depth 1 origin"
CODE="$(x curl -s -o /dev/null -w '%{http_code}' "https://api.github.com/repos/$OWNER/$REPO" 2>/dev/null | tail -1)"
if [[ "$CODE" == "200" ]]; then verdict "GitHub API GET (target repo)" ALLOWED 0; else verdict "GitHub API GET (target repo)" ALLOWED 1; fi

# --- GitHub write denial (dry-run / empty body: safe even if it were not denied)
# A failed clone would make the push "fail" for the wrong reason, so require it.
if [[ "$CLONE_OK" == "1" ]]; then expect_fail "GitHub push --dry-run" x sh -c "cd /tmp/v && git push --dry-run origin HEAD:refs/heads/openshell-verify-deny"
else record "GitHub push --dry-run" DENIED FAIL; fi
BODY="$(x curl -s -X POST -H 'Content-Type: application/json' -d '{}' \
  "https://api.github.com/repos/$OWNER/$REPO/issues" 2>/dev/null)"
if grep -q policy_denied <<<"$BODY"; then record "GitHub API mutation (POST issues)" DENIED PASS
else record "GitHub API mutation (POST issues)" DENIED FAIL; fi
CODE="$(x curl -s -o /dev/null -w '%{http_code}' https://api.github.com/repos/octocat/Hello-World 2>/dev/null | tail -1)"
if [[ "$CODE" == "403" || "$CODE" == "000" ]]; then verdict "GitHub API GET (other repo)" DENIED 0; else verdict "GitHub API GET (other repo)" DENIED 1; fi

# --- arbitrary network
expect_fail "Unapproved host (example.com)" x curl -sS -m 15 https://example.com
expect_fail "Unapproved host (registry.npmjs.org)" x curl -sS -m 15 https://registry.npmjs.org/

# --- host filesystem / credentials (existence only; values are never read)
# shellcheck disable=SC2016  # $HOME must expand inside the sandbox
expect_fail "Host paths (~/.ssh ~/.aws /Users)" x sh -c 'test -e "$HOME/.ssh" -o -e "$HOME/.aws" -o -e /Users -o -e /host_mnt -o -e /Volumes'
expect_fail "Write to /usr" x sh -c 'touch /usr/openshell-verify'
# shellcheck disable=SC2016  # expanded inside the sandbox; only a classification is printed
CLS="$(x sh -c 'case "$ANTHROPIC_API_KEY" in openshell:resolve:*) echo placeholder;; sk-ant-*) echo RAW;; "") echo unset;; *) echo other;; esac' 2>/dev/null | tail -1)"
if [[ "$CLS" == "placeholder" ]]; then verdict "Credential in env is opaque placeholder" placeholder 0; else verdict "Credential in env is opaque placeholder" placeholder 1; fi

# --- deny events visible in the OpenShell log
sleep 2
DENIES="$(openshell logs "$NAME" --since 15m --source sandbox 2>/dev/null | grep -c DENIED || true)"
if [[ "${DENIES:-0}" -ge 3 ]]; then verdict "Deny events in OpenShell log (>=3)" logged 0; else verdict "Deny events in OpenShell log (>=3)" logged 1; fi

echo
echo "Report: $REPORT (failures: $FAILS)"
[[ "$FAILS" -eq 0 ]]
