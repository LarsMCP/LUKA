"""Admin-/Lehrer-Bereich: Login, Klassenverwaltung, Freischaltungen, Ergebnisse.

Server-gerenderte Seiten mit Formular-Posts (redirect-after-post). Der Zugriff
ist durch die Lehrer-Session geschützt.
"""
from __future__ import annotations

import csv
import io
import json
import secrets

import segno
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlmodel import Session, select

from .admin_auth import (
    ADMIN_COOKIE,
    clear_admin_session,
    create_admin_session,
    get_optional_teacher,
    verify_password,
)
from .database import get_session
from .discovery import scan_tasks
from .models import Assignment, Class, SessionToken, Student, Submission, Task, Teacher
from .templating import templates

router = APIRouter(prefix="/admin", tags=["admin"])

# Ähnlich aussehende Zeichen (0/O, 1/I) vermeiden.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _generate_join_code(db: Session, length: int = 6) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if db.exec(select(Class).where(Class.join_code == code)).first() is None:
            return code


def _login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=303)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
):
    if teacher is not None:
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(request, "admin_login.html", {"error": False})


@router.post("/login", include_in_schema=False)
def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    teacher = db.exec(select(Teacher).where(Teacher.username == username)).first()
    if teacher is None or not verify_password(teacher.password_hash, password):
        return templates.TemplateResponse(
            request, "admin_login.html", {"error": True}, status_code=401
        )
    redirect = RedirectResponse(url="/admin", status_code=303)
    create_admin_session(db, teacher.id, redirect)
    return redirect


@router.post("/logout", include_in_schema=False)
def logout(
    request: Request,
    db: Session = Depends(get_session),
):
    redirect = _login_redirect()
    clear_admin_session(db, request.cookies.get(ADMIN_COOKIE), redirect)
    return redirect


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse, include_in_schema=False)
def dashboard(
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        return _login_redirect()
    counts = {
        "classes": len(db.exec(select(Class)).all()),
        "tasks": len(db.exec(select(Task)).all()),
        "students": len(db.exec(select(Student)).all()),
        "submissions": len(db.exec(select(Submission)).all()),
    }
    return templates.TemplateResponse(
        request, "admin_dashboard.html", {"teacher": teacher, "counts": counts}
    )


# ---------------------------------------------------------------------------
# Klassen + Freischaltungen
# ---------------------------------------------------------------------------

@router.get("/classes", response_class=HTMLResponse, include_in_schema=False)
def classes_page(
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        return _login_redirect()

    classes = db.exec(select(Class)).all()
    tasks = db.exec(select(Task)).all()
    # Freischaltungen je Klasse als Set von Slugs.
    assignments: dict[int, set[str]] = {}
    for a in db.exec(select(Assignment).where(Assignment.active == True)).all():  # noqa: E712
        assignments.setdefault(a.class_id, set()).add(a.task_slug)

    return templates.TemplateResponse(
        request,
        "admin_classes.html",
        {"teacher": teacher, "classes": classes, "tasks": tasks, "assignments": assignments},
    )


@router.post("/classes", include_in_schema=False)
def create_class(
    teacher: Teacher | None = Depends(get_optional_teacher),
    name: str = Form(...),
    db: Session = Depends(get_session),
):
    if teacher is None:
        return _login_redirect()
    name = name.strip()
    if name:
        klass = Class(
            name=name,
            join_code=_generate_join_code(db),
            owner_teacher_id=teacher.id,
        )
        db.add(klass)
        db.commit()
    return RedirectResponse(url="/admin/classes", status_code=303)


@router.post("/classes/{class_id}/toggle", include_in_schema=False)
def toggle_class(
    class_id: int,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        return _login_redirect()
    klass = db.get(Class, class_id)
    if klass is not None:
        klass.active = not klass.active
        db.add(klass)
        db.commit()
    return RedirectResponse(url="/admin/classes", status_code=303)


@router.post("/classes/{class_id}/delete", include_in_schema=False)
def delete_class(
    class_id: int,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    """Löscht eine Klasse inkl. Schüler, Abgaben, Sessions und Freischaltungen."""
    if teacher is None:
        return _login_redirect()

    klass = db.get(Class, class_id)
    if klass is not None:
        students = db.exec(select(Student).where(Student.class_id == class_id)).all()
        for student in students:
            for sub in db.exec(
                select(Submission).where(Submission.student_id == student.id)
            ).all():
                db.delete(sub)
            for sess in db.exec(
                select(SessionToken).where(SessionToken.student_id == student.id)
            ).all():
                db.delete(sess)
            db.delete(student)
        for assignment in db.exec(
            select(Assignment).where(Assignment.class_id == class_id)
        ).all():
            db.delete(assignment)
        db.delete(klass)
        db.commit()

    return RedirectResponse(url="/admin/classes", status_code=303)


def _join_url(request: Request, join_code: str) -> str:
    """Beitritts-URL mit vorbelegtem Klassen-Code (für QR-Code)."""
    return f"{str(request.base_url)}?code={join_code}"


@router.get("/classes/{class_id}/qr.svg", include_in_schema=False)
def class_qr_svg(
    class_id: int,
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    """QR-Code (SVG) mit der Beitritts-URL der Klasse."""
    if teacher is None:
        return _login_redirect()
    klass = db.get(Class, class_id)
    if klass is None:
        return Response(status_code=404)

    buffer = io.BytesIO()
    segno.make(_join_url(request, klass.join_code), error="m").save(
        buffer, kind="svg", scale=6, border=2
    )
    return Response(content=buffer.getvalue(), media_type="image/svg+xml")


@router.get("/classes/{class_id}/qr", response_class=HTMLResponse, include_in_schema=False)
def class_qr_page(
    class_id: int,
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    """Druckbare QR-Code-Seite zum Aushängen/Projizieren."""
    if teacher is None:
        return _login_redirect()
    klass = db.get(Class, class_id)
    if klass is None:
        return RedirectResponse(url="/admin/classes", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin_qr.html",
        {
            "teacher": teacher,
            "klass": klass,
            "join_url": _join_url(request, klass.join_code),
        },
    )


@router.post("/assignments", include_in_schema=False)
def update_assignment(
    teacher: Teacher | None = Depends(get_optional_teacher),
    class_id: int = Form(...),
    task_slug: str = Form(...),
    action: str = Form(...),  # "assign" | "unassign"
    db: Session = Depends(get_session),
):
    if teacher is None:
        return _login_redirect()

    existing = db.exec(
        select(Assignment).where(
            Assignment.class_id == class_id, Assignment.task_slug == task_slug
        )
    ).first()

    if action == "assign":
        if existing is None:
            db.add(Assignment(class_id=class_id, task_slug=task_slug, active=True))
        else:
            existing.active = True
            db.add(existing)
        db.commit()
    elif action == "unassign" and existing is not None:
        existing.active = False
        db.add(existing)
        db.commit()

    return RedirectResponse(url="/admin/classes", status_code=303)


# ---------------------------------------------------------------------------
# Aufgaben
# ---------------------------------------------------------------------------

@router.get("/tasks", response_class=HTMLResponse, include_in_schema=False)
def tasks_page(
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
    rescanned: int = 0,
):
    if teacher is None:
        return _login_redirect()
    tasks = db.exec(select(Task)).all()
    return templates.TemplateResponse(
        request, "admin_tasks.html", {"teacher": teacher, "tasks": tasks, "rescanned": rescanned}
    )


@router.post("/tasks/rescan", include_in_schema=False)
def rescan(teacher: Teacher | None = Depends(get_optional_teacher)):
    if teacher is None:
        return _login_redirect()
    scan_tasks()
    return RedirectResponse(url="/admin/tasks?rescanned=1", status_code=303)


# ---------------------------------------------------------------------------
# Schüler
# ---------------------------------------------------------------------------

@router.get("/students", response_class=HTMLResponse, include_in_schema=False)
def students_page(
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
    class_id: int | None = None,
    error: str | None = None,
):
    if teacher is None:
        return _login_redirect()

    classes = db.exec(select(Class)).all()
    students: list[dict] = []
    if class_id is not None:
        stmt = (
            select(Student)
            .where(Student.class_id == class_id)
            .order_by(func.lower(Student.display_name))
        )
        for s in db.exec(stmt).all():
            count = len(
                db.exec(select(Submission).where(Submission.student_id == s.id)).all()
            )
            students.append({
                "id": s.id,
                "display_name": s.display_name,
                "submissions": count,
                "has_password": bool(s.password_hash),
            })

    return templates.TemplateResponse(
        request,
        "admin_students.html",
        {
            "teacher": teacher,
            "classes": classes,
            "students": students,
            "sel_class": class_id,
            "error": error,
        },
    )


@router.post("/students/{student_id}/rename", include_in_schema=False)
def student_rename(
    student_id: int,
    teacher: Teacher | None = Depends(get_optional_teacher),
    display_name: str = Form(...),
    db: Session = Depends(get_session),
):
    if teacher is None:
        return _login_redirect()

    student = db.get(Student, student_id)
    if student is None:
        return RedirectResponse(url="/admin/students", status_code=303)

    new_name = display_name.strip()
    back = f"/admin/students?class_id={student.class_id}"
    if not new_name:
        return RedirectResponse(url=f"{back}&error=empty", status_code=303)

    # Namenskollision (case-insensitiv) mit anderem Schüler derselben Klasse?
    collision = db.exec(
        select(Student).where(
            Student.class_id == student.class_id,
            func.lower(Student.display_name) == new_name.lower(),
            Student.id != student.id,
        )
    ).first()
    if collision is not None:
        return RedirectResponse(url=f"{back}&error=collision", status_code=303)

    student.display_name = new_name
    db.add(student)
    db.commit()
    return RedirectResponse(url=back, status_code=303)


@router.post("/students/{student_id}/reset-password", include_in_schema=False)
def student_reset_password(
    student_id: int,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    """Setzt das Schüler-Passwort zurück (Hash = None).

    Beim nächsten Login muss der Schüler ein neues Passwort vergeben.
    """
    if teacher is None:
        return _login_redirect()

    student = db.get(Student, student_id)
    if student is None:
        return RedirectResponse(url="/admin/students", status_code=303)

    student.password_hash = None
    db.add(student)
    # Aktive Sessions beenden, damit der Reset sofort greift.
    for sess in db.exec(
        select(SessionToken).where(SessionToken.student_id == student_id)
    ).all():
        db.delete(sess)
    db.commit()
    return RedirectResponse(url=f"/admin/students?class_id={student.class_id}", status_code=303)


@router.post("/students/{student_id}/delete", include_in_schema=False)
def student_delete(
    student_id: int,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        return _login_redirect()

    student = db.get(Student, student_id)
    if student is None:
        return RedirectResponse(url="/admin/students", status_code=303)

    class_id = student.class_id
    # Zugehörige Abgaben und Sessions mitlöschen.
    for sub in db.exec(select(Submission).where(Submission.student_id == student_id)).all():
        db.delete(sub)
    for sess in db.exec(select(SessionToken).where(SessionToken.student_id == student_id)).all():
        db.delete(sess)
    db.delete(student)
    db.commit()
    return RedirectResponse(url=f"/admin/students?class_id={class_id}", status_code=303)


# ---------------------------------------------------------------------------
# Ergebnisse
# ---------------------------------------------------------------------------

def _latest_submissions(db: Session, class_id: int, task_slug: str) -> list[dict]:
    """Neueste Abgabe je Schüler der Klasse für eine Aufgabe."""
    students = db.exec(select(Student).where(Student.class_id == class_id)).all()
    rows: list[dict] = []
    for student in students:
        sub = db.exec(
            select(Submission)
            .where(
                Submission.student_id == student.id,
                Submission.task_slug == task_slug,
            )
            .order_by(Submission.submitted_at.desc())
        ).first()
        rows.append(
            {
                "student": student.display_name,
                "submitted_at": sub.submitted_at if sub else None,
                "answers": json.loads(sub.answers_json) if sub else None,
            }
        )
    return rows


def _answer_keys(rows: list[dict]) -> list[str]:
    keys: set[str] = set()
    for r in rows:
        if r["answers"]:
            keys.update(r["answers"].keys())
    return sorted(keys)


def _format_answer(value) -> str:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return "" if value is None else str(value)


@router.get("/submissions", response_class=HTMLResponse, include_in_schema=False)
def submissions_page(
    request: Request,
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
    class_id: int | None = None,
    task_slug: str | None = None,
):
    if teacher is None:
        return _login_redirect()

    classes = db.exec(select(Class)).all()
    tasks: list[Task] = []
    rows: list[dict] = []
    keys: list[str] = []

    if class_id is not None:
        # Nur der Klasse freigeschaltete Aufgaben zur Auswahl.
        stmt = (
            select(Task)
            .join(Assignment, Assignment.task_slug == Task.slug)
            .where(Assignment.class_id == class_id, Assignment.active == True)  # noqa: E712
        )
        tasks = list(db.exec(stmt).all())

    if class_id is not None and task_slug:
        rows = _latest_submissions(db, class_id, task_slug)
        keys = _answer_keys(rows)

    return templates.TemplateResponse(
        request,
        "admin_submissions.html",
        {
            "teacher": teacher,
            "classes": classes,
            "tasks": tasks,
            "rows": rows,
            "keys": keys,
            "sel_class": class_id,
            "sel_task": task_slug,
            "format_answer": _format_answer,
        },
    )


@router.get("/submissions.csv", include_in_schema=False)
def submissions_csv(
    teacher: Teacher | None = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
    class_id: int | None = None,
    task_slug: str | None = None,
):
    if teacher is None:
        return _login_redirect()
    if class_id is None or not task_slug:
        return RedirectResponse(url="/admin/submissions", status_code=303)

    rows = _latest_submissions(db, class_id, task_slug)
    keys = _answer_keys(rows)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Anzeigename", "Abgabe (UTC)"] + keys)
    for r in rows:
        answers = r["answers"] or {}
        writer.writerow(
            [
                r["student"],
                r["submitted_at"].isoformat() if r["submitted_at"] else "",
            ]
            + [_format_answer(answers.get(k)) for k in keys]
        )

    filename = f"ergebnisse_{task_slug}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
