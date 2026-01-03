FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock* .
COPY README.md .

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application files
COPY ./app/ ./app

# Run the operator using uv
CMD ["uv", "run", "kopf", "run", "app/operator.py", "--liveness=http://0.0.0.0:8080/healthz"]
