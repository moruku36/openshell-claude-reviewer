#!/usr/bin/env bash
# Delete reviewer sandboxes. With --all also delete providers, profiles and the local image.
set -uo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need openshell "Run scripts/setup.sh --install"
ALL=0; [[ "${1:-}" == "--all" ]] && ALL=1

# bash 3.2 (macOS default) has no mapfile; build the list with a read loop.
NAMES=()
while IFS= read -r n; do [[ -n "$n" ]] && NAMES+=("$n"); done \
  < <(openshell sandbox list --selector "$SANDBOX_LABEL" | awk 'NR>1 && NF {print $1}')
if [[ ${#NAMES[@]} -gt 0 ]]; then
  info "Deleting sandboxes: ${NAMES[*]}"
  openshell sandbox delete "${NAMES[@]}"
else
  info "No reviewer sandboxes found"
fi
rm -rf "$ROOT_DIR/.rendered"
if [[ "$ALL" == "1" ]]; then
  info "Deleting providers, profiles and image"
  openshell provider delete "$PROVIDER_CLAUDE" "$PROVIDER_GITHUB" 2>/dev/null || true
  openshell profile delete claude-code-reviewer 2>/dev/null || true
  openshell profile delete github-reviewer 2>/dev/null || true
  docker rmi "$IMAGE" 2>/dev/null || true
fi
