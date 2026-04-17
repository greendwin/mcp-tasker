FROM ubuntu:26.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and developer tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    zsh \
    neovim \
    tmux \
    sudo \
    ncurses-term \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Build args for matching host UID/GID/username
ARG UID=1000
ARG GID=1000
ARG USERNAME=agent

# Remove pre-existing ubuntu user/group (ships at UID/GID 1000 in Ubuntu 26.04)
# then create user with the host's UID/GID/username so volume ownership matches
RUN userdel -r ubuntu && groupdel ubuntu || true \
    && groupadd -g ${GID} ${USERNAME} \
    && useradd -m -u ${UID} -g ${GID} -s /bin/zsh ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME}

# Install Node.js (LTS) via NodeSource and Pyright globally
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g pyright \
    && rm -rf /var/lib/apt/lists/*

USER ${USERNAME}

# Bake ~/.local/bin and the project venv into the image PATH so they are visible
# even when the container is entered via `docker exec` (which does not source .zshrc).
ENV PATH="/home/${USERNAME}/.local/bin:/work/.venv/bin:${PATH}"

# Install Claude Code
# RUN curl -fsSL https://claude.ai/install.sh | bash
COPY sandbox/claude_install.sh /tmp/claude_install.sh
RUN cat /tmp/claude_install.sh | bash

# Set git identity for commits made inside the container.
# Uses --global so it writes to ~/.gitconfig (container-only, never the repo's .git/config).
# The host keeps its own ~/.gitconfig untouched.
RUN git config --global user.name "Claude Agent" \
    && git config --global user.email "agent@claude.ai"

# Install uv (standalone installer drops binaries into ~/.local/bin).
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && uv python install 3.12

# Install useful tools for global access
RUN uv tool install tox       \
    && uv tool install pytest \
    && uv tool install mypy   \
    && uv tool install black  \
    && uv tool install isort  \
    && uv tool install flake8 \
    && uv tool install mcp-tasker

# Install parent project dependencies into the image.
# Build context is the parent directory, so pyproject.toml is accessible.
# `uv sync` creates /work/.venv; --no-install-project skips the root package
# (sources are not copied here — they get mounted at runtime).
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml uv.lock* LICENSE* /work/
RUN cd /work && uv sync --no-install-project --all-extras --all-groups

# Create a working directory for mounted projects
WORKDIR /work

# Default command: attach to existing session or create a new one
CMD ["tmux", "new-session", "-A", "-s", "main"]
