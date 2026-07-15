# ── Tayari API — Hugging Face Spaces Optimized Dockerfile ──────────────
# Optimised for HF Free Tier: 2 vCPU, 16 GB RAM
# Focus: Minimal cold start latency, max throughput, and cache leverage.

FROM python:3.12-slim

# Set Hugging Face specific environment variables
# HF runs on port 7860 by default
ENV PORT=7860
# Keep python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
# Prevents python from writing pyc files to disc (saves disk I/O on cold start)
ENV PYTHONDONTWRITEBYTECODE=1
# HF cache directory
ENV HF_HOME=/tmp/.cache/huggingface

# Create a non-root user with UID 1000 as required by Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy only the requirements first to leverage Docker cache layer
# We use the prod requirements which strip out heavy ML libs for faster boots
COPY --chown=user:user backend/requirements-prod.txt .

# Install dependencies (using multiple workers for pip and no-cache to keep image small,
# though the HF image gets cached anyway).
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy the backend application code
COPY --chown=user:user backend/app ./app

# Create necessary directories with correct permissions in the user's home
RUN mkdir -p $HOME/app/uploads/reports && \
    mkdir -p /tmp/.cache/huggingface && \
    chmod -R 777 $HOME/app/uploads && \
    chmod -R 777 /tmp/.cache/huggingface

EXPOSE 7860

# Health check optimized for HF
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

# Run with 2 Uvicorn workers (HF Free Tier has 2 vCPUs) to handle concurrent requests
# Using loop=uvloop (installed via uvicorn[standard]) for max async performance
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2", "--timeout-keep-alive", "65"]
