# Use a multi-stage build to reduce the final image size.

# --- Builder Stage: Install Dependencies and Package the Application ---
FROM python:3.11-slim-bookworm AS builder

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files
COPY pyproject.toml .
COPY uv.lock .

# Install uv and use it to install project dependencies
RUN pip install uv
RUN uv pip install --no-cache-dir --no-index --find-links=. .

# Copy the application code
COPY devguardian /app/devguardian
COPY README.md .

# --- Final Stage: Create the Production Image ---
FROM python:3.11-slim-bookworm

# Set the working directory
WORKDIR /app

# Copy the dependencies from the builder stage
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/devguardian /app/devguardian
COPY --from=builder /app/README.md /app/README.md

# Make .venv executable
ENV PATH="/app/.venv/bin:${PATH}"

# Set environment variables (optional, but good practice)
ENV PYTHONUNBUFFERED=1

# Expose the port (if necessary - determine from server.py)
EXPOSE 8000

# Command to run the application
CMD ["devguardian"]