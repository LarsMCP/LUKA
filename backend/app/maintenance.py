"""Wartungs-Hilfsfunktionen.

merge_duplicate_students: Führt Schüler zusammen, die in derselben Klasse den
gleichen Anzeigenamen (case-insensitiv) haben, z.B. "anna" und "Anna". Abgaben
und Sessions werden auf den ältesten Datensatz übertragen, Duplikate gelöscht.

Ausführen:  python -m backend.app.maintenance
"""
from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from .database import engine, init_db
from .models import SessionToken, Student, Submission


def merge_duplicate_students(db: Session) -> int:
    """Führt case-insensitive Namensdubletten pro Klasse zusammen.

    Returns: Anzahl entfernter (zusammengeführter) Duplikate.
    """
    students = db.exec(select(Student)).all()
    groups: dict[tuple[int, str], list[Student]] = defaultdict(list)
    for s in students:
        groups[(s.class_id, s.display_name.strip().lower())].append(s)

    removed = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        # Ältesten Datensatz behalten (kleinste id).
        group.sort(key=lambda s: s.id)
        keeper = group[0]
        for dup in group[1:]:
            for sub in db.exec(
                select(Submission).where(Submission.student_id == dup.id)
            ).all():
                sub.student_id = keeper.id
                db.add(sub)
            for sess in db.exec(
                select(SessionToken).where(SessionToken.student_id == dup.id)
            ).all():
                sess.student_id = keeper.id
                db.add(sess)
            db.delete(dup)
            removed += 1
    db.commit()
    return removed


def main() -> None:
    init_db()
    with Session(engine) as db:
        removed = merge_duplicate_students(db)
    print(f"{removed} Dubletten zusammengeführt.")


if __name__ == "__main__":
    main()
