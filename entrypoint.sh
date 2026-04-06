#!/bin/bash
set -e

cd /interface

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Creating cache table..."
uv run python manage.py createcachetable 2>/dev/null || true

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput --clear

echo "Starting clocks app..."
DJANGO_SETTINGS_MODULE=h4kslanding.settings_clocks \
  uv run gunicorn --bind ":${CLOCKS_PORT:-20001}" --workers 2 h4kslanding.wsgi:application &

echo "Starting application..."
exec "$@"
