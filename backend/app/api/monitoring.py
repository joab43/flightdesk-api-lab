"""Endpoints de observabilidad: salud, métricas e información del servicio."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import snapshot_metrics

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


@router.get("/health", summary="Comprobar la salud del backend")
def health(db: Session = Depends(get_db)):
    """Verifica que la API y su base de datos respondan.

    - 200 OK: la aplicación puede atender tráfico.
    - 503 Service Unavailable: la base de datos no responde.

    Docker Compose usa este endpoint como healthcheck del contenedor.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - intencional: cualquier fallo de DB -> 503
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="base de datos no disponible",
        )
    return {"status": "ok", "database": "ok", "service": "flightdesk-backend"}


@router.get("/metrics", summary="Métricas básicas de la API")
def metrics():
    """Métricas en memoria: solicitudes, errores, duraciones y solicitudes lentas."""
    return snapshot_metrics()


@router.get("", include_in_schema=False)
def root():
    """Redirige la raíz hacia la documentación interactiva."""
    return {
        "service": "FlightDesk API Lab",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
