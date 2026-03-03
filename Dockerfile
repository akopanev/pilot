FROM node:22-slim

# System deps (node/npm/corepack already in base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git python3 python3-pip python3-venv \
    ripgrep bash curl ca-certificates jq gosu graphviz \
    && rm -rf /var/lib/apt/lists/*

# Enable corepack (pnpm/yarn available without separate install)
RUN corepack enable

# Install CLI tools
RUN npm install -g @anthropic-ai/claude-code @openai/codex opencode-ai \
    && command -v claude >/dev/null \
    && command -v codex >/dev/null

# Install ticket (tk) — git-backed issue tracker (full clone for plugins)
RUN git clone --depth 1 https://github.com/wedow/ticket.git /opt/ticket \
    && ln -s /opt/ticket/ticket /usr/local/bin/tk
ENV PATH="/opt/ticket/plugins:${PATH}"

# Install Pilot
COPY . /opt/pilot
RUN python3 -m venv /opt/pilot-venv \
    && /opt/pilot-venv/bin/pip install --no-cache-dir /opt/pilot \
    && rm -rf /opt/pilot
ENV PATH="/opt/pilot-venv/bin:${PATH}"

# Init script (UID mapping + credential forwarding)
COPY scripts/init-docker.sh /usr/local/bin/init-docker.sh
RUN chmod +x /usr/local/bin/init-docker.sh

# Non-root user (UID remapped at runtime via APP_UID)
RUN useradd -m -s /bin/bash pilot

# Docker marker
ENV PILOT_DOCKER=1

WORKDIR /workspace

# Entrypoint runs as root, remaps UID, drops to pilot via gosu
ENTRYPOINT ["/usr/local/bin/init-docker.sh"]
CMD ["pilot", "run", ".pilot/pipeline.yaml"]
