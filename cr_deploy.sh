#!/bin/bash

# BSD 2-Clause License

# Copyright (c) 2021 to present, CloudReactor
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# This script uses the aws-ecs-cloudreactor-deployer Docker image to
# deploy Tasks to AWS ECS and CloudReactor.
#
# It will call the deploy.py script in the image, which
# calls ansible-playbook to run build and deployment steps.
#
# The behavior of ansible-playbook can be modified with many command-line
# options which you can pass to it by first adding the --ansible-args
# option, then all the options you want to pass to ansible-playbook.
# For example, to use secrets encrypted with ansible-vault
# and get the encryption password from the command-line during deployment:
#
# ./cr_deploy.sh staging --ansible-args --ask-vault-pass
#
# Alternatively, you can use a password file:
#
# ./cr_deploy.sh staging --ansible-args --vault-password-file pw.txt
#
# The password file could be a plaintext file, or a script like this:
#
# #!/bin/bash
# echo `aws s3 cp s3://widgets-co/vault_pass.$DEPLOYMENT_ENVIRONMENT.txt -`
#
# If you use a password file, make sure it is available in the Docker
# context of the container. You can either put it in your Docker context
# directory or add an additional mount option to the docker command-line.
#
# This script also puts the variables defined in deploy.env and
# deploy.[environment].env into the environment
# that deploy.py runs in, which in turn passes the environment to
# ansible-playbook.
#
# If possible, try to avoid modifying this script, because this project
# will frequently update it with options. Instead, create a wrapper script
# that configures some settings with environment variables, then calls
# this script. Some things your wrapper script could do include:
#
#   - Passing secrets to the deploy container via environment variables
#   - Passing AWS (temporary) credentials to the deployer container
#   - Fetching the Ansible Vault password and using it to set
#     CLOUDREACTOR_TASK_VERSION_SIGNATURE
#   - Computing a commit signature and using it to set
#     CLOUDREACTOR_TASK_VERSION_SIGNATURE

set -eo pipefail

if [ -z "$1" ]
  then
    if [ -z "$DEPLOYMENT_ENVIRONMENT" ]
      then
        echo "Usage: $0 <deployment> [task_names]"
        exit 1
    fi
  else
    DEPLOYMENT_ENVIRONMENT=$1
    shift
fi

echo "DEPLOYMENT_ENVIRONMENT = $DEPLOYMENT_ENVIRONMENT"

if [ -z "$1" ] || [[ "$1" =~ ^- ]]
  then
    if [ -z "$TASK_NAMES" ]
      then
        TASK_NAMES="ALL"
    fi
  else
    export TASK_NAMES=$1
    shift
fi

if [ -z "$CONFIG_FILENAME_STEM" ]
  then
    CONFIG_FILENAME_STEM="$DEPLOYMENT_ENVIRONMENT"
fi

VAR_FILENAME="deploy_config/vars/$CONFIG_FILENAME_STEM.yml"

echo "VAR_FILENAME = $VAR_FILENAME"

if [[ ! -f $VAR_FILENAME ]]
  then
    echo "$VAR_FILENAME does not exist, please copy deploy_config/vars/example.yml to $VAR_FILENAME and fill in your secrets."
    exit 1
fi

ENV_FILE_OPTIONS="-e WORK_DIR=/home/appuser/work"

if [[ -f "deploy.env" ]]
  then
    ENV_FILE_OPTIONS="--env-file deploy.env"
fi

# Environment-specific deployment settings are assumed to be in
# deploy.[environment].env but you can override the location by setting
# PER_ENV_SETTINGS_FILE.
if [ -z "$PER_ENV_SETTINGS_FILE" ]
  then
    PER_ENV_SETTINGS_FILE="deploy.$CONFIG_FILENAME_STEM.env"
fi

if [[ -f $PER_ENV_SETTINGS_FILE ]]
  then
    ENV_FILE_OPTIONS="$ENV_FILE_OPTIONS --env-file $PER_ENV_SETTINGS_FILE"
fi

if [ -z "$EXTRA_DOCKER_RUN_OPTIONS" ]
  then
    EXTRA_DOCKER_RUN_OPTIONS=""
fi

if [ "$DEPLOYMENT_ENVIRONMENT" != "$CONFIG_FILENAME_STEM" ]
  then
    EXTRA_DOCKER_RUN_OPTIONS="-e CONFIG_FILENAME_STEM=$CONFIG_FILENAME_STEM $EXTRA_DOCKER_RUN_OPTIONS"
fi

# The default Docker context directory on the host is the current directory.
# Override by setting DOCKER_CONTEXT_DIR to an absolute path.
if [ -z "$DOCKER_CONTEXT_DIR" ]
  then
    DOCKER_CONTEXT_DIR="$PWD"
fi

echo "Docker context dir = $DOCKER_CONTEXT_DIR"

# The default Dockerfile location is /home/appuser/work/Dockerfile
# (in the container's filesystem).
# Override by setting DOCKERFILE_PATH to an absolute path in the
# container's filesystem, or a path relative to the Docker context directory.
if [ -n "$DOCKERFILE_PATH" ]
  then
    EXTRA_DOCKER_RUN_OPTIONS="$EXTRA_DOCKER_RUN_OPTIONS -e DOCKERFILE_PATH=$DOCKERFILE_PATH"
fi

# The default Docker image name is "ghcr.io/cloudreactor/aws-ecs-cloudreactor-deployer"
# which comes from GitHub Packages. You may also get the image from
# DockerHub by setting
# DOCKER_IMAGE_NAME="cloudreactor/aws-ecs-cloudreactor-deployer"
# Or, if deploying from within AWS, use the image in AWS ECR Public:
# DOCKER_IMAGE_NAME=public.ecr.aws/x2w9p9b7/aws_ecs_cloudreactor_deployer
# You can also use a custom image by setting DOCKER_IMAGE_NAME.
if [ -z "$DOCKER_IMAGE_NAME" ]
  then
    DOCKER_IMAGE_NAME="ghcr.io/cloudreactor/aws-ecs-cloudreactor-deployer"
fi

echo "Docker image name = $DOCKER_IMAGE_NAME"

# By default, the Docker image tag is 3, since this project uses
# semantic versioning and non-compatible changes will increment the
# major version number.
# For repeatable builds, pin the DOCKER_IMAGE_TAG to a version that is
# known to work.
if [ -z "$DOCKER_IMAGE_TAG" ]
  then
    DOCKER_IMAGE_TAG="3"
fi

echo "Docker image tag = $DOCKER_IMAGE_TAG"

if [ "$DEBUG_MODE" == "TRUE" ]
  then
    EXTRA_DOCKER_RUN_OPTIONS="-ti $EXTRA_DOCKER_RUN_OPTIONS --entrypoint bash"
fi

if [ "$PASS_AWS_ACCESS_KEY" == "TRUE" ]
  then
    EXTRA_DOCKER_RUN_OPTIONS="-e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY $EXTRA_DOCKER_RUN_OPTIONS"
fi

# GitHub Actions must be run as root, but keep this as a variable in case
# we publish another Docker image that runs as appuser.
DOCKER_USER_HOME=/root

if [ "$USE_USER_AWS_CONFIG" == "TRUE" ]
  then
    EXTRA_DOCKER_RUN_OPTIONS="-v $HOME/.aws:$DOCKER_USER_HOME/.aws $EXTRA_DOCKER_RUN_OPTIONS"
    if [ -n "$AWS_PROFILE" ]
      then
        EXTRA_DOCKER_RUN_OPTIONS="-e AWS_PROFILE $EXTRA_DOCKER_RUN_OPTIONS"
    fi
fi

if [ -n "$AWS_DEFAULT_REGION" ]
    then
      EXTRA_DOCKER_RUN_OPTIONS="-e AWS_DEFAULT_REGION $EXTRA_DOCKER_RUN_OPTIONS"
fi

if [ -n "$ANSIBLE_VAULT_PASSWORD" ]
    then
      EXTRA_DOCKER_RUN_OPTIONS="-e ANSIBLE_VAULT_PASSWORD $EXTRA_DOCKER_RUN_OPTIONS"
fi


echo "Extra Docker run options = '$EXTRA_DOCKER_RUN_OPTIONS'"

# Optional: use the latest git commit hash to set the version signature,
# so that the git commit can be linked in the CloudReactor dashboard.
# Otherwise, ansible will use the current date/time as the task version signature.
# You can comment out the next block if you don't use git, or set the
# CLOUDREACTOR_TASK_VERSION_SIGNATURE variable before calling this script.
if [ -z "$CLOUDREACTOR_TASK_VERSION_SIGNATURE" ]
  then
    if command -v git &> /dev/null
      then
        CLOUDREACTOR_TASK_VERSION_SIGNATURE=`git rev-parse HEAD`
        echo "CLOUDREACTOR_TASK_VERSION_SIGNATURE = $CLOUDREACTOR_TASK_VERSION_SIGNATURE"
      else
        echo "git not found, setting CLOUDREACTOR_TASK_VERSION_SIGNATURE to empty string"
        CLOUDREACTOR_TASK_VERSION_SIGNATURE=""
    fi
fi
# End Optional

if [ -z "$DEPLOY_COMMAND" ]
  then
    if [ "$DEBUG_MODE" == "TRUE" ]
      then
        DEPLOY_COMMAND=""
      else
        DEPLOY_COMMAND="$DEPLOYMENT_ENVIRONMENT $TASK_NAMES"

        if [ -n "$EXTRA_ANSIBLE_OPTIONS" ]
          then
            DEPLOY_COMMAND="$DEPLOY_COMMAND --ansible-args $EXTRA_ANSIBLE_OPTIONS"
        fi
    fi
fi

exec docker run --rm \
  -e CLOUDREACTOR_TASK_VERSION_SIGNATURE=$CLOUDREACTOR_TASK_VERSION_SIGNATURE \
  -e HOST_PWD=$PWD \
  -e CONTAINER_DOCKER_CONTEXT_DIR=/home/appuser/work/docker_context \
  $ENV_FILE_OPTIONS \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $PWD/deploy_config:/home/appuser/work/deploy_config \
  -v $DOCKER_CONTEXT_DIR:/home/appuser/work/docker_context \
  $EXTRA_DOCKER_RUN_OPTIONS \
  $DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG \
  $DEPLOY_COMMAND "$@"
