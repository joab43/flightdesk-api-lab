"""Punto de entrada de la aplicación FastAPI.

Responsabilidades:
 - Ciclo de vida (lifespan): logging estructurado, creación de tablas
   y siembra de datos de demostración.
 - Middleware: CORS restringido, identificador de solicitud y
   registro de método/ruta/estado/duración de cada petición.
 - Manejo global de excepciones: no filtrar trazas internas al cliente.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.flights import router as flights_router
from app.api.monitoring import router as monitoring_router
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.logging_config import record_request, setup_logging
from app.services.flight_service import seed_demo_data

settings = get_settings()
logger = logging.getLogger("flightdesk.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranque y apagado ordenado de la aplicación."""
    setup_logging(settings.log_level)
    init_db()
    if settings.demo_seed:
        db = SessionLocal()
        try:
            seeded = seed_demo_data(db)
            if seeded:
                logger.info(
                    "Datos de demostración creados", extra={"seeded": seeded}
                )
            else:
                logger.info("Base de datos lista (ya contenía datos)")
        finally:
            db.close()
    else:
        logger.info("Base de datos lista (siembra de demostración desactivada)")
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "API REST de demostración para gestión de vuelos. "
        "Laboratorio educativo: no procesa pagos ni datos reales."
    ),
    lifespan=lifespan,
)

# CORS restringido a los orígenes configurados. En despliegue Docker
# el navegador habla con el proxy del frontend (mismo origen), por lo
# que CORS normalmente no interviene; se mantiene para desarrollo local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Middleware central: request-id + métricas + log estructurado."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000.0

    response.headers["X-Request-ID"] = request_id

    record_request(
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        settings.slow_request_ms,
    )

    context = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration_ms, 2),
    }
    logger.info("Solicitud completada", extra=context)
    if duration_ms >= settings.slow_request_ms:
        logger.warning("Solicitud lenta detectada", extra=context)

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Convierte fallos inesperados en 500 genérico.

    La traza completa se registra en los logs del servidor, pero el
    cliente solo recibe un mensaje genérico y el request_id para
    correlacionar. Nunca se expone información interna.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Error interno no controlado",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": 500,
        },
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "request_id": request_id},
    )


app.include_router(flights_router)
app.include_router(monitoring_router)
