"""Anbindung eines externen, öffentlichen Git-Repos für Aufgaben.

Struktur des Repos entspricht `content/aufgaben/`: pro Aufgabe ein Ordner
`<slug>/index.html` direkt im Repo-Root. Der Klon liegt in `TASKS_REPO_DIR`
(persistentes Datenverzeichnis, nicht Teil des Haupt-Repos).
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime

from sqlmodel import Session, select

from .config import TASKS_REPO_DIR
from .models import TaskRepoConfig

_CONFIG_ID = 1
_GIT_TIMEOUT_SECONDS = 60


def get_config(db: Session) -> TaskRepoConfig | None:
    return db.get(TaskRepoConfig, _CONFIG_ID)


def save_config(db: Session, repo_url: str, branch: str, sync_interval_minutes: int) -> TaskRepoConfig:
    config = get_config(db)
    if config is None:
        config = TaskRepoConfig(id=_CONFIG_ID, repo_url=repo_url)
    config.repo_url = repo_url
    config.branch = branch or "main"
    config.sync_interval_minutes = max(1, sync_interval_minutes)
    config.updated_at = datetime.utcnow()
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def disconnect(db: Session) -> None:
    """Entfernt die Repo-Konfiguration und den lokalen Klon."""
    config = get_config(db)
    if config is not None:
        db.delete(config)
        db.commit()
    if TASKS_REPO_DIR.exists():
        shutil.rmtree(TASKS_REPO_DIR)


def _run_git(args: list[str], cwd=None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "git-Fehler").strip())
    return result.stdout


def sync(db: Session) -> TaskRepoConfig:
    """Klont (erstmalig) oder aktualisiert (danach) das konfigurierte Repo.

    Schreibt Status/Zeitstempel in die Konfiguration, auch bei Fehlern
    (der zuletzt funktionierende lokale Stand bleibt dabei unangetastet).
    """
    config = get_config(db)
    if config is None or not config.repo_url.strip():
        raise RuntimeError("Kein Aufgaben-Repo konfiguriert.")

    try:
        TASKS_REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
        if (TASKS_REPO_DIR / ".git").exists():
            _run_git(["fetch", "--depth", "1", "origin", config.branch], cwd=TASKS_REPO_DIR)
            _run_git(["reset", "--hard", f"origin/{config.branch}"], cwd=TASKS_REPO_DIR)
        else:
            if TASKS_REPO_DIR.exists():
                shutil.rmtree(TASKS_REPO_DIR)
            _run_git([
                "clone",
                "--branch", config.branch,
                "--depth", "1",
                config.repo_url,
                str(TASKS_REPO_DIR),
            ])
        config.last_sync_status = "ok"
        config.last_sync_error = None
    except Exception as exc:  # noqa: BLE001 - Fehler wird angezeigt, nicht verschluckt
        config.last_sync_status = "error"
        config.last_sync_error = str(exc)[:500]

    config.last_synced_at = datetime.utcnow()
    db.add(config)
    db.commit()
    db.refresh(config)
    return config
