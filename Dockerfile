# Один контейнер на всё: API, бот (через вебхук) и собранное мини-приложение.

# --- Сборка мини-приложения ---
FROM node:24-alpine AS webapp
WORKDIR /webapp
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci
COPY webapp/ ./
RUN npm run build

# --- Бэкенд ---
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=webapp /webapp/dist ./static

# При каждом старте: миграции базы, справочник игр (повторный запуск безопасен), затем API.
# PORT задаёт хостинг (у Render — 10000).
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed_games && uvicorn app.api.main:create_app_from_settings --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
