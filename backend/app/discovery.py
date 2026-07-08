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

from .config import CONTENT_DIR, TASKS_REPO_DIR
from .database import engine
from .models import Task

_META_RE = re.compile(
    r'<script[^>]*id=["\']luka-task["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

# Sucht data-solution Attribute auf Input/Select/Textarea-Elementen.
_DATA_SOLUTION_RE = re.compile(
    r'<(?:input|select|textarea)\b[^>]*\bname=["\']([^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
_DATA_SOL_ATTR_RE = re.compile(
    r'\bdata-solution\s*=\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_DATA_TYPE_ATTR_RE = re.compile(
    r'\bdata-type\s*=\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
# Sucht den SOLUTIONS-Block im <script> (Lernpfad-Format).
_SOLUTIONS_BLOCK_RE = re.compile(
    r'const\s+SOLUTIONS\s*=\s*(\{.*?\})\s*;',
    re.DOTALL,
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


def extract_solutions(html: str) -> dict | None:
    """Extrahiert Lösungen aus dem Aufgaben-HTML.

    Zwei Formate:
    1. data-solution Attribute (Fragment-Format)
    2. const SOLUTIONS = {...} im <script> (Lernpfad-Format)

    Returns einheitliches Dict: {feldname: {"answer": wert, "type": typ?}}
    oder None wenn keine Lösungen gefunden wurden.
    """
    solutions: dict = {}

    # 1. data-solution Attribute (Fragment-Format)
    for m in _DATA_SOLUTION_RE.finditer(html):
        tag = m.group(0)
        name = m.group(1)
        sol_match = _DATA_SOL_ATTR_RE.search(tag)
        if not sol_match:
            continue
        answer = sol_match.group(1)
        type_match = _DATA_TYPE_ATTR_RE.search(tag)
        entry = {"answer": answer}
        if type_match:
            entry["type"] = type_match.group(1)
        solutions[name] = entry

    # 2. const SOLUTIONS = {...} (Lernpfad-Format)
    sol_block = _SOLUTIONS_BLOCK_RE.search(html)
    if sol_block:
        try:
            raw = _parse_js_object(sol_block.group(1))
            _flatten_solutions(raw, solutions)
        except Exception:
            pass

    return solutions if solutions else None


def _parse_js_object(text: str) -> dict:
    """Parst ein vereinfachtes JS-Object-Literal zu einem Python dict.

    Behandelt Single-Quotes als String-Begrenzer und unquoted Keys.
    """
    # JS-Object zu JSON konvertieren: Single-Quotes -> Double-Quotes
    text = text.replace("'", '"')
    # Unquoted Keys quoten: {step1_A: -> {"step1_A":
    text = re.sub(r'(\w+):', r'"\1":', text)
    return json.loads(text)


def _flatten_solutions(raw: dict, solutions: dict) -> None:
    """Flacht das SOLUTIONS-Objekt zu {feld: {answer}} auf.

    step1: {step1_A: 'Würfel'} -> step1_A: {answer: 'Würfel'}
    step2: ['a', 'b'] -> step2: {answer: ['a', 'b'], type: 'checkbox'}
    """
    for key, val in raw.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                solutions[sub_key] = {"answer": sub_val}
        elif isinstance(val, list):
            solutions[key] = {"answer": val, "type": "checkbox"}
        else:
            solutions[key] = {"answer": val}


def _scan_dir(base: Path, session: Session, found_slugs: set[str], discovered: list[str]) -> None:
    """Scannt ein einzelnes Aufgabenverzeichnis und upserted in die tasks-Tabelle."""
    if not base.exists():
        return
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
        solutions = extract_solutions(html)
        solutions_str = json.dumps(solutions, ensure_ascii=False) if solutions else None
        if task is None:
            task = Task(slug=slug, title=title, subject=subject, hash=file_hash,
                        solutions_json=solutions_str)
            session.add(task)
            discovered.append(slug)
        elif task.hash != file_hash:
            task.title = title
            task.subject = subject
            task.hash = file_hash
            task.solutions_json = solutions_str
            session.add(task)
            discovered.append(slug)
        elif task.solutions_json != solutions_str:
            task.solutions_json = solutions_str
            session.add(task)


def scan_tasks(content_dir: Path | None = None) -> dict:
    """Scannt die Aufgabenverzeichnisse und aktualisiert die tasks-Tabelle.

    Liest sowohl das lokale Verzeichnis (`content/aufgaben`, bzw. `content_dir`
    falls angegeben) als auch – falls verbunden – den Klon eines externen
    Aufgaben-Git-Repos (`TASKS_REPO_DIR`, siehe task_repo.py). Bei gleichem
    Slug in beiden Quellen gewinnt das Git-Repo (wird zuletzt eingelesen).

    Returns: {"discovered": [slugs], "removed": [slugs]}.
    Aufgaben, deren Ordner in keiner Quelle mehr existiert, werden entfernt.
    """
    base = content_dir or CONTENT_DIR
    discovered: list[str] = []

    with Session(engine) as session:
        found_slugs: set[str] = set()

        _scan_dir(base, session, found_slugs, discovered)
        _scan_dir(TASKS_REPO_DIR, session, found_slugs, discovered)

        # Verwaiste Aufgaben (Ordner in keiner Quelle mehr vorhanden) entfernen.
        removed: list[str] = []
        existing = session.exec(select(Task)).all()
        for task in existing:
            if task.slug not in found_slugs:
                session.delete(task)
                removed.append(task.slug)

        session.commit()

    return {"discovered": discovered, "removed": removed}


def read_task_html(slug: str, content_dir: Path | None = None) -> str | None:
    """Liest das rohe HTML einer Aufgabe (oder None, wenn nicht vorhanden).

    Sucht zuerst im Git-Repo-Klon (falls vorhanden), dann im lokalen
    Verzeichnis – konsistent zur Vorrang-Regel in `scan_tasks()`.
    """
    for base in (TASKS_REPO_DIR, content_dir or CONTENT_DIR):
        index = base / slug / "index.html"
        if index.is_file():
            return index.read_text(encoding="utf-8")
    return None
