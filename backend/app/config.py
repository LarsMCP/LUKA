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

# Templates
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Runtime-Assets (luka.js), die in Aufgaben injiziert werden
RUNTIME_DIR = Path(os.getenv("LUKA_RUNTIME_DIR", BASE_DIR / "runtime"))

# In Produktion (hinter HTTPS) auf "true" setzen, damit Cookies nur über
# verschlüsselte Verbindungen gesendet werden (Secure-Flag).
SECURE_COOKIES = os.getenv("LUKA_SECURE_COOKIES", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)
