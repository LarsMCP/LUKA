"""Legt ein Admin-/Lehrer-Konto an (oder setzt das Passwort neu).

Nutzung:
    python -m backend.app.create_admin <username> [--role admin|teacher]

Das Passwort wird interaktiv (verdeckt) abgefragt.
"""
from __future__ import annotations

import argparse
import getpass

from sqlmodel import Session, select

from .admin_auth import hash_password
from .database import engine, init_db
from .models import Teacher


def main() -> None:
    parser = argparse.ArgumentParser(description="LUKA Admin-Konto anlegen")
    parser.add_argument("username")
    parser.add_argument("--role", default="admin", choices=["admin", "teacher"])
    args = parser.parse_args()

    password = getpass.getpass("Passwort: ")
    confirm = getpass.getpass("Passwort bestätigen: ")
    if password != confirm:
        raise SystemExit("Passwörter stimmen nicht überein.")
    if len(password) < 8:
        raise SystemExit("Passwort sollte mindestens 8 Zeichen haben.")

    init_db()
    with Session(engine) as db:
        teacher = db.exec(
            select(Teacher).where(Teacher.username == args.username)
        ).first()
        if teacher is None:
            teacher = Teacher(
                username=args.username,
                password_hash=hash_password(password),
                role=args.role,
            )
            db.add(teacher)
            action = "angelegt"
        else:
            teacher.password_hash = hash_password(password)
            teacher.role = args.role
            db.add(teacher)
            action = "aktualisiert"
        db.commit()
    print(f"Konto '{args.username}' ({args.role}) {action}.")


if __name__ == "__main__":
    main()
