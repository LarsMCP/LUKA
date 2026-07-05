"""LUKA – FastAPI-Anwendung.

App-Einstiegspunkt: Datenbank-Init + Aufgaben-Discovery beim Start, Health-Check,
Auslieferung der Aufgaben-HTML inkl. luka.js. Schüler- und Admin-Flows liegen in
den jeweiligen Routern (student, admin).
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session, select

from .admin import router as admin_router
from .auth import get_optional_student
from .config import RUNTIME_DIR
from .database import get_session, init_db
from .discovery import read_task_html, scan_tasks
from .models import Assignment, Student, Task
from .render import render_task_page
from .student import router as student_router
from .templating import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Datenverzeichnis + Tabellen anlegen, dann Aufgaben einlesen.
    init_db()
    scan_tasks()
    yield
    # Shutdown: aktuell nichts aufzuräumen.


app = FastAPI(
    title="LUKA – Lernplattform",
    description="Schlanke Lernplattform für Schülerklassen.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(student_router)
app.include_router(admin_router)


@app.get("/health", tags=["system"])
def health() -> JSONResponse:
    """Einfacher Health-Check für Monitoring/Deploy."""
    return JSONResponse({"status": "ok", "service": "luka", "version": app.version})


@app.get("/datenschutz", response_class=HTMLResponse, include_in_schema=False)
def datenschutz(request: Request):
    """Öffentliche Datenschutzhinweise."""
    return templates.TemplateResponse(request, "datenschutz.html", {})


@app.get("/static/luka.js", tags=["runtime"])
def luka_runtime() -> FileResponse:
    """Liefert die Aufgaben-Runtime aus."""
    path = RUNTIME_DIR / "luka.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="luka.js nicht gefunden")
    return FileResponse(path, media_type="application/javascript")


@app.get("/task/{slug}", response_class=HTMLResponse, tags=["tasks"])
def get_task(
    slug: str,
    session: Session = Depends(get_session),
    student: Student | None = Depends(get_optional_student),
):
    """Liefert eine Aufgabenseite (ohne Lösungen) inkl. luka.js.

    Zugriff nur für eingeloggte Schüler und nur für Aufgaben, die für ihre
    Klasse freigeschaltet sind.
    """
    if student is None:
        return RedirectResponse(url="/", status_code=303)

    task = session.get(Task, slug)
    raw_html = read_task_html(slug)
    if task is None or raw_html is None:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")

    assignment = session.exec(
        select(Assignment).where(
            Assignment.class_id == student.class_id,
            Assignment.task_slug == slug,
            Assignment.active == True,  # noqa: E712
        )
    ).first()
    if assignment is None:
        raise HTTPException(status_code=403, detail="Aufgabe nicht freigeschaltet")

    return HTMLResponse(render_task_page(slug, task.title, raw_html))
