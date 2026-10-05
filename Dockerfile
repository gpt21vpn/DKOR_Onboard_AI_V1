FROM node:22-alpine AS frontend

WORKDIR /ui
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/backend/requirements.txt

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# GigaChat requires the Russian Trusted Root CA.
# Add it to Python's certifi bundle so httpx can verify GigaChat TLS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -kfsSL "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt" -o /tmp/russian_trusted_root_ca.pem \
    && cat /tmp/russian_trusted_root_ca.pem >> "$(python -m certifi)" \
    && rm -f /tmp/russian_trusted_root_ca.pem \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

COPY --from=frontend /ui/dist /app/frontend_dist

EXPOSE 8000

CMD ["sh","-c","exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
