"""Configuración de pruebas.

Cada prueba usa su propia base de datos SQLite temporal
(archivo en disco dentro de tmp_path), nunca la base de datos
real del laboratorio.

Las variables de entorno se fijan ANTES de importar la app,
porque la configuración se lee y cachea en el momento del
primer import.
"""

import os

os.environ.setdefault("FLIGHTDESK_DEMO_SEED", "false")
os.environ.setdefault("FLIGHTDESK_DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_engine(tmp_path):
    """Motor de base de datos de prueba aislado."""
    db_file = tmp_path / "test_flights.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Sesión SQLAlchemy contra la base de datos de prueba."""
    TestSession = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    """Cliente HTTP de prueba con la dependencia de DB sobreescrita."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
