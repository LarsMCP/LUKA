"""Admin-/Lehrer-Bereich: Login, Klassenverwaltung, Freischaltungen, Ergebnisse.

Server-gerenderte Seiten mit Formular-Posts (redirect-after-post). Der Zugriff
ist durch die Lehrer-Session geschützt.
"""
from __future__ import annotations

import csv
import io
import json
import secrets
from datetime import datetime, timedelta

import segno
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlmodel import Session, select

from .admin_auth import (
    ADMIN_COOKIE,
    can_access_class,
    clear_admin_session,
    create_admin_session,
    get_optional_teacher,
    require_admin,
    verify_password,
)
from .database import get_session
from .discovery import scan_tasks
from .models import (
    Assignment,
    Class,
    SessionToken,
    Student,
    Submission,
    Task,
    Teacher,
    TeacherInvite,
)
from .security import hash_password
from .templating import templates

INVITE_TTL = timedelta(days=7)

router = APIRouter(prefix="/admin", tags=["admin"])

# Ähnlich aussehende Zeichen (0/O, 1/I) vermeiden.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _generate_join_code(db: Session, length: int = 6) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if db.exec(select(Class).where(Class.join_code == code)).first() is None:
            return code


def _generate_invite_code(db: Session, length: int = 10) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if db.exec(select(TeacherInvite).where(TeacherInvite.code == code)).first() is None:
            return code


def _login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=303)


def _visible_classes(db: Session, teacher: Teacher) -> list[Class]:
    """Klassen, die der Lehrer sehen darf: admin = alle, teacher = nur eigene."""
    if teacher.role == "admin":
        return list(db.exec(select(Class)).all())
    return list(db.exec(select(Class).where(Class.owner_teacher_id == teacher.id)).all())


def _get_accessible_class(db: Session, teacher: Teacher, class_id: int | None) -> Class | None:
    """Lädt eine Klasse nur, wenn der Lehrer darauf zugreifen darf."""
    if class_id is None:
        return None
    klass = db.get(Class, class_id)
    if klass is None or not can_access_class(teacher, klass):
        return None
    return klass


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
    classes = _visible_classes(db, teacher)
    class_ids = [c.id for c in classes]
    students = (
        db.exec(select(Student)).all()
        if teacher.role == "admin"
        else db.exec(select(Student).where(Student.class_id.in_(class_ids))).all()
    )
    student_ids = [s.id for s in students]
    submissions = (
        db.exec(select(Submission)).all()
        if teacher.role == "admin"
        else db.exec(select(Submission).where(Submission.student_id.in_(student_ids))).all()
    )
    counts = {
        "classes": len(classes),
        "tasks": len(db.exec(select(Task)).all()),
        "students": len(students),
        "submissions": len(submissions),
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

    classes = _visible_classes(db, teacher)
    tasks = db.exec(select(Task)).all()
    # Freischaltungen je Klasse als Set von Slugs.
    assignments: dict[int, set[str]] = {}
    class_ids = {c.id for c in classes}
    for a in db.exec(select(Assignment).where(Assignment.active == True)).all():  # noqa: E712
        if a.class_id in class_ids:
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
    klass = _get_accessible_class(db, teacher, class_id)
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

    klass = _get_accessible_class(db, teacher, class_id)
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
    klass = _get_accessible_class(db, teacher, class_id)
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
    klass = _get_accessible_class(db, teacher, class_id)
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
    if _get_accessible_class(db, teacher, class_id) is None:
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

    classes = _visible_classes(db, teacher)
    accessible_class = _get_accessible_class(db, teacher, class_id)
    students: list[dict] = []
    if accessible_class is not None:
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
            "sel_class": accessible_class.id if accessible_class else None,
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
    if student is None or _get_accessible_class(db, teacher, student.class_id) is None:
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
    if student is None or _get_accessible_class(db, teacher, student.class_id) is None:
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
    if student is None or _get_accessible_class(db, teacher, student.class_id) is None:
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

    classes = _visible_classes(db, teacher)
    accessible_class = _get_accessible_class(db, teacher, class_id)
    tasks: list[Task] = []
    rows: list[dict] = []
    keys: list[str] = []

    if accessible_class is not None:
        # Nur der Klasse freigeschaltete Aufgaben zur Auswahl.
        stmt = (
            select(Task)
            .join(Assignment, Assignment.task_slug == Task.slug)
            .where(Assignment.class_id == class_id, Assignment.active == True)  # noqa: E712
        )
        tasks = list(db.exec(stmt).all())

    if accessible_class is not None and task_slug:
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
            "sel_class": accessible_class.id if accessible_class else None,
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
    if _get_accessible_class(db, teacher, class_id) is None or not task_slug:
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


# ---------------------------------------------------------------------------
# Lehrerverwaltung (nur Admins) + Einladungscode-Registrierung (öffentlich)
# ---------------------------------------------------------------------------

@router.get("/teachers", response_class=HTMLResponse, include_in_schema=False)
def teachers_page(
    request: Request,
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    teachers = db.exec(select(Teacher).order_by(Teacher.created_at)).all()
    now = datetime.utcnow()
    invites = db.exec(
        select(TeacherInvite)
        .where(TeacherInvite.used_at == None)  # noqa: E711
        .order_by(TeacherInvite.created_at.desc())
    ).all()
    admin_count = len([t for t in teachers if t.role == "admin"])
    return templates.TemplateResponse(
        request,
        "admin_teachers.html",
        {
            "teacher": teacher,
            "teachers": teachers,
            "invites": invites,
            "now": now,
            "admin_count": admin_count,
            "join_base_url": str(request.base_url).rstrip("/") + "/admin/join",
        },
    )


@router.post("/teachers/invite", include_in_schema=False)
def create_teacher_invite(
    teacher: Teacher = Depends(require_admin),
    role: str = Form("teacher"),
    db: Session = Depends(get_session),
):
    role = role if role in ("admin", "teacher") else "teacher"
    invite = TeacherInvite(
        code=_generate_invite_code(db),
        role=role,
        created_by_teacher_id=teacher.id,
        expires_at=datetime.utcnow() + INVITE_TTL,
    )
    db.add(invite)
    db.commit()
    return RedirectResponse(url="/admin/teachers", status_code=303)


@router.post("/teachers/invites/{invite_id}/revoke", include_in_schema=False)
def revoke_teacher_invite(
    invite_id: int,
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    invite = db.get(TeacherInvite, invite_id)
    if invite is not None and invite.used_at is None:
        db.delete(invite)
        db.commit()
    return RedirectResponse(url="/admin/teachers", status_code=303)


@router.post("/teachers/{teacher_id}/delete", include_in_schema=False)
def delete_teacher(
    teacher_id: int,
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    target = db.get(Teacher, teacher_id)
    if target is None:
        return RedirectResponse(url="/admin/teachers", status_code=303)
    if target.id == teacher.id:
        return RedirectResponse(url="/admin/teachers?error=self", status_code=303)
    if target.role == "admin":
        admin_count = len(
            db.exec(select(Teacher).where(Teacher.role == "admin")).all()
        )
        if admin_count <= 1:
            return RedirectResponse(url="/admin/teachers?error=last_admin", status_code=303)

    # Klassen des gelöschten Lehrers nicht verwaisen lassen: dem löschenden
    # Admin zuordnen, damit sie weiterhin verwaltbar bleiben.
    for klass in db.exec(select(Class).where(Class.owner_teacher_id == target.id)).all():
        klass.owner_teacher_id = teacher.id
        db.add(klass)

    db.delete(target)
    db.commit()
    return RedirectResponse(url="/admin/teachers", status_code=303)


@router.get("/join", response_class=HTMLResponse, include_in_schema=False)
def teacher_join_page(request: Request, code: str = ""):
    """Öffentliche Registrierungsseite für neue Lehrer via Einladungscode."""
    return templates.TemplateResponse(
        request, "admin_join.html", {"prefill_code": code, "error": None}
    )


@router.post("/join", include_in_schema=False)
def teacher_join_submit(
    request: Request,
    code: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_session),
):
    def fail(message: str, status_code: int = 400):
        return templates.TemplateResponse(
            request,
            "admin_join.html",
            {"prefill_code": code, "error": message},
            status_code=status_code,
        )

    invite = db.exec(select(TeacherInvite).where(TeacherInvite.code == code.strip().upper())).first()
    if invite is None:
        return fail("Ungültiger Einladungscode.")
    if invite.used_at is not None:
        return fail("Dieser Einladungscode wurde bereits verwendet.")
    if invite.expires_at < datetime.utcnow():
        return fail("Dieser Einladungscode ist abgelaufen.")

    username = username.strip()
    if not username:
        return fail("Bitte einen Benutzernamen angeben.")
    if len(password) < 8:
        return fail("Das Passwort sollte mindestens 8 Zeichen haben.")
    if password != password_confirm:
        return fail("Die Passwörter stimmen nicht überein.")
    if db.exec(select(Teacher).where(Teacher.username == username)).first() is not None:
        return fail("Dieser Benutzername ist bereits vergeben.")

    new_teacher = Teacher(
        username=username,
        password_hash=hash_password(password),
        role=invite.role,
    )
    db.add(new_teacher)
    db.flush()

    invite.used_at = datetime.utcnow()
    invite.used_by_teacher_id = new_teacher.id
    db.add(invite)
    db.commit()
    db.refresh(new_teacher)

    redirect = RedirectResponse(url="/admin", status_code=303)
    create_admin_session(db, new_teacher.id, redirect)
    return redirect
