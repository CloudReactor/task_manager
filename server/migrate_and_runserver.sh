#!/usr/bin/env bash

set -Eeuxo pipefail

python manage.py migrate
python manage.py load_dynamic_fixtures
exec gunicorn task_manager.wsgi --bind 0.0.0.0:8000 --workers=2 --threads=4 --worker-class=gthread --worker-tmp-dir /dev/shm
