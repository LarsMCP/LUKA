"""Authentifizierung für Lehrer/Admin (Passwort-basiert).

Passwörter werden mit Argon2 gehasht. Nach dem Login wird ein zufälliger
Session-Token als HttpOnly-Cookie gesetzt (getrennt vom Schüler-Cookie).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session

from .config import SECURE_COOKIES
from .database import get_session
from .models import AdminSession, Teacher
from .security import hash_password, verify_password  # noqa: F401 (re-export)

ADMIN_COOKIE = "luka_admin"
ADMIN_SESSION_TTL = timedelta(hours=12)


def create_admin_session(db: Session, teacher_id: int, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + ADMIN_SESSION_TTL
    db.add(AdminSession(token=token, teacher_id=teacher_id, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=SECURE_COOKIES,
        max_age=int(ADMIN_SESSION_TTL.total_seconds()),
        path="/",
    )
    return token


def clear_admin_session(db: Session, token: str | None, response: Response) -> None:
    if token:
        obj = db.get(AdminSession, token)
        if obj:
            db.delete(obj)
            db.commit()
    response.delete_cookie(ADMIN_COOKIE, path="/")


def get_optional_teacher(
    request: Request,
    db: Session = Depends(get_session),
) -> Teacher | None:
    token = request.cookies.get(ADMIN_COOKIE)
    if not token:
        return None
    session = db.get(AdminSession, token)
    if session is None or session.expires_at < datetime.utcnow():
        return None
    return db.get(Teacher, session.teacher_id)


def get_current_teacher(
    teacher: Teacher | None = Depends(get_optional_teacher),
) -> Teacher:
    if teacher is None:
        raise HTTPException(status_code=401, detail="Nicht als Lehrer eingeloggt")
    return teacher
