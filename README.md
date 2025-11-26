# Merci Assessment — Backend

Lightweight README for the Django backend used by the Assessment Advanced project.

## Overview
Django REST backend providing authentication (JWT), user management, and API endpoints consumed by the frontend at `https://assessment-advanced-fe.vercel.app`. The app is containerized with Docker and deploys to platforms such as Render.

## Prerequisites
- Python 3.12 (venv recommended)
- Docker & Docker Compose (for container runs)
- git

## Quick start — local (venv)
1. Create & activate virtualenv:
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file (see `.env.example` or below) and fill values:
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

4. Run migrations and collect static:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

5. Start dev server:
```bash
python manage.py runserver
# or using gunicorn for a production-like run:
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
- The repo includes `entrypoint.sh` which runs migrations and `collectstatic` on container start.
- Ensure `.dockerignore` does not exclude `entrypoint.sh` before building.

## Deployment Notes
- Render: set environment variables in the dashboard and use the Dockerfile or image. Ensure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` include the deployed domain(s).
- If pulling images from GHCR, ensure the CI/deploy user is authenticated or build locally.

## CORS & JWT
- This app uses `django-cors-headers`. In production, set:
```python
CORS_ALLOWED_ORIGINS = [
  "https://assessment-advanced-fe.vercel.app",
]
CORS_ALLOW_HEADERS = list(default_headers) + ["authorization"]
CORS_ALLOW_CREDENTIALS = True
```
- Send JWT in requests using header:
```
Authorization: Bearer <access_token>
```

## Environment variables
Key vars (non-exhaustive):
- SECRET_KEY
- DEBUG (True/False)
- DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT
- ALLOWED_HOSTS (comma-separated)
- EMAIL_* for SMTP

## Tests, linting & formatting (CI mirrors these)
Run locally:
```bash
# tests
pytest

# formatting
black .

# import sorting
isort --profile black .

# lint
flake8 --config .flake8
```

CI expects files to be formatted with black and imports sorted with isort.

## Requirements
Generate exact requirements from your venv:
```bash
source .venv/bin/activate
pip freeze > requirements.txt
```
Commit the pinned file for reproducible builds.

## Common troubleshooting
- `COPY entrypoint.sh ...` fails in CI: ensure `entrypoint.sh` is committed and not excluded by `.dockerignore`.
- `Bad Request (400)` on deployed URL: add the host to `ALLOWED_HOSTS` and set `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` if behind a proxy.
- CORS preflight fails: verify corsheaders is installed, added to `INSTALLED_APPS`, and `CorsMiddleware` is high in `MIDDLEWARE` (before `CommonMiddleware`).

## Security
- Do not commit secrets. Rotate any credentials exposed during testing (SECRET_KEY, email app password, DB password).

## Useful commands
```bash
# view logs (compose)
docker compose logs -f merci-assessment-backend

# run management command inside container
docker compose run --rm merci-assessment-backend python manage.py createsuperuser
```

## Contributing / Support
- Create issues or PRs for bugs/features.
- For CI failures, run the same checks locally (black, isort, flake8) and fix formatting/import order before pushing.
