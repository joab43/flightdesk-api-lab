"""Configuración de la aplicación basada en variables de entorno.

La separación entre código y configuración es una práctica de seguridad:
el código nunca contiene valores que cambien entre entornos (puertos,
URLs de base de datos, orígenes CORS). Todo se lee del entorno.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


def _parse_bool(value: str | None, default: bool) -> bool:
    """Convierte una cadena de entorno en booleano de forma tolerante."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la aplicación."""

    app_name: str = "FlightDesk API Lab"
    environment: str = "development"
    database_url: str = "sqlite:///./data/flights.db"
    cors_origins: tuple[str, ...] = ("http://localhost:8080",)
    log_level: str = "INFO"
    demo_seed: bool = True
    slow_request_ms: int = 500


@lru_cache
def get_settings() -> Settings:
    """Lee la configuración del entorno y la cachea (se lee una sola vez)."""
    origins_env = os.environ.get("FLIGHTDESK_CORS_ORIGINS", "")
    cors_origins = tuple(
        origin.strip() for origin in origins_env.split(",") if origin.strip()
    )
    if not cors_origins:
        # Valor por defecto razonable para desarrollo local.
        cors_origins = ("http://localhost:8080",)

    slow_ms = os.environ.get("FLIGHTDESK_SLOW_REQUEST_MS", "500")
    try:
        slow_request_ms = int(slow_ms)
    except ValueError:
        slow_request_ms = 500

    return Settings(
        app_name=os.environ.get("FLIGHTDESK_APP_NAME", "FlightDesk API Lab"),
        environment=os.environ.get("FLIGHTDESK_ENVIRONMENT", "development"),
        database_url=os.environ.get(
            "FLIGHTDESK_DATABASE_URL", "sqlite:///./data/flights.db"
        ),
        cors_origins=cors_origins,
        log_level=os.environ.get("FLIGHTDESK_LOG_LEVEL", "INFO").upper(),
        demo_seed=_parse_bool(os.environ.get("FLIGHTDESK_DEMO_SEED"), True),
        slow_request_ms=slow_request_ms,
    )
