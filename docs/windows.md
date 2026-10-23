# Windows workflow and remaining operational steps

The Python entry point runs natively on Windows with Python 3.11+ and no pip
dependencies. Config validation, dry-run, synthetic reports and guarded supplied-text
execution are implemented. Provider execution is mock-tested only: no real AI
inference or OpenShell isolation test was run.

## Safe commands without accounts or services

From the repository root in PowerShell:

```powershell
python -m unittest discover -s tests -v
python scripts/check-docs.py
python -m reviewer --config configs/codex.json --dry-run
python -m reviewer --config configs/claude.json --dry-run
python -m reviewer --config configs/custom.json --dry-run
python -m reviewer --config configs/synthetic.json --execute
```

Dry-run is the default and reads only its config, even if `--input` is specified.
It starts no processes, reads no credentials and writes no files. Custom argv are
omitted from printed plans. Synthetic execution reads no user input and uses a fixed
fixture; `--out synthetic-review.md` creates a new file without overwriting.

## Before the first real native review

1. Choose an already installed, trusted native Codex/Claude `.exe`, with existing
   working authentication. Batch/PowerShell shims are refused. If installation or
   new login is required, that is a separate operation: this program does neither.
   `executable` can select the actual `.exe` path.
2. Decide whether an ordinary host process is acceptable. It is **not** OpenShell
   isolation: global settings/hooks and normal host access may apply. If enforced
   confinement is required, use the existing Linux/OpenShell path.
3. Verify an externally enforced provider/account spending limit. Copy
   `configs/live-codex.example.json` to a local config and set `budget_usd` to that
   verified allowance. Example `0.25` is illustrative, not an installed cap or
   authorization. No hard Codex cost flag is invented. Claude's additional
   `--max-budget-usd` estimates spend and can overshoot, so an external cap is still
   required. If no verifiable cap exists, keep using synthetic/dry-run.
4. Prepare one UTF-8 text file containing only material approved for that provider.
   Start with a small public or synthetic sample. The program does not discover or
   export an entire repository. Nonpublic material needs separate explicit permission.
5. After those checks and permission for the actual call, the operator may run:

```powershell
python -m reviewer --config my-live-config.json --execute --input approved-review.txt --out new-review.md --allow-data-transfer --allow-native-execution --confirm-external-budget
```

This command **starts a provider and may spend money**. It was not run for this
change. Flags attest to checks the operator has completed; they do not configure
billing, authenticate or make native execution isolated. Real execution requires a
new `--out` path. Failures never trigger login, retry, installation or fallback.
After timeout/uncertainty, check provider state before repeating a call.
The ordinary Codex/Claude configs omit a budget, so `--execute` alone stays blocked.

## Existing OpenShell environment

The official [support matrix](https://docs.nvidia.com/openshell/about/support-matrix)
lists Windows x86_64 through WSL 2 + Docker Desktop as experimental. The
[native Windows roadmap](https://github.com/NVIDIA/OpenShell/issues/4450) was open
when checked on 2026-10-23. Build CI/MXC proposals do not establish native runtime
support. This project does not install, launch or configure Docker/WSL, virtualization,
networking, gateways or services. Legacy `setup.sh --install` is not a Windows fix.

Use an already working Linux/WSL session with the current OpenShell CLI, a ready
caller-owned sandbox containing the chosen AI, matching endpoint/binary policy,
existing credentials and a verified external budget. The legacy Claude-only tuple
cannot serve Codex unchanged. Prepare those independently under separate operational
permission if absent.

From that **existing Linux session**, after approving input and verifying the
complete tuple, adapt `configs/openshell-codex.example.json` and use:

```sh
python3 -m reviewer --config my-sandbox-config.json --execute --input approved-review.txt --out new-review.md --allow-data-transfer --confirm-external-budget --confirm-sandbox-verified
```

This executes in the selected running sandbox and leaves it intact. It does not
create/start/reconfigure/delete resources. Native Windows OpenShell execution is
refused; no implicit WSL launch or host fallback occurs. Active gateway, policies,
startup environment and credentials are operator-verified prerequisites, not
established by a flag. No real sandbox acceptance has been performed here.

## Configuration and exit codes

| Key | Meaning |
|---|---|
| `version`, `provider` | Required `1` and `codex` / `claude` / `custom` / `synthetic` |
| `runtime` | `native` default, or `openshell` |
| `model` | Optional actual Codex/Claude CLI ID; no guessed default |
| `executable` | Optional Codex/Claude executable path/name |
| `command` | Literal argv array for custom only; no substitutions |
| `timeout_seconds` | Integer 1-600; defaults to 120 |
| `budget_usd` | Positive external allowance up to 100; required for real execution |
| `sandbox` | Existing sandbox name for OpenShell |

Unknown/duplicate fields, invalid types and configs over 32 KiB fail validation.
No credential fields are accepted. UTF-8 BOM and Japanese/space-containing paths
work. The app label `GPT-6.1 Sol medium` is not assumed to be an API model ID; select
an actual CLI-supported ID separately.

| Exit | Meaning |
|---|---|
| 0 | Plan, fixed fixture, or successful provider report |
| 2 | CLI/config error |
| 3 | Permission/prerequisite blocked |
| 4 | New output file cannot be created or already exists |
| 5 | Input/provider failure; timeout or remote state may be uncertain |
| 130 | Interrupted; check any in-flight operation before retrying |

Source/mock checks do not verify authentication, costs or enforced isolation.
See [design](provider-design.md) and [verification](windows-verification.md).
