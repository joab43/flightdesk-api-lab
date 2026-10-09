"""Capa de acceso a datos: motor SQLAlchemy, sesiones y modelo base.

SQLite se usa como almacenamiento persistente. En Docker, la base de datos
vive dentro de un volumen montado en /app/data, por lo que los datos
sobreviven a la recreación del contenedor.
"""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

_settings = get_settings()


def _ensure_sqlite_directory(database_url: str) -> None:
    """Crea el directorio de la base de datos si no existe.

    SQLite no crea directorios por sí mismo: sin esto, una URL como
    sqlite:///./data/flights.db falla en el primer arranque.
    """
    prefix = "sqlite:///"
    if database_url.startswith(prefix) and not database_url.startswith(
        "sqlite:///:memory:"
    ):
        db_path = database_url[len(prefix) :]
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)


_ensure_sqlite_directory(_settings.database_url)

_connect_args = {}
if _settings.database_url.startswith("sqlite"):
    # SQLite + FastAPI: las solicitudes se atienden en varios hilos.
    # check_same_thread=False permite compartir la conexión entre hilos
    # de forma segura porque cada sesión se crea y destruye por solicitud.
    _connect_args["check_same_thread"] = False

engine = create_engine(_settings.database_url, connect_args=_connect_args, future=True)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos SQLAlchemy."""


def get_db() -> Iterator:
    """Dependencia de FastAPI: abre y cierra una sesión por solicitud.

    Este es el patrón "unit of work" por petición: la sesión se cierra
    siempre, incluso si la vista lanza una excepción.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea las tablas si no existen (idempotente, seguro en arranque)."""
    Base.metadata.create_all(bind=engine)
