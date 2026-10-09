"""Modelo de persistencia para la entidad Flight (tabla `flights`)."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    """Marca de tiempo UTC "naive" (sin zona horaria).

    SQLite no conserva la información de zona horaria de forma fiable, por
    lo que la aplicación normaliza todas las fechas a UTC sin tzinfo.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Flight(Base):
    """Vuelo: la entidad (recurso) principal del laboratorio."""

    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    flight_number: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    origin: Mapped[str] = mapped_column(String(3), index=True)
    destination: Mapped[str] = mapped_column(String(3), index=True)
    departure_time: Mapped[datetime] = mapped_column(DateTime)
    arrival_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    # Índice compuesto que acelera el filtro origin + destination.
    __table_args__ = (Index("ix_flights_origin_destination", "origin", "destination"),)

    def __repr__(self) -> str:  # pragma: no cover - utilidad de depuración
        return (
            f"Flight(id={self.id}, flight_number={self.flight_number!r}, "
            f"route={self.origin}->{self.destination}, status={self.status!r})"
        )
