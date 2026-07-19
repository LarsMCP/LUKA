# ── Stage 1: React-Frontend bauen ─────────────────────────────
FROM node:22-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python-Backend + fertiges Frontend ───────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# git wird für das optionale externe Aufgaben-Repo benötigt (siehe task_repo.py).
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten zuerst (bessere Layer-Caching-Nutzung)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode + Runtime-Assets
COPY backend/ ./backend/
COPY runtime/ ./runtime/

# React-Build aus Stage 1 kopieren
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Daten- und Contentverzeichnisse werden per Volume gemountet (siehe compose)
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
