FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git nodejs npm ripgrep bash curl ca-certificates jq \
    && rm -rf /var/lib/apt/lists/*

# Install CLI tools
RUN npm install -g @anthropic-ai/claude-code @openai/codex opencode-ai \
    && command -v claude >/dev/null \
    && command -v codex >/dev/null

# Install Pilot
COPY . /opt/pilot
RUN pip install --no-cache-dir /opt/pilot && rm -rf /opt/pilot

# Init script (credential copy from read-only mounts)
COPY scripts/init-docker.sh /usr/local/bin/init-docker.sh
RUN chmod +x /usr/local/bin/init-docker.sh

# Non-root user
ARG USER_UID=1000
RUN useradd -m -u ${USER_UID} -s /bin/bash pilot
USER pilot

# Docker marker
ENV PILOT_DOCKER=1

# Git safe.directory for host-mounted workspace
ENV GIT_CONFIG_COUNT=1
ENV GIT_CONFIG_KEY_0=safe.directory
ENV GIT_CONFIG_VALUE_0=/workspace

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/init-docker.sh"]
CMD ["pilot", "run", ".pilot/pipeline.yaml"]
