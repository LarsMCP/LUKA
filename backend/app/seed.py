"""Seed-Skript für lokale Tests.

Legt (idempotent) eine Testklasse an und schaltet die Beispielaufgabe frei.
Ausführen:  python -m backend.app.seed

Hinweis: In M4 wird das über die Admin-Oberfläche erledigt; dieses Skript
dient nur dem lokalen Ausprobieren des Schüler-Flows.
"""
from __future__ import annotations

from sqlmodel import Session, select

from .database import engine, init_db
from .discovery import scan_tasks
from .models import Assignment, Class, Task

TEST_JOIN_CODE = "TEST01"
TEST_CLASS_NAME = "Testklasse"
TEST_TASK_SLUG = "beispiel-bruchrechnung"


def seed() -> None:
    init_db()
    scan_tasks()

    with Session(engine) as db:
        klass = db.exec(select(Class).where(Class.join_code == TEST_JOIN_CODE)).first()
        if klass is None:
            klass = Class(name=TEST_CLASS_NAME, join_code=TEST_JOIN_CODE)
            db.add(klass)
            db.commit()
            db.refresh(klass)
            print(f"Klasse angelegt: {klass.name} (Code {klass.join_code})")
        else:
            print(f"Klasse existiert bereits: {klass.name} (Code {klass.join_code})")

        if db.get(Task, TEST_TASK_SLUG) is None:
            print(
                f"Hinweis: Aufgabe '{TEST_TASK_SLUG}' nicht gefunden – "
                "liegt sie in content/aufgaben/?"
            )
            return

        existing = db.exec(
            select(Assignment).where(
                Assignment.class_id == klass.id,
                Assignment.task_slug == TEST_TASK_SLUG,
            )
        ).first()
        if existing is None:
            db.add(Assignment(class_id=klass.id, task_slug=TEST_TASK_SLUG, active=True))
            db.commit()
            print(f"Aufgabe '{TEST_TASK_SLUG}' für '{klass.name}' freigeschaltet.")
        else:
            print(f"Freischaltung existiert bereits: {TEST_TASK_SLUG}")


if __name__ == "__main__":
    seed()
