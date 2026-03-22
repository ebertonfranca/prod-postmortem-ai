FROM python:3.12-slim

# Variables to optimize Python execution
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Ensure uv uses the virtual environment
    PATH="/app/.venv/bin:$PATH"

# Install uv by copying the compiled binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy requirement files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Sync dependencies using uv. We omit the project itself first for better caching.
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Sync again to install the project
RUN uv sync --frozen --no-dev

# Expose the port
EXPOSE 8000

# Start Uvicorn instantly utilizing the frozen Virtual Environment (.venv)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
