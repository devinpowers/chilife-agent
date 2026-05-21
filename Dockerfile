# ── Stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install deps into a separate prefix so we can copy only them to final stage
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create the db directory and make it writable
# In Azure Container Apps, mount a persistent volume here instead
RUN mkdir -p /app/db && chmod 777 /app/db

# Streamlit config — disable file watcher (not useful in container)
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# All secrets and env-specific config come from the container runtime,
# never baked into the image (12-factor principle)
# APP_ENV, DATABASE_URL, OPENAI_API_KEY, etc. are injected at deploy time

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py"]
