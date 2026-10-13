# Certify Workshops backend — Zoho Catalyst AppSail (custom Docker)
FROM python:3.12-slim

# System deps for psycopg[binary] / bcrypt builds (slim-safe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Catalyst AppSail injects X_ZOHO_CATALYST_LISTEN_PORT; default 8000 for local runs
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT:-8000}"]
