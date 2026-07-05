"""Datenbank-Setup (SQLite via SQLModel).

Stellt die Engine, das Anlegen der Tabellen und eine Session-Dependency bereit.
"""
from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from .config import DATA_DIR, DATABASE_URL

# Leichte "Migrationen" für SQLite: fehlende Spalten additiv ergänzen.
# Format: {tabelle: [(spaltenname, spalten-DDL), ...]}
_COLUMN_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "students": [("password_hash", "VARCHAR")],
}

# check_same_thread=False ist für SQLite mit FastAPI (mehrere Threads) notwendig.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Legt das Datenverzeichnis und alle Tabellen an, falls sie fehlen."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Import stellt sicher, dass alle Modelle registriert sind, bevor create_all läuft.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _run_column_migrations()


def _run_column_migrations() -> None:
    """Ergänzt fehlende Spalten in bestehenden Tabellen (additive Migration)."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _COLUMN_MIGRATIONS.items():
            if table not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl in columns:
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def get_session() -> Generator[Session, None, None]:
    """FastAPI-Dependency: liefert eine DB-Session pro Request."""
    with Session(engine) as session:
        yield session
