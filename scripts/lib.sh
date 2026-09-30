#!/usr/bin/env bash
# Shared helpers. Source this file; do not execute it.
# shellcheck shell=bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC2034  # used by the scripts that source this file
IMAGE="${REVIEWER_IMAGE:-openshell-claude-reviewer:local}"
# shellcheck disable=SC2034
PROVIDER_CLAUDE="reviewer-claude"
# shellcheck disable=SC2034
PROVIDER_GITHUB="reviewer-github"
# shellcheck disable=SC2034
SANDBOX_LABEL="app=claude-reviewer"

die() { echo "error: $*" >&2; exit 1; }
info() { echo "==> $*"; }
need() { command -v "$1" >/dev/null 2>&1 || die "'$1' not found. $2"; }

# parse_repo <url|owner/repo>  -> sets OWNER and REPO (strictly validated; they are
# interpolated into the sandbox policy and into a shell command, so no other chars).
parse_repo() {
  local in="$1" path
  path="${in#https://github.com/}"
  path="${path%.git}"
  path="${path%/}"
  [[ "$path" =~ ^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$ ]] \
    || die "expected https://github.com/<owner>/<repo> or <owner>/<repo>, got: $in"
  OWNER="${BASH_REMATCH[1]}"
  REPO="${BASH_REMATCH[2]}"
  [[ "$OWNER" != "." && "$OWNER" != ".." && "$REPO" != "." && "$REPO" != ".." ]] \
    || die "invalid owner/repo"
}

# render_policy <owner> <repo> <with_token:0|1> <out_file>
render_policy() {
  local owner="$1" repo="$2" token="$3" out="$4" binding='#@GH_BINDING@'
  [[ "$token" == "1" ]] && binding=''
  mkdir -p "$(dirname "$out")"
  sed -e "s|@OWNER@|${owner}|g" -e "s|@REPO@|${repo}|g" \
      -e "s|#@GH_BINDING@|${binding}|g" \
      "$ROOT_DIR/policies/claude-reviewer.yaml" > "$out"
}

# Read a secret from the environment or prompt silently. Never echoed, never an argv.
ensure_secret() {
  local var="$1" prompt="$2"
  if [[ -z "${!var:-}" ]]; then
    [[ -t 0 ]] || die "$var is not set and stdin is not a terminal"
    read -rsp "$prompt: " "${var?}"
    echo
    export "${var?}"
  fi
  [[ -n "${!var}" ]] || die "$var is empty"
}
