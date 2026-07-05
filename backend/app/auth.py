"""Authentifizierung/Session-Handling für Schüler.

Schüler loggen sich per Klassen-Code + Pseudonym ein (kein Passwort, Datenminimierung).
Nach dem Login wird ein zufälliger Session-Token als HttpOnly-Cookie gesetzt.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session

from .config import SECURE_COOKIES
from .database import get_session
from .models import SessionToken, Student

COOKIE_NAME = "luka_session"
SESSION_TTL = timedelta(days=30)


def create_session(db: Session, student_id: int, response: Response) -> str:
    """Erzeugt eine Session, speichert sie und setzt das Cookie."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + SESSION_TTL
    db.add(SessionToken(token=token, student_id=student_id, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=SECURE_COOKIES,
        max_age=int(SESSION_TTL.total_seconds()),
        path="/",
    )
    return token


def clear_session(db: Session, token: str | None, response: Response) -> None:
    """Löscht die Session (Logout)."""
    if token:
        obj = db.get(SessionToken, token)
        if obj:
            db.delete(obj)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")


def get_optional_student(
    request: Request,
    db: Session = Depends(get_session),
) -> Student | None:
    """Liefert den eingeloggten Schüler oder None (für Seiten mit Weiche)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = db.get(SessionToken, token)
    if session is None or session.expires_at < datetime.utcnow():
        return None
    return db.get(Student, session.student_id)


def get_current_student(
    student: Student | None = Depends(get_optional_student),
) -> Student:
    """Erzwingt einen eingeloggten Schüler (401, sonst)."""
    if student is None:
        raise HTTPException(status_code=401, detail="Nicht eingeloggt")
    return student
