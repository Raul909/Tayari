# ── Tayari API — Production Dockerfile ────────────────────────────────
# Optimised for Koyeb free tier (512 MB RAM, 0.1 vCPU).
# Multi-stage build keeps the final image lean.

# ── Stage 1: build dependencies ──────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only production dependencies (no ML libs — they are optional
# and the flood model already falls back to pure heuristics).
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-prod.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────
FROM python:3.12-slim

# Non-root user for security
RUN adduser --disabled-password --gecos '' tayari
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY requirements-prod.txt .

# Create uploads directory
RUN mkdir -p uploads/reports && chown -R tayari:tayari /app

USER tayari

# Koyeb free tier exposes port 8000
EXPOSE 8000

# Health check for Koyeb
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with minimal workers to fit in 512 MB RAM
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "65"]
