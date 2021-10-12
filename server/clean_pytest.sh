#!/usr/bin/env bash

# When running in Docker, tt is sometimes necessary to cleanup cache files
# or else pytest reports "source code not available" and fails tests.
find . -type d -name '.pytest_cache' -exec rm -rf {} +
find . -type d -name '__pycache__' -exec rm -rf {} +
pytest "$@"
