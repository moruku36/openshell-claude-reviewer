# Reviewer sandbox image: Claude Code + git on a minimal Debian base.
# The OpenShell supervisor replaces CMD at runtime; pass the command after `--`.
FROM node:22-bookworm-slim

ARG CLAUDE_CODE_VERSION=latest

# iproute2 / nftables: needed by the sandbox network namespace setup.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates curl iproute2 nftables \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force

# Non-root identity; must match process.run_as_user/group in the policy.
RUN groupadd --gid 1500 reviewer \
    && useradd --uid 1500 --gid reviewer --create-home --home-dir /home/reviewer reviewer \
    && install -d -o reviewer -g reviewer /sandbox

COPY prompts/reviewer.md /opt/reviewer/reviewer.md

ENV DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

WORKDIR /sandbox
USER reviewer
CMD ["claude", "--version"]
