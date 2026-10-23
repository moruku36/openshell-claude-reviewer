# Windows: reproducible offline workflow

Status: Windows-native configuration validation, provider argv planning and a fixed
synthetic review are implemented. **Real Codex/Claude/custom reviews are not
implemented by this entry point.** This is an incremental foundation, not a claim
that OpenShell now runs natively on Windows or that a real review was verified.

## Requirements and commands

Use an existing Python 3.11+ installation from PowerShell in the repository root.
No pip dependencies, Docker, WSL, gateway, credentials or provider CLI are needed.
Obtain this public repository using your already approved GitHub access; this tool
does not clone repositories, repair connectivity or disable TLS validation.

```powershell
python --version
python -m unittest discover -s tests -v
python -m reviewer --config configs/codex.json --dry-run
python -m reviewer --config configs/claude.json --dry-run
python -m reviewer --config configs/custom.json --dry-run
python -m reviewer --config configs/synthetic.json --execute
python -m reviewer --config configs/synthetic.json --execute --out synthetic-review.md
```

`--dry-run` is the default. It reads only the selected configuration file, emits a
JSON plan and does not start any process, read environment variables or write files.
`--execute` accepts only `synthetic`, which uses a fixed built-in bug and report;
it does not read a user's repository. `--out` creates a new file exclusively;
repeat the command with a different path rather than overwriting an earlier report.
UTF-8 BOM configs, spaces and Japanese characters in config/report paths work.

This command deliberately exits 3 and creates no report:

```powershell
python -m reviewer --config configs/codex.json --execute
```

No flag unlocks a real provider, starts WSL or Docker, creates credentials, changes
network/security settings, or starts/reconfigures services. The legacy `scripts/*.sh`
workflow remains macOS-oriented; do not run `setup.sh --install` as a Windows fix.
Historical macOS instructions below the new README notice do not apply to this path.

## Configuration contract

| Key | Contract |
|---|---|
| `version` | Required integer `1`; booleans rejected |
| `provider` | Required: `codex`, `claude`, `custom`, `synthetic` |
| `runtime` | `native` (default) or `openshell`; planning label, not an executor |
| `model` | Optional explicit CLI model identifier for Codex/Claude only |
| `command` | Required argv array for custom only; literal arguments, no substitution |

Unknown/duplicate keys, malformed JSON, configs over 32 KiB, invalid argument
types and option-shaped model IDs fail validation. No credential fields are
accepted. Do not paste secrets into command arguments. Custom argv are omitted
from printed plans to reduce accidental disclosure. The adapter library retains
literal argv for tests and future reviewed integrations; no shell interprets them.

Model defaults are left to the selected CLI. The app's model label `GPT-6.1 Sol medium`
is not assumed to be an API/CLI model ID. Choose an actual supported CLI identifier
only after verifying availability; no inference was performed for this change.

| Exit | Meaning |
|---|---|
| 0 | Valid plan or completed fixed synthetic fixture |
| 2 | CLI/config error |
| 3 | Live provider execution blocked |
| 4 | Output file cannot be created, including an existing file |
| 130 | Interrupted |

## Native Windows versus Linux runtime

| Capability | Native Windows in this project | Linux/WSL/container dependency |
|---|---|---|
| JSON validation, argv adapters, dry-run | Implemented, Python stdlib | None |
| Fixed synthetic report, failure handling | Implemented | None |
| Actual Codex/Claude/custom review | Not implemented in new entry point | Future executor needs separate verification |
| Legacy image and provider profiles | Linux paths and Node/Debian image | Existing Docker/OpenShell workflow |
| Landlock hard requirement, uid 1500, Linux paths | Not a Windows security boundary | Linux sandbox/kernel |
| Default-deny proxy and credential injection | No native guarantee claimed | Verified gateway, policy and matching image/profile |

Official NVIDIA [support matrix](https://docs.nvidia.com/openshell/about/support-matrix)
lists Windows x86_64 via WSL 2 + Docker Desktop as experimental. The official
[native Windows roadmap](https://github.com/NVIDIA/OpenShell/issues/4450) was open
when checked on 2026-10-23. Build workflows and MXC proposals alone do not establish
a supported native runtime. See official [installation](https://docs.nvidia.com/openshell/about/installation)
for prerequisites; this change does not install or alter them.

## Remaining work for live execution

A live executor must verify a complete provider/image/policy combination, existing
authentication, data-transfer permission and cost limits. Codex cannot use the
Anthropic-only image/profile unchanged. Custom CLI arguments do not define safe
network destinations or credential bindings. Windows-hosted CLI controls also do
not establish the same boundary as OpenShell's Linux sandbox. An executor must
never fall back to unrestricted host execution after an isolation failure.

Live execution, provider image/profile changes and gateway provisioning are outside
this incremental PR. Historical macOS checks do not validate Windows, Codex, custom
providers, or a new OpenShell version. The next phase needs explicit operational
authorization at the relevant boundary, not merely a successful synthetic run.
