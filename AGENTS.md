# Repository guidance

- Read both READMEs and docs/architecture.md before modifying the reviewer.
- `python -m reviewer` is an offline planner and fixed synthetic runner. Keep the
  default offline and preserve fail-closed behavior for every real provider.
- Do not present CLI tool controls as an OpenShell filesystem/network boundary.
- Verify provider and OpenShell flags against installed help or official docs;
  do not infer native Windows support from build-only CI or roadmap issues.
- Run `python -m unittest discover -s tests -v` for changes to the Python entry point.
  Tests must be synthetic and must not require AI accounts, credentials or Docker.
- Never add credentials to config examples. Do not run legacy setup/security
  scripts without authorization covering credentials, services and remote calls.
- Preserve the legacy macOS image/policy/profile contract unless the full
  provider-image-policy tuple has been explicitly designed and verified.
