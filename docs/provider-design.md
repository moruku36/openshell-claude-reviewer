# Provider adapter and execution design

The Python layer selects Codex, Claude or another CLI without changing the legacy
macOS image, policy or provider profiles. Default behavior stays offline.

```text
JSON -> validator -> pure adapter -> argv + stdin contract -> dry-run JSON
                                -> fixed synthetic executor
                                -> authorization -> approved text file
                                   -> native process OR existing OpenShell sandbox
                                   -> bounded UTF-8 output -> new report
```

`config.py` validates bounded UTF-8 JSON and per-provider fields. `adapters.py`
constructs literal argv without launching processes or expanding templates.
`execution.py` owns permissions, input limits, executable lookup, transports,
bounded pipe draining and terminal failure behavior. `__main__.py` owns CLI
selection, dry-run and report publication.

## Adapter contracts

| Adapter | Behavior | Evidence |
|---|---|---|
| Codex | `exec --sandbox read-only --ephemeral --skip-git-repo-check`, stdin `-`, optional model/executable | Installed `codex exec --help` and official reference |
| Claude | Print/text mode, built-in tools disabled, strict empty MCP config, MCP tools disallowed, session persistence disabled | Official CLI reference; source/mock checks only |
| Custom | Literal argv, prompt on stdin, UTF-8 report on stdout | Mock contract tests; CLI-specific behavior is operator-owned |
| Synthetic | Fixed input/report without a process | Local/CI fixture tests |

Claude additionally receives `--max-budget-usd` when configured. This estimated-spend
limit can overshoot. There is no invented equivalent Codex flag. Every live provider
therefore requires confirmation of an externally enforced budget. `budget_usd`
records that allowance, not proof it is configured.

Sources checked on 2026-10-23: [Codex CLI](https://developers.openai.com/codex/cli/reference),
[Claude CLI](https://code.claude.com/docs/en/cli-reference),
[OpenShell exec](https://docs.nvidia.com/openshell/how-it-works/sandboxes/overview).
The old Claude `--allowedTools` controls approval prompts rather than complete tool
availability. CLI tool controls and prompts do not establish an OpenShell-equivalent
host security boundary.

## Authorization and transports

Real execution needs an explicitly selected UTF-8 input, a new output path,
`--allow-data-transfer`, `budget_usd`, and `--confirm-external-budget`. Native
execution also requires `--allow-native-execution`. These are operator attestations;
they do not query billing or grant real-call permission during tests.

Native transport uses `shell=False` in an empty temporary working directory.
No repository is cloned, mounted or scanned. Windows requires a resolved `.exe`;
batch/PowerShell shims are refused. The provider still inherits its normal host
environment, existing authentication, global settings and hooks. It may have broad
host access: native mode is unsuitable when enforced isolation is required.

OpenShell transport runs from a non-Windows CLI environment against an existing,
operator-verified sandbox selected by `sandbox`. It additionally requires
`--confirm-sandbox-verified`. It constructs `sandbox exec -n NAME --no-tty
--no-login-shell --timeout SECONDS -- ARGV...`, sends stdin and propagates failure.
It never creates/starts/deletes sandboxes, imports profiles, saves credentials,
selects gateways, uploads files or alters policies. No native fallback exists.
`--no-login-shell` does not neutralize existing `BASH_ENV`; verify that environment
with the image, provider, binaries and policy. Caller-owned sandbox state persists;
this transport does not claim per-review ephemerality.

## Failure behavior

Authorization precedes input reads or process creation. Input is limited to 256 KiB;
combined stdout/stderr to 1 MiB. Timeouts are 1-600 seconds, with a 10-second client
grace period for the OpenShell server-side timeout. Both pipes are drained;
diagnostics are discarded because they may contain secrets. Success requires zero
exit status and nonempty valid UTF-8 output. Reports are created exclusively after
success, with no overwrite of existing files/symlinks. A disk failure can leave an
incomplete new file and returns failure.

Timeout, interruption, oversized output or incomplete streams cause terminal failure
and direct-child cleanup. No retries occur. Killing a local CLI does not prove
descendants, remote commands or in-flight paid requests stopped. Such outcomes are
explicitly uncertain; verify state before any manual retry.

All provider launches in tests are mocks. Only the fixed Python synthetic fixture
is launched as a real child. No AI account, credentials, API, Docker, WSL or gateway
is used. The legacy tuple is preserved. A real Codex OpenShell sandbox needs a
separately prepared matching image, endpoint/binary policy and credential provider;
the Anthropic-only legacy image is not silently reused. Authentication, costs,
native provider behavior and actual sandbox isolation remain acceptance work.
