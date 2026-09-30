# Security model

## Assets and trust

| Trusted | Untrusted |
|---|---|
| Host, gateway, policy files, provider store | Reviewed repository content, the model's output, anything inside the sandbox |

The reviewed code is treated as hostile: it may contain prompt injection. The sandbox must be safe even
if the model fully obeys such instructions.

## Controls

| Layer | Control | Where |
|---|---|---|
| Filesystem | Only `/tmp`, `/sandbox`, `/home/reviewer` writable; `/usr /lib /etc /opt/reviewer` read-only; Landlock `hard_requirement`; nothing from the host mounted | `policies/claude-reviewer.yaml` |
| Identity | Non-root uid/gid 1500 | policy `process`, `image/Dockerfile` |
| Network | Default deny. Allowed: `api.anthropic.com` (provider profile), `github.com` and `api.github.com` (this repo only) | policy + profile |
| GitHub write | API: only `GET`/`HEAD` allow rules (no `POST/PUT/PATCH/DELETE`). Git: `git-receive-pack` and the receive-pack advertisement denied explicitly | policy |
| Binary scoping | Only listed executables may use each endpoint (`git`, `curl`, `claude`/`node`) | policy + profile `binaries` |
| Credentials | Env holds `openshell:resolve:env:*` placeholders; the proxy substitutes real values only at bound endpoints; delete purges them | providers |
| Tool allow-list | `claude -p --allowedTools Read,Grep,Glob,Bash(git log/diff/show/status:*)` | `scripts/review.sh` |
| Prompt | Reviewer-not-Builder instructions | `prompts/reviewer.md` (defense in depth only) |

The tool allow-list and prompt are **not** relied on for safety. The policy is.

## Credentials

- Anthropic: Console API key from your environment → `openshell provider create --from-existing`.
  Subscription (OAuth) tokens are not supported by OpenShell's provider; do not copy `~/.claude` into the sandbox.
- GitHub (optional): fine-grained token, read-only, one repository. Prefer none for public repos.
- Secrets are read from env or hidden prompt, never passed as argv, never committed
  (`.gitignore`, `scripts/scan-secrets.sh`, CI). Verification prints only a classification
  (`placeholder` / `RAW` / `unset`), never a value.

## Residual risks

- Exfiltration through allowed channels: repository contents go to Anthropic (required for review). A
  prompt-injected model could put data in an Anthropic request; that request only ever reaches Anthropic.
- Read access to the target repository (and, with a token, whatever that token can read on it).
- A `curl` allowance on `api.github.com` (GET on the target repo only) exists so verification can observe L7 denials.
- Sandbox escape or OpenShell bugs are out of scope; keep OpenShell and Docker Desktop updated.
