"""Datenmodelle für LUKA (SQLModel / SQLite).

Das Schema ist bewusst schlank gehalten und auf spätere Erweiterungen vorbereitet:
- Rollen (`Teacher.role`) ermöglichen später mehrere Admins/Lehrer.
- `Class.owner_teacher_id` erlaubt später klasseneigene Verwaltung pro Lehrer.
- `Submission` speichert pro Neu-Abgabe einen Eintrag (unbegrenzte Historie).
Auto-Korrektur ist vorerst nicht enthalten, das Schema bleibt dafür kompatibel.
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.utcnow()


class Teacher(SQLModel, table=True):
    """Lehrer-/Admin-Konten. Zunächst existiert genau ein Admin."""

    __tablename__ = "teachers"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="admin")  # "admin" | "teacher"
    created_at: datetime = Field(default_factory=_now)


class TeacherInvite(SQLModel, table=True):
    """Einmal-Einladungscode, mit dem sich ein neuer Lehrer selbst registriert.

    Analog zum Klassen-Beitrittscode (`Class.join_code`): der Admin generiert
    den Code, der neue Lehrer vergibt sich damit selbst Benutzername/Passwort.
    """

    __tablename__ = "teacher_invites"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    role: str = Field(default="teacher")  # Rolle, die der neue Account erhält
    created_by_teacher_id: int = Field(foreign_key="teachers.id")
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime
    used_at: datetime | None = Field(default=None)
    used_by_teacher_id: int | None = Field(default=None, foreign_key="teachers.id")


class Class(SQLModel, table=True):
    """Schulklasse mit eindeutigem Beitritts-Code."""

    __tablename__ = "classes"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    join_code: str = Field(index=True, unique=True)
    owner_teacher_id: int | None = Field(default=None, foreign_key="teachers.id")
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_now)


class Student(SQLModel, table=True):
    """Schüler mit Pseudonym (Datenminimierung), gebunden an eine Klasse."""

    __tablename__ = "students"

    id: int | None = Field(default=None, primary_key=True)
    class_id: int = Field(foreign_key="classes.id", index=True)
    display_name: str
    # Argon2-Hash des selbst vergebenen Passworts. None = noch keins gesetzt
    # (neuer Schüler oder vom Admin zurückgesetzt) → beim Login neu vergeben.
    password_hash: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_now)


class SessionToken(SQLModel, table=True):
    """Schüler-Session (Login per Klassen-Code, ohne Passwort)."""

    __tablename__ = "sessions"

    token: str = Field(primary_key=True)
    student_id: int = Field(foreign_key="students.id", index=True)
    expires_at: datetime


class AdminSession(SQLModel, table=True):
    """Lehrer-/Admin-Session (Login per Passwort)."""

    __tablename__ = "admin_sessions"

    token: str = Field(primary_key=True)
    teacher_id: int = Field(foreign_key="teachers.id", index=True)
    expires_at: datetime


class TaskRepoConfig(SQLModel, table=True):
    """Konfiguration für ein optional verbundenes externes Aufgaben-Git-Repo.

    Singleton-Tabelle: es existiert höchstens eine Zeile (id=1). Die Aufgaben
    darin werden zusätzlich zu `content/aufgaben` gelesen (siehe discovery.py)
    und per Hintergrund-Task periodisch synchronisiert (siehe task_repo.py).
    """

    __tablename__ = "task_repo_config"

    id: int | None = Field(default=None, primary_key=True)
    repo_url: str
    branch: str = Field(default="main")
    sync_interval_minutes: int = Field(default=15)
    last_synced_at: datetime | None = Field(default=None)
    last_sync_status: str | None = Field(default=None)  # "ok" | "error"
    last_sync_error: str | None = Field(default=None)
    updated_at: datetime = Field(default_factory=_now)


class Task(SQLModel, table=True):
    """Aus dem Dateisystem gespiegelte Aufgabe (Auto-Discovery in M2)."""

    __tablename__ = "tasks"

    slug: str = Field(primary_key=True)
    title: str
    subject: str | None = Field(default=None)
    hash: str | None = Field(default=None)
    discovered_at: datetime = Field(default_factory=_now)


class Assignment(SQLModel, table=True):
    """Freischaltung: welche Klasse welche Aufgabe sieht."""

    __tablename__ = "assignments"

    id: int | None = Field(default=None, primary_key=True)
    class_id: int = Field(foreign_key="classes.id", index=True)
    task_slug: str = Field(foreign_key="tasks.slug", index=True)
    active: bool = Field(default=True)


class Submission(SQLModel, table=True):
    """Eine Abgabe eines Schülers. Pro Neu-Abgabe entsteht ein neuer Eintrag."""

    __tablename__ = "submissions"

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id", index=True)
    task_slug: str = Field(foreign_key="tasks.slug", index=True)
    answers_json: str  # JSON-serialisierte Antworten { feldname: wert }
    submitted_at: datetime = Field(default_factory=_now)
