"""Endpoints REST para la entidad Flight (CRUD + filtros + estadísticas).

Notas de diseño:
 - El prefijo /api/v1 deja claro que la API tiene versionado.
 - El router solo traduce entre HTTP y el servicio: no contiene
   lógica de negocio ni SQL.
 - Errores de dominio -> códigos HTTP semánticos (404, 409, 400).
 - La validación de esquemas la realiza FastAPI/Pydantic (422).
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.flight import (
    FlightCreate,
    FlightPatch,
    FlightReplace,
    FlightResponse,
    FlightStatus,
)
from app.services import flight_service

router = APIRouter(prefix="/api/v1", tags=["flights"])


@router.get(
    "/flights",
    response_model=list[FlightResponse],
    summary="Listar vuelos",
    description="Devuelve vuelos con filtros opcionales por origen, destino, estado y búsqueda textual.",
)
def list_flights(
    origin: Optional[Annotated[str, Query(pattern=r"^[A-Za-z]{3}$")]] = None,
    destination: Optional[Annotated[str, Query(pattern=r"^[A-Za-z]{3}$")]] = None,
    status_filter: Optional[FlightStatus] = Query(
        default=None, alias="status", description="Filtrar por estado"
    ),
    search: Optional[str] = Query(
        default=None, max_length=50, description="Buscar en número de vuelo, origen o destino"
    ),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
):
    """GET /api/v1/flights con query parameters opcionales."""
    return flight_service.list_flights(
        db,
        origin=origin,
        destination=destination,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/flights/{flight_id}",
    response_model=FlightResponse,
    summary="Consultar un vuelo",
)
def get_flight(
    flight_id: Annotated[int, Path(ge=1, description="Identificador numérico del vuelo")],
    db: Session = Depends(get_db),
):
    """GET /api/v1/flights/{flight_id}. Devuelve 404 si no existe."""
    try:
        return flight_service.get_flight(db, flight_id)
    except flight_service.FlightNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/flights",
    response_model=FlightResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un vuelo",
)
def create_flight(payload: FlightCreate, db: Session = Depends(get_db)):
    """POST /api/v1/flights. Devuelve 201 y el vuelo creado."""
    try:
        return flight_service.create_flight(db, payload)
    except flight_service.FlightConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.put(
    "/flights/{flight_id}",
    response_model=FlightResponse,
    summary="Reemplazar un vuelo",
    description="Reemplaza todos los campos editables. Equivale a un reemplazo completo.",
)
def replace_flight(
    flight_id: Annotated[int, Path(ge=1)],
    payload: FlightReplace,
    db: Session = Depends(get_db),
):
    """PUT /api/v1/flights/{flight_id}."""
    try:
        return flight_service.replace_flight(db, flight_id, payload)
    except flight_service.FlightNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except flight_service.FlightConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch(
    "/flights/{flight_id}",
    response_model=FlightResponse,
    summary="Actualizar parcialmente un vuelo",
    description="Aplica únicamente los campos enviados.",
)
def patch_flight(
    flight_id: Annotated[int, Path(ge=1)],
    payload: FlightPatch,
    db: Session = Depends(get_db),
):
    """PATCH /api/v1/flights/{flight_id}."""
    try:
        return flight_service.patch_flight(db, flight_id, payload)
    except flight_service.FlightNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except flight_service.FlightConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except flight_service.FlightValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/flights/{flight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un vuelo",
)
def delete_flight(
    flight_id: Annotated[int, Path(ge=1)],
    db: Session = Depends(get_db),
):
    """DELETE /api/v1/flights/{flight_id}. Devuelve 204 sin cuerpo."""
    try:
        flight_service.delete_flight(db, flight_id)
    except flight_service.FlightNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/stats",
    summary="Estadísticas de vuelos",
)
def get_flight_stats(db: Session = Depends(get_db)):
    """GET /api/v1/stats: agregados básicos calculados en la base de datos."""
    return flight_service.get_stats(db)
