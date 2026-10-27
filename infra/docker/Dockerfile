FROM python:3.11-slim

LABEL org.opencontainers.image.title="Ann Reveals AI Manager (ARAIM v4.0)"
LABEL org.opencontainers.image.description="Unified Cloud Manager & Dual-Platform Purchase Verification PWA for @annreveals"
LABEL org.opencontainers.image.vendor="Ann Reveals (@annreveals)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    TIKTOK_WRITE_ENABLED=false \
    INSTAGRAM_WRITE_ENABLED=false \
    THIRD_PARTY_AUTOCOMMENT=false \
    MONTHLY_BUDGET_CAP_GBP=30.00 \
    AI_MONTHLY_SUBCAP_GBP=5.00

# Create non-root runtime user
RUN groupadd -r araim && useradd -r -g araim -d /app -s /sbin/nologin araim

WORKDIR /app

COPY . /app

RUN mkdir -p /app/data /app/backups && chown -R araim:araim /app

USER araim

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

CMD ["python3", "-m", "apps.backend.server"]
