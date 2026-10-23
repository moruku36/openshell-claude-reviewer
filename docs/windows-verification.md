# Windows verification record

The initial baseline was default branch `feat/initial-openshell-claude-reviewer`,
commit `78d908f349a6fc58e2fcf916fa0f8b0143e6e405`. Both READMEs, architecture,
security model, scripts, policy, profiles and image were inspected. No AGENTS.md
existed at that baseline. Draft PR #3 initially added offline planning only.

The owner then explicitly approved source restoration/modification and synthetic
tests, without approving real authentication, service changes or external AI calls.
The denied source restoration was retried once on that new evidence and succeeded.
Profiles, prompts and scripts were restored as source only; setup/review/security
scripts were not executed. Legacy image/profile/policy contents remain unchanged
in the PR. The docs checker now reads UTF-8 explicitly, fixing a reproduced CP932
failure on Windows.

## Follow-up tests

Guarded supplied-text execution is implemented for native providers and an existing
OpenShell sandbox. All provider startup in tests is mocked. The only actual test
child remains the built-in fixed synthetic Python fixture.

Windows/Python 3.11 tests cover strict config, large integers/budgets, missing
permissions before input reads/process creation, executable lookup/Windows batch
refusal, literal argv/stdin delivery, temporary cwd cleanup, both pipes and combined
output limits, launch failure/nonzero exits, invalid/empty output, timeout/direct-child
cleanup without retry, existing OpenShell command shape, native Windows refusal
for that transport, no provisioning, mock CLI-to-report success, no report on provider
failure, existing-output protection, UTF-8 BOM and Japanese paths.

Installed `codex exec --help` confirmed Codex flags; official Claude and OpenShell
sandbox-exec docs were checked. CI runs synthetic tests and UTF-8 docs checks on
Windows/Ubuntu with Python 3.11/3.13, alongside existing Linux lint/image CI. Final
counts/results are recorded in the PR and are not evidence of live AI behavior.

## Operations not performed

No model/API request, paid inference, new login, credential saving, Docker/WSL or
virtualization setup, network/security change, service start/reconfiguration,
private-repository transmission or live sandbox acceptance was performed.

An earlier ordinary clone failed DNS resolution. No alternate DNS/proxy, TLS
bypass or network change was attempted. Existing GitHub connector access supplies
source and commit/PR operations. The local source snapshot is not a Git checkout.

Remaining acceptance: choose an existing trusted/authenticated CLI, verify an actual
external spend limit, approve one input and the native host-execution boundary, or
independently prepare/verify a matching existing OpenShell sandbox. Minimal operator
steps are in [Windows instructions](windows.md). Budget/sandbox flags are operator
attestations, not automatic verification. Killing a CLI cannot prove descendants or
remote paid requests stopped; check uncertain state before manual retry. No automatic
retry or isolation downgrade exists.
