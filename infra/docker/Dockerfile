FROM python:3.11-slim

LABEL org.opencontainers.image.title="Ann Reveals AI Manager"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    ARAIM_DB_PATH=/app/data/database/ann_reveals_manager.db \
    ARAIM_BACKUP_DIR=/app/data/backups \
    TIKTOK_WRITE_ENABLED=false \
    INSTAGRAM_WRITE_ENABLED=false \
    THIRD_PARTY_AUTOCOMMENT=false

RUN groupadd --gid 10001 araim \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin araim \
    && install -d -m 0750 -o araim -g araim /app/data /app/data/database /app/data/backups

WORKDIR /app
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir --requirement requirements.txt
COPY apps/ ./apps/
COPY backend/ ./backend/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

USER araim
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python3", "-c", "import os, urllib.request; port=int(os.environ['PORT']); urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/health', timeout=3).close()"]

CMD ["python3", "-m", "backend.main"]
