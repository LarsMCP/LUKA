"""JSON-API-Endpunkte für den Admin-Bereich (React-Frontend).

Diese Routen ergänzen die bestehenden HTML-Routen in admin.py und liefern
JSON-Antworten für die React-SPA.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import func
from sqlmodel import Session, select

from .admin_auth import (
    ADMIN_COOKIE,
    clear_admin_session,
    create_admin_session,
    get_optional_teacher,
    require_admin,
    verify_password,
)
from .database import get_session
from .discovery import read_task_html, scan_tasks
from .models import (
    Assignment,
    Class,
    Student,
    Submission,
    Task,
    Teacher,
    TeacherInvite,
)
from . import task_repo
from .render import render_task_page

import io
import segno

router = APIRouter(prefix="/api/admin", tags=["admin-api"])


# ---------------------------------------------------------------------------
# Hilfsfunktionen (spiegeln admin.py, aber für JSON-Antworten)
# ---------------------------------------------------------------------------

def _visible_classes(db: Session, teacher: Teacher) -> list[Class]:
    if teacher.role == "admin":
        return list(db.exec(select(Class)).all())
    return list(db.exec(select(Class).where(Class.owner_teacher_id == teacher.id)).all())


def _get_accessible_class(db: Session, teacher: Teacher, class_id: int | None) -> Class | None:
    if class_id is None:
        return None
    klass = db.get(Class, class_id)
    if klass is None:
        return None
    if teacher.role == "admin":
        return klass
    if klass.owner_teacher_id == teacher.id:
        return klass
    return None


def _pretty_key(key: str) -> str:
    import re
    m = re.match(r"^step(\d+)_(.+)$", key)
    if m:
        return f"Schritt {m.group(1)}: {m.group(2).replace('_', ' ').title()}"
    return key


def _sort_keys_natural(keys: list[str]) -> list[str]:
    import re
    def sort_key(k: str):
        m = re.match(r"^step(\d+)_(.*)$", k)
        if m:
            return (int(m.group(1)), m.group(2))
        m = re.match(r"^step(\d+)$", k)
        if m:
            return (int(m.group(1)), "")
        return (999, k)
    return sorted(keys, key=sort_key)


def _format_answer(value) -> str:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return "" if value is None else str(value)


def _evaluate_answers(solutions: dict, answers: dict) -> dict:
    per_field: dict[str, str] = {}
    correct = wrong = empty = 0
    for field, sol in solutions.items():
        expected = sol.get("answer")
        sol_type = sol.get("type")
        student_val = answers.get(field)
        if student_val is None or student_val == "" or student_val == []:
            per_field[field] = "empty"
            empty += 1
            continue
        if sol_type == "numeric":
            try:
                if abs(float(student_val) - float(expected)) < 0.01:
                    per_field[field] = "correct"
                    correct += 1
                else:
                    per_field[field] = "wrong"
                    wrong += 1
            except (ValueError, TypeError):
                per_field[field] = "wrong"
                wrong += 1
            continue
        if sol_type == "checkbox" or isinstance(expected, list):
            expected_set = set(str(v) for v in expected)
            if isinstance(student_val, list):
                student_set = set(str(v) for v in student_val)
            else:
                student_set = {str(student_val)}
            if student_set == expected_set:
                per_field[field] = "correct"
                correct += 1
            else:
                per_field[field] = "wrong"
                wrong += 1
            continue
        if str(student_val).strip().lower() == str(expected).strip().lower():
            per_field[field] = "correct"
            correct += 1
        else:
            per_field[field] = "wrong"
            wrong += 1
    return {
        "total": len(solutions),
        "correct": correct,
        "wrong": wrong,
        "empty": empty,
        "per_field": per_field,
    }


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@router.post("/login")
def api_admin_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    teacher = db.exec(select(Teacher).where(Teacher.username == username)).first()
    if teacher is None or not verify_password(teacher.password_hash, password):
        raise HTTPException(status_code=401, detail="Falscher Benutzername oder Passwort")
    create_admin_session(db, teacher.id, response)
    return {"ok": True}


@router.post("/logout")
def api_admin_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
):
    clear_admin_session(db, request.cookies.get(ADMIN_COOKIE), response)
    return {"ok": True}


@router.get("/me")
def api_admin_me(
    teacher: Teacher | None = Depends(get_optional_teacher),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    return {
        "id": teacher.id,
        "username": teacher.username,
        "role": teacher.role,
        "created_at": teacher.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def api_dashboard(
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
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
    return {
        "classes": len(classes),
        "tasks": len(db.exec(select(Task)).all()),
        "students": len(students),
        "submissions": len(submissions),
    }


# ---------------------------------------------------------------------------
# Klassen
# ---------------------------------------------------------------------------

@router.get("/classes")
def api_list_classes(
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    classes = _visible_classes(db, teacher)
    return [
        {
            "id": c.id,
            "name": c.name,
            "join_code": c.join_code,
            "owner_teacher_id": c.owner_teacher_id,
            "active": c.active,
            "created_at": c.created_at.isoformat(),
        }
        for c in classes
    ]


@router.post("/classes")
def api_create_class(
    teacher: Teacher = Depends(get_optional_teacher),
    name: str = Form(...),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    import secrets as _secrets
    _ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "".join(_secrets.choice(_ALPHABET) for _ in range(6))
        if db.exec(select(Class).where(Class.join_code == code)).first() is None:
            break
    klass = Class(name=name.strip(), join_code=code, owner_teacher_id=teacher.id)
    db.add(klass)
    db.commit()
    db.refresh(klass)
    return {
        "id": klass.id,
        "name": klass.name,
        "join_code": klass.join_code,
        "owner_teacher_id": klass.owner_teacher_id,
        "active": klass.active,
        "created_at": klass.created_at.isoformat(),
    }


@router.post("/classes/{class_id}/toggle")
def api_toggle_class(
    class_id: int,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    klass = _get_accessible_class(db, teacher, class_id)
    if klass is None:
        raise HTTPException(status_code=404)
    klass.active = not klass.active
    db.add(klass)
    db.commit()
    return {"ok": True}


@router.post("/classes/{class_id}/delete")
def api_delete_class(
    class_id: int,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    klass = _get_accessible_class(db, teacher, class_id)
    if klass is not None:
        students = db.exec(select(Student).where(Student.class_id == class_id)).all()
        for student in students:
            for sub in db.exec(select(Submission).where(Submission.student_id == student.id)).all():
                db.delete(sub)
            db.delete(student)
        for assignment in db.exec(select(Assignment).where(Assignment.class_id == class_id)).all():
            db.delete(assignment)
        db.delete(klass)
        db.commit()
    return {"ok": True}


@router.get("/classes/{class_id}/qr.svg")
def api_class_qr_svg(
    class_id: int,
    request: Request,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    """QR-Code (SVG) mit der Beitritts-URL der Klasse."""
    if teacher is None:
        raise HTTPException(status_code=401)
    klass = _get_accessible_class(db, teacher, class_id)
    if klass is None:
        raise HTTPException(status_code=404)
    join_url = f"{str(request.base_url)}?code={klass.join_code}"
    buffer = io.BytesIO()
    segno.make(join_url, error="m").save(buffer, kind="svg", scale=6, border=2)
    return Response(content=buffer.getvalue(), media_type="image/svg+xml")


# ---------------------------------------------------------------------------
# Schüler
# ---------------------------------------------------------------------------

@router.get("/students")
def api_list_students(
    class_id: int,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    if _get_accessible_class(db, teacher, class_id) is None:
        raise HTTPException(status_code=403)
    students = db.exec(
        select(Student).where(Student.class_id == class_id).order_by(func.lower(Student.display_name))
    ).all()
    result = []
    for s in students:
        count = len(db.exec(select(Submission).where(Submission.student_id == s.id)).all())
        result.append({
            "id": s.id,
            "display_name": s.display_name,
            "submissions": count,
            "has_password": bool(s.password_hash),
        })
    return result


@router.post("/students/{student_id}/rename")
def api_rename_student(
    student_id: int,
    display_name: str = Form(...),
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    student = db.get(Student, student_id)
    if student is None or _get_accessible_class(db, teacher, student.class_id) is None:
        raise HTTPException(status_code=404)
    new_name = display_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    collision = db.exec(
        select(Student).where(
            Student.class_id == student.class_id,
            func.lower(Student.display_name) == new_name.lower(),
            Student.id != student.id,
        )
    ).first()
    if collision is not None:
        raise HTTPException(status_code=400, detail="Name bereits vergeben")
    student.display_name = new_name
    db.add(student)
    db.commit()
    return {"ok": True}


@router.post("/students/{student_id}/reset-password")
def api_reset_password(
    student_id: int,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    student = db.get(Student, student_id)
    if student is None or _get_accessible_class(db, teacher, student.class_id) is None:
        raise HTTPException(status_code=404)
    student.password_hash = None
    db.add(student)
    from .models import SessionToken
    for sess in db.exec(select(SessionToken).where(SessionToken.student_id == student_id)).all():
        db.delete(sess)
    db.commit()
    return {"ok": True}


@router.post("/students/{student_id}/delete")
def api_delete_student(
    student_id: int,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    student = db.get(Student, student_id)
    if student is None or _get_accessible_class(db, teacher, student.class_id) is None:
        raise HTTPException(status_code=404)
    for sub in db.exec(select(Submission).where(Submission.student_id == student_id)).all():
        db.delete(sub)
    from .models import SessionToken
    for sess in db.exec(select(SessionToken).where(SessionToken.student_id == student_id)).all():
        db.delete(sess)
    db.delete(student)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Aufgaben
# ---------------------------------------------------------------------------

@router.get("/tasks")
def api_list_tasks(
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    tasks = db.exec(select(Task)).all()
    return [
        {
            "slug": t.slug,
            "title": t.title,
            "subject": t.subject,
            "hash": t.hash,
            "solutions_json": t.solutions_json,
            "discovered_at": t.discovered_at.isoformat(),
        }
        for t in tasks
    ]


@router.post("/tasks/rescan")
def api_rescan_tasks(
    teacher: Teacher = Depends(get_optional_teacher),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    scan_tasks()
    return {"ok": True}


@router.get("/tasks/repo")
def api_get_task_repo(
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    config = task_repo.get_config(db)
    if config is None:
        return None
    return {
        "id": config.id,
        "repo_url": config.repo_url,
        "branch": config.branch,
        "sync_interval_minutes": config.sync_interval_minutes,
        "last_synced_at": config.last_synced_at.isoformat() if config.last_synced_at else None,
        "last_sync_status": config.last_sync_status,
        "last_sync_error": config.last_sync_error,
    }


@router.post("/tasks/repo")
def api_save_task_repo(
    teacher: Teacher = Depends(require_admin),
    repo_url: str = Form(...),
    branch: str = Form("main"),
    sync_interval_minutes: int = Form(15),
    db: Session = Depends(get_session),
):
    task_repo.save_config(db, repo_url.strip(), branch.strip(), sync_interval_minutes)
    task_repo.sync(db)
    scan_tasks()
    return {"ok": True}


@router.post("/tasks/repo/sync")
def api_sync_task_repo(
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    task_repo.sync(db)
    scan_tasks()
    return {"ok": True}


@router.post("/tasks/repo/disconnect")
def api_disconnect_task_repo(
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    task_repo.disconnect(db)
    scan_tasks()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Abgaben / Ergebnisse
# ---------------------------------------------------------------------------

@router.get("/submissions")
def api_get_submissions(
    class_id: int,
    task_slug: str,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    if teacher is None:
        raise HTTPException(status_code=401)
    if _get_accessible_class(db, teacher, class_id) is None:
        raise HTTPException(status_code=403)

    students = db.exec(select(Student).where(Student.class_id == class_id)).all()
    rows = []
    for student in students:
        sub = db.exec(
            select(Submission)
            .where(Submission.student_id == student.id, Submission.task_slug == task_slug)
            .order_by(Submission.submitted_at.desc())
        ).first()
        rows.append({
            "student": student.display_name,
            "student_id": student.id,
            "submitted_at": sub.submitted_at.isoformat() if sub else None,
            "answers": json.loads(sub.answers_json) if sub else None,
        })

    keys_set: set[str] = set()
    for r in rows:
        if r["answers"]:
            keys_set.update(r["answers"].keys())
    keys = _sort_keys_natural(list(keys_set))
    pretty_keys = [_pretty_key(k) for k in keys]

    return {"rows": rows, "keys": keys, "pretty_keys": pretty_keys}


@router.get("/submissions.csv")
def api_submissions_csv(
    class_id: int,
    task_slug: str,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    """CSV-Export der Abgaben."""
    import csv
    if teacher is None:
        raise HTTPException(status_code=401)
    if _get_accessible_class(db, teacher, class_id) is None:
        raise HTTPException(status_code=403)

    students = db.exec(select(Student).where(Student.class_id == class_id)).all()
    rows = []
    for student in students:
        sub = db.exec(
            select(Submission)
            .where(Submission.student_id == student.id, Submission.task_slug == task_slug)
            .order_by(Submission.submitted_at.desc())
        ).first()
        rows.append({
            "student": student.display_name,
            "submitted_at": sub.submitted_at.isoformat() if sub else None,
            "answers": json.loads(sub.answers_json) if sub else None,
        })

    keys_set: set[str] = set()
    for r in rows:
        if r["answers"]:
            keys_set.update(r["answers"].keys())
    keys = _sort_keys_natural(list(keys_set))
    pretty_keys = [_pretty_key(k) for k in keys]

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Schüler", "Abgabe"] + pretty_keys)
    for r in rows:
        row_data = [r["student"], r["submitted_at"] or ""]
        for key in keys:
            row_data.append(_format_answer(r["answers"].get(key) if r["answers"] else None))
        writer.writerow(row_data)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=submissions_{task_slug}.csv"},
    )


@router.get("/submissions/view")
def api_submission_view(
    class_id: int,
    task_slug: str,
    student_id: int,
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
):
    """Liefert das vorbereitete HTML für die Lehrer-Ansicht."""
    if teacher is None:
        raise HTTPException(status_code=401)
    if _get_accessible_class(db, teacher, class_id) is None:
        raise HTTPException(status_code=403)

    student = db.get(Student, student_id)
    if student is None or student.class_id != class_id:
        raise HTTPException(status_code=404)

    task = db.get(Task, task_slug)
    if task is None:
        raise HTTPException(status_code=404)

    sub = db.exec(
        select(Submission)
        .where(Submission.student_id == student_id, Submission.task_slug == task_slug)
        .order_by(Submission.submitted_at.desc())
    ).first()
    answers = json.loads(sub.answers_json) if sub else {}

    raw_html = read_task_html(task_slug)
    if raw_html is None:
        raise HTTPException(status_code=404)

    answers_json = json.dumps(answers)
    extra_inject = """  <!-- Teacher-View -->
  <script>window.LUKA_STUDENT_ANSWERS = {answers_json};</script>
  <script>window.LUKA_TEACHER_VIEW = true;</script>
  <script>
  (function() {{
    var answers = window.LUKA_STUDENT_ANSWERS || {{}};
    window.LUKA = window.LUKA || {{}};
    window.LUKA.autoSave = function() {{}};
    window.unlock = function(n) {{ return; }};
    document.addEventListener('DOMContentLoaded', function() {{
      if (window.LUKA && window.LUKA.applyAnswers) {{
        window.LUKA.applyAnswers(answers);
      }}
      document.querySelectorAll('.step').forEach(function(s) {{
        s.style.display = 'block';
        s.classList.add('active');
      }});
      var pf = document.getElementById('progressFill');
      if (pf) pf.style.width = '100%';
      var pt = document.getElementById('progressText');
      if (pt) pt.textContent = 'Lehrer-Ansicht';
      var checkFns = ['checkStep1','checkStep2','checkStep4','checkStep5',
                      'checkStep6','checkStep7','checkStep8','checkStep9',
                      'checkStep10','checkStep11','checkStep12'];
      checkFns.forEach(function(fn) {{
        try {{ if (typeof window[fn] === 'function') window[fn](); }} catch(e) {{}}
      }});
      try {{ if (typeof checkTextStep === 'function') checkTextStep(3,'planText','fb3'); }} catch(e) {{}}
      document.querySelectorAll('.solution, .hidden-solution').forEach(function(s) {{
        s.classList.add('show');
      }});
      document.querySelectorAll('input, select, textarea').forEach(function(el) {{
        el.disabled = true;
      }});
      document.querySelectorAll('.btn').forEach(function(b) {{
        b.disabled = true;
        b.style.opacity = '0.5';
        b.style.cursor = 'default';
      }});
    }});
  }})();
  </script>
""".format(answers_json=answers_json)

    html = render_task_page(task_slug, task.title, raw_html, extra_inject=extra_inject)
    html = html.replace(
        'href="/aufgaben"',
        'href="/admin/submissions?class_id={}&amp;task_slug={}"'.format(class_id, task_slug),
    )
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Statistik
# ---------------------------------------------------------------------------

@router.get("/stats")
def api_stats(
    teacher: Teacher = Depends(get_optional_teacher),
    db: Session = Depends(get_session),
    class_id: int | None = None,
):
    if teacher is None:
        raise HTTPException(status_code=401)

    classes = _visible_classes(db, teacher)
    accessible_class = _get_accessible_class(db, teacher, class_id)
    eval_classes = [accessible_class] if accessible_class is not None else classes

    task_stats: list[dict] = []
    seen_slugs: set[str] = set()

    for klass in eval_classes:
        assignments = db.exec(
            select(Assignment).where(Assignment.class_id == klass.id, Assignment.active == True)  # noqa: E712
        ).all()
        students = db.exec(select(Student).where(Student.class_id == klass.id)).all()
        student_count = len(students)

        for assignment in assignments:
            slug = assignment.task_slug
            task = db.get(Task, slug)
            if task is None:
                continue

            solutions = json.loads(task.solutions_json) if task.solutions_json else None
            submissions = []
            for student in students:
                sub = db.exec(
                    select(Submission)
                    .where(Submission.student_id == student.id, Submission.task_slug == slug)
                    .order_by(Submission.submitted_at.desc())
                ).first()
                if sub:
                    submissions.append(json.loads(sub.answers_json))
            submitted_count = len(submissions)

            field_stats: dict[str, dict] = {}
            if solutions:
                for sol_field in solutions:
                    field_stats[sol_field] = {"correct": 0, "wrong": 0, "empty": 0}
                for answers in submissions:
                    result = _evaluate_answers(solutions, answers)
                    for field, status in result["per_field"].items():
                        if field in field_stats:
                            field_stats[field][status] += 1
                hotspots = []
                for field, counts in field_stats.items():
                    total = counts["correct"] + counts["wrong"] + counts["empty"]
                    if total == 0:
                        continue
                    wrong_pct = (counts["wrong"] + counts["empty"]) / total
                    hotspots.append({
                        "field": field,
                        "pretty": _pretty_key(field),
                        "correct": counts["correct"],
                        "wrong": counts["wrong"],
                        "empty": counts["empty"],
                        "total": total,
                        "error_pct": round(wrong_pct * 100),
                    })
                hotspots.sort(key=lambda h: h["error_pct"], reverse=True)
                total_fields = len(solutions) * max(submitted_count, 1)
                total_correct = sum(c["correct"] for c in field_stats.values())
                total_wrong = sum(c["wrong"] for c in field_stats.values())
                total_empty = sum(c["empty"] for c in field_stats.values())
            else:
                hotspots = []
                total_fields = 0
                total_correct = total_wrong = total_empty = 0

            task_key = f"{slug}:{klass.id}"
            if task_key in seen_slugs:
                for ts in task_stats:
                    if ts["slug"] == slug and ts["class_name"] == klass.name:
                        ts["submitted_count"] += submitted_count
                        ts["student_count"] += student_count
                        break
                continue
            seen_slugs.add(task_key)

            task_stats.append({
                "slug": slug,
                "title": task.title,
                "class_name": klass.name,
                "student_count": student_count,
                "submitted_count": submitted_count,
                "has_solutions": solutions is not None,
                "submission_pct": round(submitted_count / student_count * 100) if student_count else 0,
                "fill_pct": round(total_correct / total_fields * 100) if total_fields else 0,
                "error_pct": round((total_wrong + total_empty) / total_fields * 100) if total_fields else 0,
                "hotspots": hotspots[:5],
            })

    task_stats.sort(key=lambda t: t["error_pct"], reverse=True)
    return {"task_stats": task_stats}


# ---------------------------------------------------------------------------
# Lehrer-Verwaltung
# ---------------------------------------------------------------------------

@router.get("/teachers")
def api_list_teachers(
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    from datetime import datetime
    teachers = db.exec(select(Teacher).order_by(Teacher.created_at)).all()
    invites = db.exec(
        select(TeacherInvite)
        .where(TeacherInvite.used_at == None)  # noqa: E711
        .order_by(TeacherInvite.created_at.desc())
    ).all()
    return {
        "teachers": [
            {
                "id": t.id,
                "username": t.username,
                "role": t.role,
                "created_at": t.created_at.isoformat(),
            }
            for t in teachers
        ],
        "invites": [
            {
                "id": inv.id,
                "code": inv.code,
                "role": inv.role,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat(),
                "used_at": inv.used_at.isoformat() if inv.used_at else None,
                "used_by_teacher_id": inv.used_by_teacher_id,
            }
            for inv in invites
        ],
    }


@router.post("/teachers/invite")
def api_create_invite(
    teacher: Teacher = Depends(require_admin),
    role: str = Form("teacher"),
    db: Session = Depends(get_session),
):
    import secrets as _secrets
    from datetime import datetime, timedelta
    _ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "".join(_secrets.choice(_ALPHABET) for _ in range(10))
        if db.exec(select(TeacherInvite).where(TeacherInvite.code == code)).first() is None:
            break
    role = role if role in ("admin", "teacher") else "teacher"
    invite = TeacherInvite(
        code=code,
        role=role,
        created_by_teacher_id=teacher.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()
    return {"ok": True}


@router.post("/teachers/invites/{invite_id}/revoke")
def api_revoke_invite(
    invite_id: int,
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    invite = db.get(TeacherInvite, invite_id)
    if invite is not None and invite.used_at is None:
        db.delete(invite)
        db.commit()
    return {"ok": True}


@router.post("/teachers/{teacher_id}/delete")
def api_delete_teacher(
    teacher_id: int,
    teacher: Teacher = Depends(require_admin),
    db: Session = Depends(get_session),
):
    target = db.get(Teacher, teacher_id)
    if target is None:
        raise HTTPException(status_code=404)
    if target.id == teacher.id:
        raise HTTPException(status_code=400, detail="Man kann sich nicht selbst löschen")
    if target.role == "admin":
        admin_count = len(db.exec(select(Teacher).where(Teacher.role == "admin")).all())
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Letzter Admin kann nicht gelöscht werden")
    for klass in db.exec(select(Class).where(Class.owner_teacher_id == target.id)).all():
        klass.owner_teacher_id = teacher.id
        db.add(klass)
    db.delete(target)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Join (öffentliche Registrierung)
# ---------------------------------------------------------------------------

@router.post("/join")
def api_teacher_join(
    code: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    response: Response = None,
    db: Session = Depends(get_session),
):
    from datetime import datetime
    from .security import hash_password

    invite = db.exec(select(TeacherInvite).where(TeacherInvite.code == code.strip().upper())).first()
    if invite is None:
        raise HTTPException(status_code=400, detail="Ungültiger Einladungscode")
    if invite.used_at is not None:
        raise HTTPException(status_code=400, detail="Einladungscode bereits verwendet")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Einladungscode abgelaufen")

    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Benutzername erforderlich")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 8 Zeichen haben")
    if password != password_confirm:
        raise HTTPException(status_code=400, detail="Passwörter stimmen nicht überein")
    if db.exec(select(Teacher).where(Teacher.username == username)).first() is not None:
        raise HTTPException(status_code=400, detail="Benutzername bereits vergeben")

    new_teacher = Teacher(username=username, password_hash=hash_password(password), role=invite.role)
    db.add(new_teacher)
    db.flush()
    invite.used_at = datetime.utcnow()
    invite.used_by_teacher_id = new_teacher.id
    db.add(invite)
    db.commit()
    db.refresh(new_teacher)

    create_admin_session(db, new_teacher.id, response)
    return {"ok": True}
