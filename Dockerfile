# ---- Build stage: build wheel with Poetry ----
FROM python:3.14-slim AS builder

ENV POETRY_VERSION=1.8.3 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app

# Copy dependency metadata first (better caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies needed to build (but not the project itself)
RUN poetry install --only main --no-root

# Copy full project and build wheel
COPY . .
RUN rm -rf dist && poetry build && ls -lh dist

# ---- Runtime stage: slim image with only app + deps ----
FROM python:3.12-slim AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GUNICORN_CMD_ARGS="--workers=4 --threads=2 --bind=0.0.0.0:8000 --timeout=60 --access-logfile=- --error-logfile=-"

# Install only runtime OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Create directories and set permissions BEFORE switching user
RUN mkdir -p /app /data/upload /data/tmp && \
    chown -R app:app /app /data

WORKDIR /app

# Copy and install app wheel (only newest wheel is installed)
COPY --from=builder /app/dist /tmp/dist
RUN pip install --no-cache-dir gunicorn /tmp/dist/*.whl && rm -rf /tmp/dist

# Copy application files (if you need static files/configs)
COPY . .
RUN chown -R app:app /app


# Set environment variables
ENV APP_MODULE="oldap_api.wsgi:app"
ENV OLDAP_REDIS_URL="redis://redis:6379"

# Switch to non-root user
USER app
EXPOSE 8000

# HEALTHCHECK: prüft alle 30 Sekunden, Timeout nach 10s
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/status || exit 1

# Start API only (Redis runs in a separate container)
CMD ["gunicorn", "oldap_api.wsgi:app"]