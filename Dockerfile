# Stage 1: build the React frontend.
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: run Flask with gunicorn and serve the built frontend.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist
# Exactly one worker: campaign state lives in process memory.
CMD ["sh", "-c", "exec gunicorn -w 1 --threads 8 -b 0.0.0.0:${PORT:-8000} --access-logfile - backend.wsgi:app"]
