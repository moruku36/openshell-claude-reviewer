#!/usr/bin/env bash
# One-time setup: check prerequisites, build the reviewer image, import provider
# profiles, create providers. Usage: scripts/setup.sh [--install] [--with-github-token]
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INSTALL=0 WITH_GH=0
for a in "$@"; do
  case "$a" in
    --install) INSTALL=1 ;;
    --with-github-token) WITH_GH=1 ;;
    -h|--help) sed -n '2,3p' "$0"; exit 0 ;;
    *) die "unknown option: $a" ;;
  esac
done

info "Host: $(uname -s) $(uname -m)"
if [[ "$(uname -s)-$(uname -m)" != "Darwin-arm64" ]]; then
  echo "warning: verified target is macOS on Apple Silicon; continuing anyway" >&2
fi

need docker "Install and start Docker Desktop."
docker info >/dev/null 2>&1 || die "Docker daemon is not running. Start Docker Desktop."

if ! command -v openshell >/dev/null 2>&1; then
  if [[ "$INSTALL" == "1" ]]; then
    need brew "OpenShell's macOS installer requires Homebrew (https://brew.sh)."
    info "Installing OpenShell with the official NVIDIA installer"
    curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
  else
    die "openshell not found. Re-run with --install (runs NVIDIA's official installer), or see README."
  fi
fi
openshell --version
openshell status || die "Cannot reach the OpenShell gateway. On macOS: brew services restart openshell"

info "Building reviewer image: $IMAGE"
docker build -t "$IMAGE" -f "$ROOT_DIR/image/Dockerfile" "$ROOT_DIR"

import_profile() {
  local f="$1"
  openshell profile lint -f "$f"
  openshell profile import -f "$f" --global 2>/dev/null \
    || openshell profile update "$(basename "$f" .yaml)" -f "$f"
}
info "Importing provider profiles"
import_profile "$ROOT_DIR/profiles/claude-code-reviewer.yaml"
[[ "$WITH_GH" == "1" ]] && import_profile "$ROOT_DIR/profiles/github-reviewer.yaml"

upsert_provider() { # name type env_var
  if openshell provider get "$1" >/dev/null 2>&1; then
    openshell provider update "$1" --from-existing
  else
    openshell provider create --name "$1" --type "$2" --from-existing
  fi
}

info "Creating providers (credentials are read from this shell's environment only)"
ensure_secret ANTHROPIC_API_KEY "Anthropic Console API key (input hidden)"
upsert_provider "$PROVIDER_CLAUDE" claude-code-reviewer
unset ANTHROPIC_API_KEY
if [[ "$WITH_GH" == "1" ]]; then
  ensure_secret GITHUB_TOKEN "GitHub fine-grained read-only token (input hidden)"
  upsert_provider "$PROVIDER_GITHUB" github-reviewer
  unset GITHUB_TOKEN
fi
info "Setup complete. Next: scripts/verify-security.sh && scripts/review.sh <repo>"
