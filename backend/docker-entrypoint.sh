#!/bin/sh
# Prepare the cache table and static files, then hand off to the CMD (gunicorn).
set -e
python manage.py createcachetable
python manage.py collectstatic --noinput >/dev/null
exec "$@" --bind "0.0.0.0:${PORT:-8000}"
