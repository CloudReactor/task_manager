#!/usr/bin/env bash
set -e
docker compose stop db
docker compose rm -f -v -s db
docker compose up -d db
# Wait for DB to start serving requests
sleep 20
docker compose run --rm db psql -U web -h db cloudreactor_task_manager -f db-setup.sql
docker compose run --rm web migrate

docker compose run --rm db psql -U web -h db cloudreactor_task_manager_test -f db-setup.sql
