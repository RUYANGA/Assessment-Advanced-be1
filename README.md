# Merci Assessment — Backend

API: https://merciapi.lovewaylogistics.com  
Swagger: https://merciapi.lovewaylogistics.com/swagger/

A concise reference for the Django REST backend used by the Assessment Advanced project.

Overview
--------
Django REST backend providing JWT authentication, user management and REST endpoints consumed by the frontend at https://assessment-advanced-fe.vercel.app. The application is container-ready (Docker) and deployable to services such as Render.

Prerequisites
-------------
- Python 3.12 (virtualenv recommended)
- Docker & Docker Compose (for container runs)
- git

Quick start — local (venv)
--------------------------
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

Docker (build & run)
--------------------
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
- `entrypoint.sh` runs migrations and collectstatic at container start — ensure it is committed and not excluded by `.dockerignore`.

Deployment
----------
- Render: set environment variables in the dashboard and use the Dockerfile or image. Ensure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` include deployed domains.
- If pulling images from GHCR, ensure CI/deploy user is authenticated or build locally.

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

Authenticate requests using:
```
Authorization: Bearer <access_token>
```

Environment variables
---------------------
Key variables (non-exhaustive):
- SECRET_KEY
- DEBUG (True/False)
- DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT
- ALLOWED_HOSTS (comma-separated)
- EMAIL_* for SMTP

Tests, linting & formatting
---------------------------
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

Requirements
------------
Generate an exact requirements file from your venv:
```bash
source .venv/bin/activate
pip freeze > requirements.txt
```
Commit the pinned requirements for reproducible builds.

Common troubleshooting
----------------------
- `COPY entrypoint.sh ...` fails in CI: ensure `entrypoint.sh` is committed and not excluded by `.dockerignore`.
- `Bad Request (400)` on deployed URL: add the host to `ALLOWED_HOSTS` and set:
```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```
- CORS preflight fails: verify `corsheaders` is installed, added to `INSTALLED_APPS`, and `CorsMiddleware` is placed before `CommonMiddleware`.

Security
--------
- Do not commit secrets. Rotate any credentials exposed during testing (SECRET_KEY, email app password, DB password).

Useful commands
---------------
```bash
# view logs (compose)
docker compose logs -f merci-assessment-backend

# run management command inside container
docker compose run --rm merci-assessment-backend python manage.py createsuperuser
```

Contributing / Support
----------------------
- Open issues or PRs for bugs and feature requests.
- For CI failures, run the same checks locally (black, isort, flake8) and fix formatting/import order before pushing.
