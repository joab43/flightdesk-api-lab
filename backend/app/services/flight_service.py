"""Lógica de negocio y acceso a datos para la entidad Flight.

Reglas de esta capa:
 - Las excepciones de dominio (FlightNotFound, FlightConflict,
   FlightValidationError) representan errores de negocio; el router
   las traduce a códigos HTTP.
 - Las consultas usan SQLAlchemy ORM (parametrizadas internamente),
   por lo que no hay riesgo de inyección SQL.
 - Toda escritura se confirma (commit) y se refresca el objeto para
   devolver el estado real de la base de datos.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.flight import Flight
from app.schemas.flight import FlightCreate, FlightPatch, FlightReplace, FlightStatus


class FlightNotFound(Exception):
    """El vuelo identificado no existe (HTTP 404)."""


class FlightConflict(Exception):
    """Conflicto de unicidad: flight_number ya registrado (HTTP 409)."""


class FlightValidationError(Exception):
    """Regla de negocio cruzada violada (HTTP 400)."""


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

def list_flights(
    db: Session,
    *,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    status: Optional[FlightStatus | str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Flight]:
    """Lista vuelos con filtros opcionales y paginación simple."""
    stmt = select(Flight)
    if origin:
        stmt = stmt.where(Flight.origin == origin.strip().upper())
    if destination:
        stmt = stmt.where(Flight.destination == destination.strip().upper())
    if status:
        status_value = status.value if isinstance(status, FlightStatus) else status
        stmt = stmt.where(Flight.status == status_value.strip().upper())
    if search:
        like_pattern = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            Flight.flight_number.ilike(like_pattern)
            | Flight.origin.ilike(like_pattern)
            | Flight.destination.ilike(like_pattern)
        )
    stmt = (
        stmt.order_by(Flight.departure_time.asc())
        .limit(min(limit, 500))
        .offset(max(offset, 0))
    )
    return list(db.execute(stmt).scalars().all())


def get_flight(db: Session, flight_id: int) -> Flight:
    """Obtiene un vuelo por su identificador o lanza FlightNotFound."""
    flight = db.get(Flight, flight_id)
    if flight is None:
        raise FlightNotFound(f"Vuelo con id {flight_id} no encontrado")
    return flight


def get_stats(db: Session) -> dict:
    """Estadísticas básicas agregadas desde la base de datos."""
    total = db.scalar(select(func.count(Flight.id))) or 0
    rows = db.execute(
        select(Flight.status, func.count(Flight.id)).group_by(Flight.status)
    ).all()
    by_status = {status: count for status, count in rows}
    origins = db.scalar(select(func.count(func.distinct(Flight.origin)))) or 0
    destinations = db.scalar(
        select(func.count(func.distinct(Flight.destination)))
    ) or 0
    return {
        "total_flights": total,
        "by_status": by_status,
        "distinct_origins": origins,
        "distinct_destinations": destinations,
    }


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------

def _ensure_flight_number_unique(
    db: Session, flight_number: str, exclude_id: Optional[int] = None
) -> None:
    """Verifica unicidad de flight_number (excluyendo el propio vuelo)."""
    stmt = select(Flight.id).where(Flight.flight_number == flight_number)
    if exclude_id is not None:
        stmt = stmt.where(Flight.id != exclude_id)
    if db.execute(stmt).first() is not None:
        raise FlightConflict(
            f"El número de vuelo '{flight_number}' ya está registrado"
        )


def _apply_editable_fields(flight: Flight, data: FlightCreate | FlightReplace) -> None:
    flight.flight_number = data.flight_number
    flight.origin = data.origin
    flight.destination = data.destination
    flight.departure_time = data.departure_time
    flight.arrival_time = data.arrival_time
    flight.status = data.status


def create_flight(db: Session, data: FlightCreate) -> Flight:
    """Crea un vuelo nuevo (valida unicidad del flight_number)."""
    _ensure_flight_number_unique(db, data.flight_number)
    flight = Flight(**data.model_dump())
    db.add(flight)
    db.commit()
    db.refresh(flight)
    return flight


def replace_flight(db: Session, flight_id: int, data: FlightReplace) -> Flight:
    """PUT: reemplaza todos los campos editables del vuelo."""
    flight = get_flight(db, flight_id)
    _ensure_flight_number_unique(db, data.flight_number, exclude_id=flight.id)
    _apply_editable_fields(flight, data)
    db.commit()
    db.refresh(flight)
    return flight


def patch_flight(db: Session, flight_id: int, data: FlightPatch) -> Flight:
    """PATCH: aplica solo los campos enviados (actualización parcial)."""
    flight = get_flight(db, flight_id)
    updates = data.model_dump(exclude_unset=True)

    if "flight_number" in updates:
        _ensure_flight_number_unique(db, updates["flight_number"], exclude_id=flight.id)

    # Estado efectivo tras aplicar la actualización parcial.
    effective_origin = updates.get("origin", flight.origin)
    effective_destination = updates.get("destination", flight.destination)
    effective_departure = updates.get("departure_time", flight.departure_time)
    effective_arrival = updates.get("arrival_time", flight.arrival_time)

    if effective_origin == effective_destination:
        raise FlightValidationError("origin y destination deben ser distintos")
    if effective_arrival <= effective_departure:
        raise FlightValidationError("arrival_time debe ser posterior a departure_time")

    for field, value in updates.items():
        setattr(flight, field, value)

    db.commit()
    db.refresh(flight)
    return flight


def delete_flight(db: Session, flight_id: int) -> None:
    """Elimina un vuelo (HTTP 204 sin cuerpo)."""
    flight = get_flight(db, flight_id)
    db.delete(flight)
    db.commit()


# ---------------------------------------------------------------------------
# Datos de demostración (ficticios, sin datos personales)
# ---------------------------------------------------------------------------

def _demo_flights(now: datetime) -> list[dict]:
    """Genera 8 vuelos de demostración relativos al momento actual."""
    def flight(hours_dep: float, hours_arr: float, **fields) -> dict:
        return {
            "departure_time": now + timedelta(hours=hours_dep),
            "arrival_time": now + timedelta(hours=hours_arr),
            **fields,
        }

    return [
        flight(1.0, 5.0, flight_number="AV101", origin="PTY", destination="MIA", status=FlightStatus.SCHEDULED),
        flight(2.0, 3.5, flight_number="AV205", origin="PTY", destination="BOG", status=FlightStatus.SCHEDULED),
        flight(3.0, 6.0, flight_number="CM310", origin="MEX", destination="PTY", status=FlightStatus.BOARDING),
        flight(1.5, 3.0, flight_number="DL1234", origin="ATL", destination="MIA", status=FlightStatus.BOARDING),
        flight(4.0, 7.0, flight_number="LA404", origin="SCL", destination="EZE", status=FlightStatus.DEPARTED),
        flight(-4.0, -1.0, flight_number="AR1812", origin="BOG", destination="PTY", status=FlightStatus.ARRIVED),
        flight(6.0, 9.0, flight_number="UA999", origin="MIA", destination="PTY", status=FlightStatus.DELAYED),
        flight(8.0, 13.0, flight_number="IB6610", origin="MAD", destination="PTY", status=FlightStatus.SCHEDULED),
    ]


def seed_demo_data(db: Session) -> int:
    """Sembra datos de demostración solo si la base de datos está vacía.

    Devuelve la cantidad de vuelos creados (0 si ya había datos).
    """
    if db.scalar(select(Flight.id).limit(1)) is not None:
        return 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for spec in _demo_flights(now):
        db.add(Flight(**spec))
    db.commit()
    return len(_demo_flights(now))
