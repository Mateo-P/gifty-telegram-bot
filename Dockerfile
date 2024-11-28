FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS base

HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

# Python outputs everything to stdout instead of buffering it
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Create source directory
ENV SOURCE="/app/src"

# Poetry will respect this when installing if it exists
ENV VIRTUAL_ENV="/app/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create working directory
WORKDIR $SOURCE

# Install python
RUN dnf install -y python3.11

# ---------------------------------------------------------------------------- #
FROM base AS build

# Poetry environment variables
ENV POETRY_HOME="/etc/poetry" \
	POETRY_NO_INTERACTION=1 \
	POETRY_VERSION=1.8.3 \
	POETRY_CORE_VERSION=1.9.0 \
	POETRY_VIRTUALENVS_CREATE=false

# Append to the end so we get the poetry bin without overriding python
ENV PATH="$PATH:$POETRY_HOME/bin"

# Install Poetry to its own virtual environment to isolate from system env
RUN python3.11 -m venv $POETRY_HOME
RUN $POETRY_HOME/bin/pip install \
	"poetry==$POETRY_VERSION" \
	"poetry-core==$POETRY_CORE_VERSION"

# Create copy-able virtual environment
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PYTHONPATH="$VIRTUAL_ENV"

# Copy package info and install dependencies so they get their own cache layer
COPY pyproject.toml poetry.lock $SOURCE/
RUN poetry install --no-root --no-dev

# Copy source and install
COPY . $SOURCE/
RUN poetry install --no-dev

# ---------------------------------------------------------------------------- #
FROM build AS dev

RUN poetry install

#COPY tests/ tests/
