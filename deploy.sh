#!/bin/bash

set -e

if [ -z "$1" ]
  then
    if [ -z "$DEPLOYMENT_ENVIRONMENT" ]
      then
        echo "Usage: $0 <deployment> [task_names]"
        exit 1
    fi
  else
    DEPLOYMENT_ENVIRONMENT=$1
fi

if [ -z "$DOCKER_IMAGE_TAG" ]
  then
    export DOCKER_IMAGE_TAG="5.0.0"
fi

export EXTRA_DOCKER_RUN_OPTIONS="$EXTRA_DOCKER_RUN_OPTIONS -v $PWD/deploy_config/files/client.env.${DEPLOYMENT_ENVIRONMENT}:/home/appuser/work/docker_context/deploy_config/files/client.env"

# export DEBUG_MODE=TRUE

exec ./cr_deploy.sh "$@"
