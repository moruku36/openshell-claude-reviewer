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

| Date | Host | OpenShell | Result |
|---|---|---|---|
| _not yet run_ | | | Run the script and paste the generated table here, without secrets. |
