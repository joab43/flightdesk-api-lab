"""Esquemas de validación con Pydantic v2 para la entidad Flight.

Aquí se define el contrato JSON de la API: qué campos existen, sus tipos,
restricciones y reglas de negocio. FastAPI usa estos esquemas para:
 - validar automáticamente el cuerpo de las solicitudes (errores -> 422)
 - serializar las respuestas (response_model)
 - generar la documentación interactiva (/docs)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --- Tipos validados -------------------------------------------------------
# Número de vuelo: 2 a 8 caracteres alfanuméricos en mayúsculas (ej. "AV101").
FlightNumber = Annotated[str, Field(min_length=2, max_length=8, pattern=r"^[A-Z0-9]+$")]
# Código IATA de aeropuerto: exactamente 3 letras mayúsculas (ej. "PTY").
AirportCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class FlightStatus(str, Enum):
    """Estados permitidos de un vuelo (enum cerrado: nada de valores libres)."""

    SCHEDULED = "SCHEDULED"
    BOARDING = "BOARDING"
    DEPARTED = "DEPARTED"
    ARRIVED = "ARRIVED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


def _to_utc_naive(value: datetime) -> datetime:
    """Normaliza un datetime con zona horaria a UTC sin tzinfo."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class _FlightFields(BaseModel):
    """Campos compartidos por crear/consultar/reemplazar un vuelo."""

    flight_number: FlightNumber
    origin: AirportCode
    destination: AirportCode
    departure_time: datetime
    arrival_time: datetime
    status: FlightStatus

    @field_validator("flight_number", "origin", "destination", mode="before")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        """Acepta minúsculas y las normaliza a mayúsculas."""
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("departure_time", "arrival_time", mode="before")
    @classmethod
    def normalize_datetime(cls, value):
        """Acepta "Z" como sufijo y normaliza a UTC naive."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _to_utc_naive(value)

    @model_validator(mode="after")
    def validate_business_rules(self):
        """Reglas de negocio: llegadas futuras y rutas válidas."""
        if self.arrival_time <= self.departure_time:
            raise ValueError("arrival_time debe ser posterior a departure_time")
        if self.origin == self.destination:
            raise ValueError("origin y destination deben ser aeropuertos distintos")
        return self


class FlightCreate(_FlightFields):
    """Cuerpo de POST /api/v1/flights (todos los campos obligatorios)."""


class FlightReplace(_FlightFields):
    """Cuerpo de PUT /api/v1/flights/{id}: reemplazo completo de los campos editables."""


class FlightPatch(BaseModel):
    """Cuerpo de PATCH /api/v1/flights/{id}: actualización parcial.

    Todos los campos son opcionales, pero debe enviarse al menos uno.
    Las reglas cruzadas (horarios, origen != destino) se validan en el
    servicio contra el estado actual del vuelo.
    """

    flight_number: Optional[FlightNumber] = None
    origin: Optional[AirportCode] = None
    destination: Optional[AirportCode] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    status: Optional[FlightStatus] = None

    @field_validator("flight_number", "origin", "destination", mode="before")
    @classmethod
    def normalize_text(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("departure_time", "arrival_time", mode="before")
    @classmethod
    def normalize_datetime(cls, value):
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _to_utc_naive(value)

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("debe proporcionar al menos un campo para actualizar")
        return self


class FlightResponse(_FlightFields):
    """Representación pública de un vuelo (incluye campos generados por el servidor)."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # from_attributes permite convertir objetos SQLAlchemy -> este esquema.
    model_config = ConfigDict(from_attributes=True)
