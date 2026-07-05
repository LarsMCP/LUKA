FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Abhängigkeiten zuerst (bessere Layer-Caching-Nutzung)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode + Runtime-Assets
COPY backend/ ./backend/
COPY runtime/ ./runtime/

# Daten- und Contentverzeichnisse werden per Volume gemountet (siehe compose)
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
