FROM python:3.12-slim

# Copy the uv package manager from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Use copy instead of hardlinks since we are building an image
ENV UV_LINK_MODE=copy
# Ensure the virtual environment's bin directory is in the system PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies without installing the project itself yet
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Sync the full project
RUN uv sync --frozen --no-dev

# Expose the default port (optional, mostly for local documentation)
EXPOSE 8000

# Start the application using a shell to properly expand the $PORT environment variable.
# Both Heroku and Google Cloud Run pass the assigned port dynamically via $PORT.
CMD ["sh", "-c", "uvicorn src:app --host 0.0.0.0 --port ${PORT:-8000}"]
