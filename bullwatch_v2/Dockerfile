# ─────────────────────────────────────────────────────────
# BullWatch v2 — Production Dockerfile
# ─────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY . .

# Environment defaults
ENV BULLWATCH_ENV=production \
    BULLWATCH_HOST=0.0.0.0 \
    BULLWATCH_PORT=34000 \
    LOG_LEVEL=WARNING \
    RATELIMIT_ENABLED=true \
    PYTHONUNBUFFERED=1

EXPOSE 34000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:34000/api/orderflow/health || exit 1

# Production: gunicorn with 1 worker (due to background threads + websocket)
CMD ["gunicorn", "wsgi:app", \
     "--bind", "0.0.0.0:34000", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
