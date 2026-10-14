# syntax=docker/dockerfile:1.7

# ---- builder: resolve and install dependencies into an isolated prefix ----
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ---- runtime: slim, non-root ----
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SQLITE_PATH=/data/db.sqlite3 \
    PORT=8000
RUN useradd --system --create-home --uid 10001 app && mkdir /data && chown app /data
COPY --from=builder /install /usr/local
WORKDIR /app
RUN chown app /app # collectstatic writes staticfiles/ here
COPY --chown=app manage.py ./
COPY --chown=app config ./config
COPY --chown=app apps ./apps
COPY --chown=app docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

USER app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD python -c "import os,urllib.request as u; u.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health/')" || exit 1
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--workers", "3", "--threads", "4", "--timeout", "120", "--access-logfile", "-"]
