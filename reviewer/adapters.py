"""Pure provider adapters: build argv, never start a provider."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Invocation:
    argv: tuple[str, ...]
    stdin: str


def build_invocation(provider, model=None, command=None):
    """Return an argv vector and stdin contract for an operator-reviewed plan.

    argv is data, not a shell command. The custom contract accepts the complete
    prompt on stdin and returns the final review on stdout; no interpolation.
    """
    if provider == "codex":
        argv = ["codex", "exec", "--sandbox", "read-only", "--ephemeral",
                "--skip-git-repo-check"]
        if model:
            argv += ["--model", model]
        return Invocation(tuple(argv + ["-"]), "review prompt and input text")
    if provider == "claude":
        # allowedTools only removes approval prompts. tools restricts availability.
        argv = ["claude", "-p", "--tools", "", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--disallowedTools", "mcp__*"]
        if model:
            argv += ["--model", model]
        return Invocation(tuple(argv), "review prompt and input text")
    if provider == "custom":
        return Invocation(tuple(command), "review prompt and input text")
    if provider == "synthetic":
        return Invocation((), "built-in fixed synthetic fixture; no input file")
    raise ValueError("unsupported provider")
