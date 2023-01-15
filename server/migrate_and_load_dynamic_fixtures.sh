#!/usr/bin/env bash

set -Eeuxo pipefail

python manage.py migrate
exec python manage.py load_dynamic_fixtures
