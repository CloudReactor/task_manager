# Alpine base image can lead to long compilation times and errors.
# https://pythonspeed.com/articles/base-image-python-docker-images/

# For AWS
FROM public.ecr.aws/docker/library/python:3.12.12-slim-bookworm

# For generic infrastructure provider
# FROM python:3.12.12-slim-bookworm

LABEL maintainer="jeff@cloudreactor.io"

EXPOSE 8000

RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install binutils libproj-dev \
  gdal-bin git \
  libpq-dev build-essential \
  expat \
  -y --no-install-recommends \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Output directly to the terminal to prevent logs from being lost
# https://stackoverflow.com/questions/59812009/what-is-the-use-of-pythonunbuffered-in-docker-file
ENV PYTHONUNBUFFERED 1

# Don't write *.pyc files
ENV PYTHONDONTWRITEBYTECODE 1

# Enable the fault handler for segfaults
# https://docs.python.org/3/library/faulthandler.html
ENV PYTHONFAULTHANDLER 1

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Prevent uv from creating a virtual environment (install to system python)
ENV UV_SYSTEM_PYTHON=1

# Install uv for package management
RUN pip install --no-cache-dir --disable-pip-version-check uv==0.5.11

# Install Python dependencies as root before switching to non-root user
# Using export->install instead of sync for better Docker layer caching
COPY server/pyproject.toml server/uv.lock /tmp/
RUN cd /tmp && \
    uv export --no-dev --frozen -o requirements.txt && \
    uv pip install --no-cache -r requirements.txt && \
    rm -rf /tmp/*

# Run as non-root user for better security
RUN groupadd appuser && useradd -g appuser --create-home appuser
USER appuser

ENV DJANGO_IN_DOCKER=TRUE \
    INSTALL_PATH=/home/appuser/src
ENV DJANGO_STATIC_ROOT=$INSTALL_PATH/static \
    CRA_ROOT=$INSTALL_PATH/client/build \
    WHITENOISE_ROOT=$INSTALL_PATH/root

RUN mkdir -p $INSTALL_PATH $DJANGO_STATIC_ROOT $CRA_ROOT $WHITENOISE_ROOT

ARG asset_path=./client/build

COPY ${asset_path}/index.html $CRA_ROOT
COPY ${asset_path}/*.ico ${asset_path}/*.js* $WHITENOISE_ROOT/
COPY ${asset_path}/images $WHITENOISE_ROOT/images

WORKDIR $INSTALL_PATH

COPY --chown=appuser:appuser ./server/manage.py ./server/migrate_and_runserver.sh ./server/migrate_and_load_dynamic_fixtures.sh ./
COPY --chown=appuser:appuser ./server/task_manager task_manager
COPY --chown=appuser:appuser ./server/spectacular spectacular
COPY --chown=appuser:appuser ./server/processes processes

COPY ${asset_path}/assets $CRA_ROOT/static

RUN python manage.py collectstatic --no-input

ENTRYPOINT ["python", "-m", "proc_wrapper"]
