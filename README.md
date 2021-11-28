# CloudReactor Task Manager

![Website](https://img.shields.io/website?url=https%3A%2F%2Fdash.cloudreactor.io)
![Security Headers](https://img.shields.io/security-headers?url=https%3A%2F%2Fapi.cloudreactor.io)
![Swagger Validator](https://img.shields.io/swagger/valid/3.0?specUrl=https%3A%2F%2Fraw.githubusercontent.com%2FCloudReactor%2Fapi-docs%2Fmaster%2Fcloudreactor-openapi3.yml)

API Server and Web Front-end for CloudReactor. Deployed to cloudreactor.io

## Requirements

* Docker (with Compose built-in)
* Python 3.9.6+ if running outside of Docker
* Node JS v12.22.5
* Postgres 13.4+

## Components

This project consists of 2 components:

1. An API server implemented in python using
[Django Rest Framework](https://www.django-rest-framework.org/). This code
lives in the `server` directory.
2. A web front-end that is written in TypeScript using the React framework
and built with [Create React App](https://create-react-app.dev/). This code
lives in the `client` directory.

## First time

Copy `server/.env.example` to `server/.env`. Then modify this file with your
AWS secrets.

Build the images:

    docker compose build web
    docker compose build dev-shell

Start the database:

    docker compose up -d db

Run the dev shell:

    docker compose run --rm dev-shell

Inside the dev shell:

    python manage.py migrate
    python manage.py load_dynamic_fixtures

This will create two users:

* An admin user with credentials `admin` / `adminpassword`
* An example user with credentials `exampleuser` / `examplepassword`

## Development

Bring up the DB and web server:

    docker compose up -d db
    docker compose up -d web

In another terminal, start the asset compiler / dev server natively:

    cd client
    nvm use (optional, but recommended, to use nvm to install nodejs)
    npm install
    npm start

(Require nodejs 12.22.5 to be installed either natively or through
[nvm](https://github.com/nvm-sh/nvm).)

Then you should be able to view the site at:

    http://localhost:3000

To view the admin site (requires a user with admin privileges):

    http://localhost:8000/admin/

To view server logs:

    docker compose logs --tail=1000 -f web

## After pulling

Update the web server and webpack builder:

    docker compose build

To migrate the DB:

    docker compose run --rm web migrate

Customizations:

As is default, users can have belong to multiple groups.

Most models are owned by a group instead of a user.
Users can view and modify all model instances owned by groups that a user is a member of.
Authentication tokens (SaasToken) identify both a user and the group the user is operating on.

## Running tests

Using Docker,

    docker compose run --rm pytest

Natively, in the `server` directory:

    pytest

## License

This software is licensed under the
[Fair Source License](https://fair.io/) with a limitation of 10 users
(Fair Source 10).

## Contributing

We welcome contributions from the community, either from individuals or
organizations. Bug fixes, new features, documentation improvements,
tests, and new Task execution methods are particularly appreciated.

If you are a contributor, you will be asked to agree to either the
[individual Contributor License Agreement](CloudReactor-Individual-Contributor-License-Agreement-1.1.pdf)
or the [entity Contributor License Agreement](CloudReactor-Entity-Contributor-License-Agreement-1.1.pdf)
by a forked version of the [cla-assistant GitHub Action](https://github.com/cla-assistant/github-action)
when you create your first pull request.
