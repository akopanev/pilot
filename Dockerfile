FROM node:22-bookworm

# System tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ripgrep bash curl ca-certificates jq python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*

# AI tools
RUN npm install -g @anthropic-ai/claude-code @openai/codex

# Non-root user with configurable UID
ARG USER_UID=1000
RUN useradd -m -u ${USER_UID} -s /bin/bash pilot
USER pilot

# Docker environment marker (codex uses danger-full-access sandbox)
ENV PILOT_DOCKER=1

# Git safe.directory — workspace is host-mounted, ownership won't match container user.
# ENV is baked into the image; no .gitconfig write needed.
ENV GIT_CONFIG_COUNT=1
ENV GIT_CONFIG_KEY_0=safe.directory
ENV GIT_CONFIG_VALUE_0=/workspace

# Init script + loop script
COPY --chmod=755 scripts/init-docker.sh /usr/local/bin/init-docker.sh
COPY --chmod=755 pilot.sh /usr/local/bin/pilot

WORKDIR /workspace
ENTRYPOINT ["init-docker.sh"]
