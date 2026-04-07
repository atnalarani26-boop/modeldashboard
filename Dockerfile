# ============================================================
# Sentiment Intelligence Center — Production Dockerfile
# Runs FastAPI + Streamlit + nginx in a single container
# ============================================================
FROM python:3.11-slim

# --- System dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Working directory ---
WORKDIR /app

# --- Python dependencies (cached layer) ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Application code ---
COPY . .

# --- Bootstrap model if not present ---
RUN python bootstrap.py

# --- Config files ---
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# --- Cloud Run uses PORT env var (default 8080) ---
ENV PORT=8080
EXPOSE 8080

# --- Health check ---
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# --- Start all services via supervisord ---
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
