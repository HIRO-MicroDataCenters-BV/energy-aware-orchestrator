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
COPY alembic.ini .
COPY ./migrations/ ./migrations
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Apply pending Alembic migrations, then start the app.
CMD ["./entrypoint.sh"]
