ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG PYTHON_VERSION=3.12

# Use uv to manage the Python interpreter even for the poetry variant —
# it's the cleanest cross-version story and poetry will happily use it.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && uv python install ${PYTHON_VERSION}

RUN uv tool install poetry \
 && uv tool install pytest \
 && uv tool install mypy \
 && uv tool install black \
 && uv tool install isort \
 && uv tool install flake8

RUN sudo npm install -g pyright && sudo rm -rf /var/lib/apt/lists/*

# Keep poetry's venv inside the project dir so the .venv volume-shadow works.
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="/work/.venv/bin:${PATH}"
