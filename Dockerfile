FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic only imports settings.py (no DB/AWS connection is made), but
# config() has no defaults for these keys and .env is not copied into the
# image, so dummy build-time values are needed to satisfy them. Cloud Run
# injects the real values as env vars/secrets at runtime.
RUN SECRET_KEY=build-time-placeholder \
    DB_NAME=placeholder \
    DB_USER=placeholder \
    DB_PASSWORD=placeholder \
    DB_HOST=placeholder \
    DB_PORT=5432 \
    AWS_ACCESS_KEY_ID=placeholder \
    AWS_SECRET_ACCESS_KEY=placeholder \
    AWS_STORAGE_BUCKET_NAME=placeholder \
    AWS_S3_REGION_NAME=placeholder \
    AWS_S3_BASE_URL=placeholder \
    CLOUDFRONT_DOMAIN=placeholder \
    python manage.py collectstatic --noinput

CMD exec gunicorn dasii_backend.wsgi:application --bind 0.0.0.0:$PORT
