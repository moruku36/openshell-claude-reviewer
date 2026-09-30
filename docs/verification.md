# Verification

CI (no secrets required) checks: shellcheck, YAML lint, policy schema sanity for both rendered variants,
hostile `owner/repo` rejection, secret scan, Markdown links, image build + sanity. CI cannot run OpenShell
(it needs a gateway and Docker-in-VM), so **live verification is local**:

```sh
scripts/verify-security.sh moruku36/multi-ai-workflow
```

## What is tested

| Test | Expected |
|---|---|
| Claude Code starts | allowed |
| Anthropic connectivity (`claude -p`) | allowed |
| `git clone` / `git fetch` of the target | allowed |
| API `GET /repos/<target>` | allowed (200) |
| `git push --dry-run` | denied |
| API `POST /repos/<target>/issues` (empty body) | denied (`policy_denied`) |
| API `GET` of a different repo | denied |
| `curl https://example.com`, `registry.npmjs.org` | denied |
| `~/.ssh`, `~/.aws`, `/Users`, `/host_mnt`, `/Volumes` | absent |
| Write to `/usr` | denied |
| `ANTHROPIC_API_KEY` in sandbox env | opaque placeholder (never a raw `sk-ant-` value) |
| `openshell logs` | contains `DENIED` events |

Safety of the test itself: pushes are `--dry-run`; the API mutation carries an empty JSON body and is denied
by the proxy (and would be rejected by GitHub if it were not); no secret value is read or printed.

## Inspect manually

```sh
scripts/status.sh <sandbox>                       # effective policy + recent denials
openshell logs <sandbox> --since 10m --source sandbox | grep DENIED
openshell policy get <sandbox> --full
```

Example deny lines (format from OpenShell's docs):

```
NET:OPEN [MED] DENIED /usr/bin/curl -> example.com:443 [policy:- engine:opa]
HTTP:POST [MED] DENIED POST http://api.github.com:443/repos/<o>/<r>/issues [policy:github_api_read engine:l7]
```

## Recorded results

Run 2026-09-30 on a MacBook Air (Apple Silicon, macOS), Docker Desktop with host networking enabled,
target `moruku36/multi-ai-workflow`, `scripts/verify-security.sh --skip-claude`. Failures: 0.

| Test | Expected | Result |
|---|---|---|
| Claude Code starts | ALLOWED | PASS |
| GitHub clone | ALLOWED | PASS |
| GitHub fetch | ALLOWED | PASS |
| GitHub API GET (target repo) | ALLOWED | PASS |
| GitHub push --dry-run | DENIED | PASS |
| GitHub API mutation (POST issues) | DENIED | PASS |
| GitHub API GET (other repo) | DENIED | PASS |
| Unapproved host (example.com) | DENIED | PASS |
| Unapproved host (registry.npmjs.org) | DENIED | PASS |
| Host paths (~/.ssh ~/.aws /Users) | DENIED | PASS |
| Write to /usr | DENIED | PASS |
| Credential in env is opaque placeholder | placeholder | PASS |
| Deny events in OpenShell log (>=3) | logged | PASS |

**Not covered by this run** (run `scripts/verify-security.sh` without `--skip-claude` and
`scripts/review.sh` with a real Anthropic Console key to complete them):

- Anthropic connectivity from inside the sandbox (`claude -p`), i.e. the `api.anthropic.com` rule and the
  Claude Code binary paths in `profiles/claude-code-reviewer.yaml`.
- An end-to-end review (`review.sh`), including the optional `--token` path for private repositories.
- This run used a placeholder value instead of a real API key, so the "opaque placeholder" check shows the
  mechanism, not a real credential being hidden.

Findings from the first live runs (all fixed): sandbox names are limited to 19 characters;
Docker Desktop needs host networking; `cleanup.sh` must not use `mapfile` (bash 3.2 on macOS).
