#!/usr/bin/env bash
# Show gateway, provider, profile and reviewer-sandbox state. Secrets are never printed.
set -uo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need openshell "Run scripts/setup.sh --install"
info "Gateway";   openshell status
info "Profiles";  openshell profile list
info "Providers"; openshell provider list
info "Reviewer sandboxes"; openshell sandbox list --selector "$SANDBOX_LABEL"
if [[ -n "${1:-}" ]]; then
  info "Effective policy of $1"; openshell policy get "$1" --full
  info "Recent denials of $1";   openshell logs "$1" --since 30m --source sandbox | grep DENIED || echo "(none)"
fi
