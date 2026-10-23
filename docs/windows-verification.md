# Windows verification record

Baseline: repository default branch `feat/initial-openshell-claude-reviewer`, commit
`78d908f349a6fc58e2fcf916fa0f8b0143e6e405`. README (English/Japanese), architecture,
security model, verification record, scripts, policy, profiles and image were read
through the existing GitHub connector. No AGENTS.md existed at that baseline.

Environment: Windows, Python 3.11, PowerShell, 2026-10-23. No AI request or API charge.

## Scope of evidence

- Synthetic tests cover config examples, malformed/oversize/duplicate JSON,
  unknown keys, provider-specific fields, argument injection shapes, BOM and Japanese
  paths, literal custom argv, no-process dry-run, blocked live execution on both
  runtime labels, exclusive output, report preservation and module-level execution.
- Installed `codex exec --help` confirmed the planned Codex flags without inference.
  It emitted access warnings for its temporary alias cleanup; no permission/config
  changes were attempted to remove those warnings.
- Official NVIDIA support matrix and Windows roadmap were checked. No native
  Windows OpenShell execution or Linux isolation claim is inferred from build CI.
- New CI runs the synthetic suite on Windows/Ubuntu with Python 3.11/3.13. The
  existing Linux lint/image workflow remains separate.

## Workstation limitations and approval boundaries

The first ordinary `git clone` failed with `Could not resolve host: github.com`.
No retry with alternate DNS, proxy, TLS disablement or network/security change was
attempted. Public source inspection and PR operations use the pre-existing GitHub
connector. The local directory is a partial source snapshot, not a Git checkout.

Automatic approval review denied local restoration of the existing
`profiles/claude-code-reviewer.yaml`, citing credential-backed transmission to
Anthropic. It also denied restoration of a batch containing the existing setup and
review scripts, citing installation/reconfiguration, credential prompts and remote
AI calls. Those denied operations were not retried or routed through another writer.
The remote legacy files remain unchanged. Only the new offline implementation and
documentation are proposed by this change.

Real provider execution and provider profile/image changes remain unimplemented.
No Docker/WSL/virtualization setup, service operation, login, credential storage,
private-repository transmission, paid inference or live policy verification took
place. Local results and CI status are reported with the PR; neither a fixed fixture
nor green CI establishes a working real AI review or an enforced Windows sandbox.
