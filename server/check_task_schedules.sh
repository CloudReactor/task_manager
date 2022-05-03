#!/usr/bin/env bash
set -Eeuxo pipefail
exec python manage.py task_schedule_checker
