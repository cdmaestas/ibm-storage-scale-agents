# syntax=docker/dockerfile:1
# Build with optional provider extras, e.g.:
#   docker build --build-arg EXTRAS="--extra openai" -t scale-agents .
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Optional provider extras (space-separated uv flags), e.g. "--extra openai".
# Base image ships the Ollama provider only.
ARG EXTRAS=""

# Install dependencies first (cached layer) using only the lock + manifest.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project ${EXTRAS}

# Then copy the source and install the project itself.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen ${EXTRAS}

ENV PATH="/app/.venv/bin:$PATH"

# main.py is an interactive CLI (reads stdin); run with `docker run -it` or the
# provided docker-compose service which sets stdin_open/tty.
ENTRYPOINT ["python", "main.py"]
