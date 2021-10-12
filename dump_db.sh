#!/usr/bin/env bash
docker-compose run --rm db sh -c "pg_dump -U web -h db cloudreactor_task_manager >> fixtures/initial_data.sql"
