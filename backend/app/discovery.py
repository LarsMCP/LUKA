"""Auto-Discovery der dateibasierten HTML-Aufgaben.

Struktur: content/aufgaben/<slug>/index.html
Jede Aufgabe enthält optional einen Meta-Block:

    <script type="application/json" id="luka-task">
    { "title": "...", "subject": "..." }
    </script>

Der Scan spiegelt gefundene Aufgaben in die `tasks`-Tabelle (Insert/Update per Hash).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from sqlmodel import Session, select

from .config import CONTENT_DIR
from .database import engine
from .models import Task

_META_RE = re.compile(
    r'<script[^>]*id=["\']luka-task["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def parse_meta(html: str) -> dict:
    """Liest den JSON-Meta-Block aus dem Aufgaben-HTML. Fehlt/ungültig -> {}."""
    match = _META_RE.search(html)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1).strip())
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _slug_from_meta_or_folder(meta: dict, folder: str) -> str:
    return str(meta.get("slug") or folder)


def scan_tasks(content_dir: Path | None = None) -> dict:
    """Scannt das Aufgabenverzeichnis und aktualisiert die tasks-Tabelle.

    Returns: {"discovered": [slugs], "removed": [slugs]}.
    Aufgaben, deren Ordner nicht mehr existiert, werden aus der Tabelle entfernt.
    """
    base = content_dir or CONTENT_DIR
    discovered: list[str] = []

    with Session(engine) as session:
        found_slugs: set[str] = set()

        if base.exists():
            for entry in sorted(base.iterdir()):
                index = entry / "index.html"
                if not entry.is_dir() or not index.is_file():
                    continue

                html = index.read_text(encoding="utf-8")
                meta = parse_meta(html)
                slug = _slug_from_meta_or_folder(meta, entry.name)
                found_slugs.add(slug)

                file_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
                title = str(meta.get("title") or slug)
                subject = meta.get("subject")

                task = session.get(Task, slug)
                if task is None:
                    task = Task(slug=slug, title=title, subject=subject, hash=file_hash)
                    session.add(task)
                    discovered.append(slug)
                elif task.hash != file_hash:
                    task.title = title
                    task.subject = subject
                    task.hash = file_hash
                    session.add(task)
                    discovered.append(slug)

        # Verwaiste Aufgaben (Ordner gelöscht) entfernen.
        removed: list[str] = []
        existing = session.exec(select(Task)).all()
        for task in existing:
            if task.slug not in found_slugs:
                session.delete(task)
                removed.append(task.slug)

        session.commit()

    return {"discovered": discovered, "removed": removed}


def read_task_html(slug: str, content_dir: Path | None = None) -> str | None:
    """Liest das rohe HTML einer Aufgabe (oder None, wenn nicht vorhanden)."""
    base = content_dir or CONTENT_DIR
    index = base / slug / "index.html"
    if not index.is_file():
        return None
    return index.read_text(encoding="utf-8")
