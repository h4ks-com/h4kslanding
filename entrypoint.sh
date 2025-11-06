#!/bin/bash
set -e

cd /interface

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput --clear

echo "Starting application..."
exec "$@"
