#!/usr/bin/env bash

set -Eeuxo pipefail

python manage.py migrate
python manage.py load_dynamic_fixtures
exec gunicorn task_manager.wsgi --threads=3 --bind 0.0.0.0:8000
