FROM python:3.13-slim

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

# Run the application using uv
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
