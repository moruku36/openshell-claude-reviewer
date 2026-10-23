"""Pure provider adapters: build argv, never start a provider."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Invocation:
    argv: tuple[str, ...]
    stdin: str


def build_invocation(provider, model=None, command=None, executable=None, budget_usd=None):
    """Return an argv vector and stdin contract for an operator-reviewed plan.

    argv is data, not a shell command. The custom contract accepts the complete
    prompt on stdin and returns the final review on stdout; no interpolation.
    """
    if provider == "codex":
        argv = [executable or "codex", "exec", "--sandbox", "read-only", "--ephemeral",
                "--skip-git-repo-check"]
        if model:
            argv += ["--model", model]
        return Invocation(tuple(argv + ["-"]), "review prompt and input text")
    if provider == "claude":
        # allowedTools only removes approval prompts. tools restricts availability.
        argv = [executable or "claude", "-p", "--tools", "", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--disallowedTools", "mcp__*",
                "--no-session-persistence", "--output-format", "text"]
        if budget_usd is not None:
            argv += ["--max-budget-usd", str(budget_usd)]
        if model:
            argv += ["--model", model]
        return Invocation(tuple(argv), "review prompt and input text")
    if provider == "custom":
        return Invocation(tuple(command), "review prompt and input text")
    if provider == "synthetic":
        return Invocation((), "built-in fixed synthetic fixture; no input file")
    raise ValueError("unsupported provider")
