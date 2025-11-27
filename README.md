# Merci Assessment — Backend

Frontend Source: https://github.com/RUYANGA/Assessment-Advanced-fe

API: https://merciapi.lovewaylogistics.com
Swagger: https://merciapi.lovewaylogistics.com/swagger/

A concise reference for the Django REST backend used by the Assessment Advanced project.

## Overview

Django REST backend providing JWT authentication, user management and REST endpoints
consumed by the frontend at https://assessment-advanced-fe.vercel.app. The application is
container-ready (Docker) and deployable to services such as Render.

## Prerequisites

- Python 3.12 (virtualenv recommended)
- Docker & Docker Compose (for container runs)
- git

## Quick start — local (venv)

1. Create & activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file (see `.env.example`) and populate required values:

```env
SECRET_KEY=replace_with_secret
DEBUG=True
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```

4. Run migrations and collect static assets:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

5. Start the development server:

```bash
python manage.py runserver
# or for a production-like run:
gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

## Docker (build & run)

Build locally and run:

```bash
docker build -t merci-backend .
docker run --rm -p 8000:8000 --env-file .env merci-backend
```

With Compose (recommended):

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f merci-assessment-backend
```

Notes:
- `entrypoint.sh` runs migrations and collectstatic at container start — ensure it is
  committed and not excluded by `.dockerignore`.

## Deployment

- Render: set environment variables in the dashboard and use the Dockerfile or image.
  Ensure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` include deployed domains.
- If pulling images from GHCR, ensure CI/deploy user is authenticated or build locally.

## CORS & JWT

This project uses `django-cors-headers`. Example production settings:

```python
CORS_ALLOWED_ORIGINS = [
    "https://assessment-advanced-fe.vercel.app",
]
CORS_ALLOW_HEADERS = list(default_headers) + ["authorization"]
CORS_ALLOW_CREDENTIALS = True
```

Authenticate requests using:

```
Authorization: Bearer <access_token>
```

## Environment variables

Key variables (non-exhaustive):
- SECRET_KEY
- DEBUG (True/False)
- DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT
- ALLOWED_HOSTS (comma-separated)
- EMAIL_* for SMTP

## Tests, linting & formatting

CI mirrors these checks. Run locally:

```bash
# tests
pytest

# formatting
black .

# import sorting
isort --profile black .

# linting
flake8 --config .flake8
```

## Requirements

Generate an exact requirements file from your venv:

```bash
source .venv/bin/activate
pip freeze > requirements.txt
```

Commit the pinned requirements for reproducible builds.

## Common troubleshooting

- `COPY entrypoint.sh ...` fails in CI: ensure `entrypoint.sh` is committed and not
  excluded by `.dockerignore`.
- `Bad Request (400)` on deployed URL: add the host to `ALLOWED_HOSTS` and set:

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```
- CORS preflight fails: verify `corsheaders` is installed, added to `INSTALLED_APPS`,
  and `CorsMiddleware` is placed before `CommonMiddleware`.

## Security

- Do not commit secrets. Rotate any credentials exposed during testing (SECRET_KEY,
  email app password, DB password).

## Useful commands

```bash
# view logs (compose)
docker compose logs -f merci-assessment-backend

# run management command inside container
docker compose run --rm merci-assessment-backend python manage.py createsuperuser
```

## Contributing / Support

- Open issues or PRs for bugs and feature requests.
- For CI failures, run the same checks locally (black, isort, flake8) and fix formatting/import order before pushing.
# Merci Assessment — Backend

Frontend Source: https://github.com/RUYANGA/Assessment-Advanced-fe
API: https://merciapi.lovewaylogistics.com
Swagger: https://merciapi.lovewaylogistics.com/swagger/

Overview
--------
This repository contains the Django REST backend for the Assessment Advanced project. The
service provides JWT authentication, user management, approval/purchase workflows and REST
endpoints consumed by the frontend at `https://assessment-advanced-fe.vercel.app`.

The application is container-ready and can be deployed with Docker, Render, or similar
platforms.

Prerequisites
-------------
- Python 3.12 (use a virtual environment)
- Docker & Docker Compose (optional — for containerized runs)
- git

Quick start — local (virtualenv)
-------------------------------
1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file (see `.env.example`) and set required variables:

```env
SECRET_KEY=replace_with_secret
DEBUG=True
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```

4. Apply migrations and collect static files:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

5. Run the development server:

```bash
python manage.py runserver
# or production-like with Gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

Docker (build & run)
--------------------
Build and run locally:

```bash
docker build -t merci-backend .
docker run --rm -p 8000:8000 --env-file .env merci-backend
```

Recommended: use Docker Compose for local stacks:

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f merci-assessment-backend
```

Note: `entrypoint.sh` runs migrations and collectstatic at container start. Make sure
it is present and not excluded by `.dockerignore`.

Deployment
----------
- Render: set environment variables in the dashboard and deploy using the Dockerfile or
    a built image. Ensure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` include your domain(s).
- If you push images to a registry (GHCR/Docker Hub), ensure CI has credentials (secrets)
    configured for pushing.

CORS & JWT
----------
This project uses `django-cors-headers`. Example production settings:

```python
CORS_ALLOWED_ORIGINS = [
        "https://assessment-advanced-fe.vercel.app",
]
CORS_ALLOW_HEADERS = list(default_headers) + ["authorization"]
CORS_ALLOW_CREDENTIALS = True
```

Authenticate requests with the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Environment variables
---------------------
Key variables used by the application (non-exhaustive):

- `SECRET_KEY`
- `DEBUG` (True/False)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `ALLOWED_HOSTS` (comma-separated)
- `EMAIL_*` for SMTP configuration

Tests, linting & formatting
---------------------------
CI mirrors these checks. Run the same commands locally before pushing:

```bash
# run tests
pytest

# format code
black .

# sort imports
isort --profile black .

# lint
flake8 --config .flake8
```

Requirements
------------
Pin exact dependencies from your virtual environment:

```bash
source .venv/bin/activate
pip freeze > requirements.txt
```

Common troubleshooting
----------------------
- `COPY entrypoint.sh ...` fails in CI: ensure `entrypoint.sh` is committed and not
    excluded by `.dockerignore`.
- `Bad Request (400)` on deployed URL: add the host to `ALLOWED_HOSTS` and set:

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```
- CORS preflight fails: verify `corsheaders` is installed, added to `INSTALLED_APPS`,
    and `CorsMiddleware` is placed before `CommonMiddleware`.

Security
--------
- Never commit secrets to source control. Rotate any credentials that may have been
    exposed during development or testing (SECRET_KEY, email passwords, DB credentials).

Useful commands
---------------

```bash
# view Docker Compose logs
docker compose logs -f merci-assessment-backend

# run a management command inside the container
docker compose run --rm merci-assessment-backend python manage.py createsuperuser
```

Contributing / Support
----------------------
- Open issues or PRs for bugs and feature requests.
- For CI failures, run the same checks locally (black, isort, flake8) and fix formatting
    and import ordering before pushing changes.

