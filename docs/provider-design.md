# Provider adapter design

## Current implementation

The original architecture intentionally implemented Claude only. This change adds
an independent, credential-free planning layer that can select Codex, Claude or
another CLI without editing the legacy Bash scripts or widening their policy.

```text
JSON config -> strict validator -> provider adapter -> immutable argv + stdin contract
                                  -> offline JSON plan (default)
                                  -> synthetic executor -> fixed fixture report
                                  -> live executor: blocked (exit 3)
```

`reviewer/config.py` owns schema validation, duplicate-key rejection and bounded
UTF-8 reads. `reviewer/adapters.py` is pure: it accepts validated settings and returns
an argv tuple and stdin contract. No adapter reads secrets, discovers executables
or invokes a shell. `reviewer/__main__.py` owns plan serialization, explicit action
selection, error codes and exclusive report creation. The only implemented executor
is the built-in synthetic fixture. A plan does not imply executable capability.

This separation permits synthetic contract tests before authorization for any real
provider call. No SDK dependency, external model, new login, paid inference or
service is needed to run the tests.

## Adapter contracts

| Adapter | Planned command behavior | Verification |
|---|---|---|
| Codex | `exec`, read-only sandbox, ephemeral session, stdin `-`; optional model | Installed `codex exec --help` plus official reference, 2026-10-23 |
| Claude | Print mode, built-in tools disabled, strict empty MCP config and MCP tools disallowed; optional model | Official Claude CLI reference, 2026-10-23; no live invocation |
| Custom | Operator-supplied literal argv; full prompt on stdin, final report on stdout | Synthetic argv tests only; no claimed provider compatibility |
| Synthetic | No argv, no process, no input files | Fixed fixture and deterministic report |

The old Claude `--allowedTools` option controls approval prompts, not the complete
set of available tools. The new planned adapter uses `--tools ""` with MCP controls
for a future supplied-text review. These controls still do not prove host-level
network or filesystem isolation. No native provider execution is enabled here.

Sources: [Codex CLI reference](https://developers.openai.com/codex/cli/reference),
[Claude CLI reference](https://code.claude.com/docs/en/cli-reference),
[OpenShell sandbox lifecycle](https://docs.nvidia.com/openshell/how-it-works/sandboxes/overview).
OpenShell documents `--no-keep` for ephemeral commands, but its current upload/main
command restrictions mean a future input-staging executor needs its own tested
lifecycle and cleanup rather than an invented all-in-one invocation.

## Failures and trust

Invalid config exits before planning. Real execution exits before opening an output
file. Existing output paths, including symlinks, are rejected by exclusive creation.
Exception messages do not echo config content. Custom argv are never printed.
The module has no subprocess or network execution path. There is no hidden environment
switch, custom-command escape hatch or host fallback to turn a plan into a live call.

The original image, policies and profiles still describe the legacy Claude path.
They are not reusable for Codex by changing only an executable name. A future live
adapter requires explicit endpoint/binary scope, reviewed credential binding,
isolation acceptance, output/timeout handling and cleanup tests. Credential values
must remain outside plans, command-line arguments, logs and source control.
