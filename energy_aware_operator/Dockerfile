FROM python:3.11-slim

WORKDIR /app

# Install uv as the Python package/dependency manager
RUN pip install --no-cache-dir --upgrade pip uv

# Copy project metadata and source so uv can resolve and install dependencies
COPY pyproject.toml .
COPY .python-version .
COPY operator.py .
COPY __init__.py .
COPY app ./app
COPY crd ./crd

# Create a virtual environment and install project dependencies with uv
RUN uv sync --no-dev

# Ensure uv-created virtualenv is on PATH
ENV PATH="/app/.venv/bin:${PATH}"

# Run the Kopf operator for EnergyAwareOrchestration
CMD ["kopf", "run", "-A", "operator.py"]