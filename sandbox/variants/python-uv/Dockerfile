ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG PYTHON_VERSION=3.12

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && uv python install ${PYTHON_VERSION}

RUN uv tool install tox \
 && uv tool install pytest \
 && uv tool install mypy \
 && uv tool install black \
 && uv tool install isort \
 && uv tool install flake8 \
 && uv tool install mcp-tasker

RUN sudo npm install -g pyright && sudo rm -rf /var/lib/apt/lists/*

ENV PATH="/work/.venv/bin:${PATH}"
