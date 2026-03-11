# Multi-stage build — keeps final image lean
# Stage 1: Builder — installs all deps into a venv
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv

# Copy only the dependency manifest first (cache-friendly layer)
COPY pyproject.toml .

# Install project deps into a proper venv using uv
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache-dir -e .

# Copy source code
COPY devguardian /app/devguardian
COPY README.md .

# ──────────────────────────────────────────────
# Stage 2: Runtime — lean final image
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy the venv and application from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/devguardian /app/devguardian
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Put venv on PATH so `devguardian` command is found
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

# DevGuardian reads from stdio (MCP protocol) — no port needed
# EXPOSE 8000 is kept for reference if HTTP mode is added later
EXPOSE 8000

# Run the MCP server
CMD ["devguardian"]