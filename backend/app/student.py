"""Schüler-Flow: Login (Klassen-Code + Pseudonym), Aufgabenliste, Abgaben.

Enthält sowohl die JSON-API (von luka.js/Frontend genutzt) als auch die
server-gerenderten Seiten (Login, Aufgabenliste).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from .auth import (
    COOKIE_NAME,
    clear_session,
    create_session,
    get_current_student,
    get_optional_student,
)
from .database import get_session
from .models import Assignment, Class, Student, Submission, Task
from .security import MIN_PASSWORD_LENGTH, hash_password, verify_password
from .discovery import read_task_html
from .render import render_task_page
from .templating import templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _assigned_tasks(db: Session, class_id: int) -> list[Task]:
    """Alle aktiv freigeschalteten Aufgaben einer Klasse."""
    stmt = (
        select(Task)
        .join(Assignment, Assignment.task_slug == Task.slug)
        .where(Assignment.class_id == class_id, Assignment.active == True)  # noqa: E712
    )
    return list(db.exec(stmt).all())


def _is_assigned(db: Session, class_id: int, slug: str) -> bool:
    stmt = select(Assignment).where(
        Assignment.class_id == class_id,
        Assignment.task_slug == slug,
        Assignment.active == True,  # noqa: E712
    )
    return db.exec(stmt).first() is not None


# ---------------------------------------------------------------------------
# JSON-API
# ---------------------------------------------------------------------------

class JoinStatusRequest(BaseModel):
    join_code: str
    display_name: str


class JoinRequest(BaseModel):
    join_code: str
    display_name: str
    password: str


def _lookup_class(db: Session, code: str) -> Class:
    klass = db.exec(
        select(Class).where(Class.join_code == code, Class.active == True)  # noqa: E712
    ).first()
    if klass is None:
        raise HTTPException(status_code=404, detail="Ungültiger oder inaktiver Klassen-Code")
    return klass


def _find_student(db: Session, class_id: int, name: str) -> Student | None:
    return db.exec(
        select(Student).where(
            Student.class_id == class_id,
            func.lower(Student.display_name) == name.lower(),
        )
    ).first()


@router.post("/api/join/status", tags=["student"])
def join_status(
    payload: JoinStatusRequest,
    db: Session = Depends(get_session),
) -> dict:
    """Prüft Code + Kürzel und meldet, ob ein Passwort *gesetzt* oder
    *eingegeben* werden muss.

    - mode "new": Schüler existiert noch nicht oder hat (nach Reset) kein
      Passwort → er muss jetzt ein neues vergeben.
    - mode "existing": Schüler hat ein Passwort → er muss es eingeben.
    """
    code = payload.join_code.strip().upper()
    name = payload.display_name.strip()
    if not code or not name:
        raise HTTPException(status_code=400, detail="Code und Kürzel erforderlich")

    klass = _lookup_class(db, code)
    student = _find_student(db, klass.id, name)
    mode = "existing" if (student and student.password_hash) else "new"
    return {"mode": mode, "class": klass.name}


@router.post("/api/join", tags=["student"])
def join(
    payload: JoinRequest,
    response: Response,
    db: Session = Depends(get_session),
) -> dict:
    """Login per Klassen-Code + Kürzel + Passwort.

    Neuer Schüler oder zurückgesetztes Passwort: das übergebene Passwort wird als
    neues Passwort gesetzt. Sonst wird das Passwort geprüft.
    """
    code = payload.join_code.strip().upper()
    name = payload.display_name.strip()
    password = payload.password
    if not code or not name:
        raise HTTPException(status_code=400, detail="Code und Kürzel erforderlich")

    klass = _lookup_class(db, code)
    student = _find_student(db, klass.id, name)

    if student is not None and student.password_hash:
        # Bestehendes Passwort prüfen.
        if not verify_password(student.password_hash, password):
            raise HTTPException(status_code=401, detail="Falsches Passwort")
    else:
        # Neues Passwort vergeben (neuer Schüler oder nach Admin-Reset).
        if len(password) < MIN_PASSWORD_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben",
            )
        if student is None:
            student = Student(class_id=klass.id, display_name=name)
        student.password_hash = hash_password(password)
        db.add(student)
        db.commit()
        db.refresh(student)

    create_session(db, student.id, response)
    return {"student_id": student.id, "display_name": student.display_name, "class": klass.name}


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/password", tags=["student"])
def change_password(
    payload: PasswordChangeRequest,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_session),
) -> dict:
    """Schüler ändert sein eigenes Passwort."""
    if not student.password_hash or not verify_password(
        student.password_hash, payload.current_password
    ):
        raise HTTPException(status_code=401, detail="Aktuelles Passwort ist falsch")
    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Neues Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben",
        )
    student.password_hash = hash_password(payload.new_password)
    db.add(student)
    db.commit()
    return {"ok": True}


@router.post("/api/logout", tags=["student"])
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> dict:
    clear_session(db, request.cookies.get(COOKIE_NAME), response)
    return {"ok": True}


@router.get("/api/me", tags=["student"])
def me(student: Student = Depends(get_current_student)) -> dict:
    return {"id": student.id, "display_name": student.display_name, "class_id": student.class_id}


@router.get("/api/tasks", tags=["student"])
def list_tasks(
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_session),
) -> list[dict]:
    """Für die Klasse des Schülers freigeschaltete Aufgaben."""
    tasks = _assigned_tasks(db, student.class_id)
    submitted = {
        row for row in db.exec(
            select(Submission.task_slug)
            .where(Submission.student_id == student.id)
            .distinct()
        ).all()
    }
    return [
        {"slug": t.slug, "title": t.title, "subject": t.subject, "submitted": t.slug in submitted}
        for t in tasks
    ]


class SubmissionRequest(BaseModel):
    slug: str
    answers: dict


@router.post("/api/submissions", tags=["student"])
def create_submission(
    payload: SubmissionRequest,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_session),
) -> dict:
    """Speichert eine (neue) Abgabe. Beliebig oft wiederholbar."""
    if db.get(Task, payload.slug) is None:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")
    if not _is_assigned(db, student.class_id, payload.slug):
        raise HTTPException(status_code=403, detail="Aufgabe nicht freigeschaltet")

    submission = Submission(
        student_id=student.id,
        task_slug=payload.slug,
        answers_json=json.dumps(payload.answers, ensure_ascii=False),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"id": submission.id, "submitted_at": submission.submitted_at.isoformat()}


@router.get("/api/submissions/{slug}", tags=["student"])
def latest_submission(
    slug: str,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_session),
) -> dict:
    """Letzte Abgabe des Schülers zu einer Aufgabe (zum Vorausfüllen)."""
    stmt = (
        select(Submission)
        .where(Submission.student_id == student.id, Submission.task_slug == slug)
        .order_by(Submission.submitted_at.desc())
    )
    submission = db.exec(stmt).first()
    if submission is None:
        return {"answers": None}
    return {
        "answers": json.loads(submission.answers_json),
        "submitted_at": submission.submitted_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Server-gerenderte Seiten
# ---------------------------------------------------------------------------

@router.get("/api/tasks/{slug}/html", tags=["student"], response_class=HTMLResponse)
def get_task_html(
    slug: str,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_session),
):
    """Liefert die Aufgaben-HTML (ohne Lösungen) für das React-Frontend."""
    task = db.get(Task, slug)
    raw_html = read_task_html(slug)
    if task is None or raw_html is None:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")
    if not _is_assigned(db, student.class_id, slug):
        raise HTTPException(status_code=403, detail="Aufgabe nicht freigeschaltet")
    return HTMLResponse(render_task_page(slug, task.title, raw_html))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(
    request: Request,
    student: Student | None = Depends(get_optional_student),
    code: str | None = None,
):
    if student is not None:
        return RedirectResponse(url="/aufgaben", status_code=303)
    # Per QR-Code vorbelegter Klassen-Code (?code=...).
    prefill = (code or "").strip().upper()
    return templates.TemplateResponse(request, "login.html", {"prefill_code": prefill})


@router.get("/aufgaben", response_class=HTMLResponse, include_in_schema=False)
def tasks_page(
    request: Request,
    student: Student | None = Depends(get_optional_student),
    db: Session = Depends(get_session),
):
    if student is None:
        return RedirectResponse(url="/", status_code=303)
    tasks = _assigned_tasks(db, student.class_id)

    # Slugs, zu denen der Schüler bereits (mindestens) eine Abgabe hat.
    submitted = {
        row for row in db.exec(
            select(Submission.task_slug)
            .where(Submission.student_id == student.id)
            .distinct()
        ).all()
    }
    task_list = [
        {
            "slug": t.slug,
            "title": t.title,
            "subject": t.subject,
            "submitted": t.slug in submitted,
        }
        for t in tasks
    ]
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {"student": student, "tasks": task_list},
    )


@router.get("/passwort", response_class=HTMLResponse, include_in_schema=False)
def password_page(
    request: Request,
    student: Student | None = Depends(get_optional_student),
):
    if student is None:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "password.html", {"student": student})
