# check=skip=InvalidDefaultArgInFrom
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG PYTHON_VERSION="3.10 3.11 3.12"

# uv ships in the base image; use it to install the requested interpreters.
RUN uv python install ${PYTHON_VERSION}

# Both uv- and poetry-based projects are supported, so install both package
# managers alongside the shared dev tooling.
RUN uv tool install poetry \
 && uv tool install tox \
 && uv tool install pytest \
 && uv tool install mypy \
 && uv tool install black \
 && uv tool install isort \
 && uv tool install flake8

USER root
RUN npm install -g pyright && rm -rf /var/lib/apt/lists/*
USER ${USERNAME}

# Pre-create volume mount points so named-volume init inherits user ownership
# instead of being created as root by the Docker daemon.
RUN mkdir -p /work/.venv /work/.tox

# Keep poetry's venv inside the project dir so the .venv volume-shadow works.
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="/work/.venv/bin:${PATH}"
