FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git nodejs npm ripgrep fzf bash openssh-client curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install CLI tools unconditionally
RUN npm install -g @anthropic-ai/claude-code @openai/codex \
    && command -v claude >/dev/null \
    && command -v codex >/dev/null

# Install Pilot
COPY . /opt/pilot
RUN pip install --no-cache-dir /opt/pilot && rm -rf /opt/pilot

# Non-root user with configurable UID
ARG USER_UID=1000
RUN useradd -m -u ${USER_UID} -s /bin/bash pilot
USER pilot

# Docker environment marker
ENV PILOT_DOCKER=1

# Git safe.directory — workspace is host-mounted, ownership won't match container user.
# ENV is baked into the image; no .gitconfig write needed.
ENV GIT_CONFIG_COUNT=1
ENV GIT_CONFIG_KEY_0=safe.directory
ENV GIT_CONFIG_VALUE_0=/workspace

# Init script (runs before CMD via entrypoint)
COPY scripts/init-docker.sh /usr/local/bin/init-docker.sh
USER root
RUN chmod +x /usr/local/bin/init-docker.sh
USER pilot

WORKDIR /workspace
ENTRYPOINT ["init-docker.sh"]
CMD ["pilot", "run"]
