"""Zentrale Konfiguration für LUKA.

Pfade und Einstellungen werden hier gebündelt, damit sie an einer Stelle
angepasst werden können. Werte lassen sich über Umgebungsvariablen überschreiben.
"""
import os
from pathlib import Path

# Projektwurzel: .../LUKA
BASE_DIR = Path(__file__).resolve().parents[2]

# Verzeichnis mit den HTML-Aufgaben (dateibasiert, Auto-Discovery in M2)
CONTENT_DIR = Path(os.getenv("LUKA_CONTENT_DIR", BASE_DIR / "content" / "aufgaben"))

# SQLite-Datenbankdatei
DATA_DIR = Path(os.getenv("LUKA_DATA_DIR", BASE_DIR / "data"))
DATABASE_PATH = DATA_DIR / "luka.db"
DATABASE_URL = os.getenv("LUKA_DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# Lokaler Klon eines optional verbundenen Aufgaben-Git-Repos (siehe Admin >
# Aufgaben). Liegt im persistenten Datenverzeichnis, nicht im Haupt-Repo.
TASKS_REPO_DIR = Path(os.getenv("LUKA_TASKS_REPO_DIR", DATA_DIR / "tasks-repo"))

# Templates
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Statische Assets (CSS, selbst gehostete Schriften) – ausschließlich lokal,
# es werden bewusst KEINE Google-Font-CDN-Links verwendet (DSGVO).
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Runtime-Assets (luka.js), die in Aufgaben injiziert werden
RUNTIME_DIR = Path(os.getenv("LUKA_RUNTIME_DIR", BASE_DIR / "runtime"))

# In Produktion (hinter HTTPS) auf "true" setzen, damit Cookies nur über
# verschlüsselte Verbindungen gesendet werden (Secure-Flag).
SECURE_COOKIES = os.getenv("LUKA_SECURE_COOKIES", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)
