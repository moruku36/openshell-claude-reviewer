# Troubleshooting

| Symptom | Fix |
|---|---|
| `Cannot reach the OpenShell gateway` | Start Docker Desktop, then `brew services restart openshell`; check `openshell status` |
| `Docker daemon is not running` | Start Docker Desktop; OpenShell's Docker driver needs Engine 28+ |
| Sandbox stuck in `Provisioning` | `openshell sandbox get <name>`; a `ConfigurationInvalid` condition means the policy or provider is rejected — fix and it recovers within 300 s |
| `--from openshell-claude-reviewer:local` not found | The gateway must see local images. Otherwise push the image to a registry you control and set `REVIEWER_IMAGE=<registry>/<image>:<tag>` |
| Claude cannot reach Anthropic (`403 from proxy`) | `openshell logs <name> --source sandbox \| grep DENIED` shows the binary path that was denied; add that **real** path (not a symlink) to `binaries` in `profiles/claude-code-reviewer.yaml`, then `scripts/setup.sh` |
| `git clone` denied | Owner/repo casing must match GitHub's exactly; private repos need `--token` and a token with `Contents: read` |
| Private clone returns 401/404 | Token missing or not scoped to that repo; re-run `scripts/setup.sh --with-github-token` |
| `openshell profile ...` / `provider ...` command not found | OpenShell's CLI is evolving; check `openshell --help`, and update the command in `scripts/setup.sh` |
| Landlock startup failure | `landlock.compatibility: hard_requirement` fails closed by design; needs a kernel with Landlock ABI v3 (Docker Desktop's VM normally has it) |
| Need a package registry for a review | Add a narrowly scoped rule to a copy of the policy (exact host, `access: read-only`, specific binary). Do not use wildcards |

Re-run anything safely: `scripts/cleanup.sh` removes reviewer sandboxes; `scripts/cleanup.sh --all` resets everything.
