#!/usr/bin/env bash
set -Eeuxo pipefail
exec python manage.py usage_limit_enforcer
