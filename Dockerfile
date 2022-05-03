# Alpine base image can lead to long compilation times and errors.
# https://pythonspeed.com/articles/base-image-python-docker-images/
FROM python:3.9.12-slim-buster

LABEL maintainer="jeff@cloudreactor.io"

EXPOSE 8000

RUN apt-get update \
  && apt-get install binutils=2.31.1-16 libproj-dev=5.2.0-1 \
  gdal-bin=2.4.0+dfsg-1+b1 git=1:2.20.1-2+deb10u3 \
  libpq-dev build-essential=12.6 \
  -y --no-install-recommends \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Run as non-root user for better security
RUN groupadd appuser && useradd -g appuser --create-home appuser
USER appuser

# Output directly to the terminal to prevent logs from being lost
# https://stackoverflow.com/questions/59812009/what-is-the-use-of-pythonunbuffered-in-docker-file
ENV PYTHONUNBUFFERED 1

# Don't write *.pyc files
ENV PYTHONDONTWRITEBYTECODE 1

# Enable the fault handler for segfaults
# https://docs.python.org/3/library/faulthandler.html
ENV PYTHONFAULTHANDLER 1

# So that pip-compile is available in path
ENV PATH="/home/appuser/.local/bin:${PATH}"

ENV INSTALL_PATH /home/appuser/src
RUN mkdir $INSTALL_PATH
WORKDIR $INSTALL_PATH
ENV DJANGO_IN_DOCKER TRUE
ENV DJANGO_STATIC_ROOT $INSTALL_PATH/static
ENV CRA_ROOT $INSTALL_PATH/client/build
ENV WHITENOISE_ROOT $INSTALL_PATH/root
RUN mkdir -p $DJANGO_STATIC_ROOT
RUN mkdir -p $CRA_ROOT
RUN mkdir -p $WHITENOISE_ROOT

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-input --no-cache-dir pip-tools==6.6.0 requests==2.27.1

WORKDIR /tmp
COPY server/requirements.in .

RUN pip-compile --allow-unsafe --generate-hashes \
  requirements.in --output-file requirements.txt

# install dependencies
RUN pip install --no-input --no-cache-dir -r requirements.txt

ARG asset_path=./client/build

COPY ${asset_path}/index.html $CRA_ROOT
COPY ${asset_path}/*.ico $WHITENOISE_ROOT/
COPY ${asset_path}/*.js* $WHITENOISE_ROOT/
COPY ${asset_path}/images $WHITENOISE_ROOT/images

COPY ./server/migrate_and_runserver.sh .
COPY ./server/check_task_schedules.sh .
COPY ./server/enforce_usage_limits.sh .
COPY ./server/manage.py .
COPY ./server/task_manager task_manager
COPY ./server/spectacular spectacular
COPY ./server/processes processes

COPY ${asset_path}/static $CRA_ROOT/static

RUN python manage.py collectstatic --no-input

ENTRYPOINT ["python", "-m", "proc_wrapper", $TASK_COMMAND]
