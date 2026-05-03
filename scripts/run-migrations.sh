#!/bin/sh
set -e
export PYTHONPATH=/usr/lib/python3.11/site-packages:/app/backend
cd /app/backend
python -m alembic upgrade head
