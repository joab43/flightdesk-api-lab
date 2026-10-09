"""Logging estructurado (JSON) y métricas básicas en memoria.

Observabilidad de la Fase 8:
 - Cada línea de log es un objeto JSON con timestamp, nivel, mensaje y
   campos de contexto (request_id, método, ruta, código de estado, duración).
 - Las métricas se mantienen en memoria: total de solicitudes, errores,
   duración media/máxima y las últimas solicitudes lentas.
 - No se registran cuerpos de solicitudes, cookies, tokens ni headers
   de autorización (ver docs/security.md).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections import deque
from threading import Lock

# Campos de contexto que el formateador extrae de cada registro (si existen).
_CONTEXT_FIELDS = ("request_id", "method", "path", "status", "duration_ms", "seeded")


class JSONFormatter(logging.Formatter):
    """Formatea cada registro de log como una línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Configura el logger raíz con salida JSON a stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


# ---------------------------------------------------------------------------
# Métricas en memoria (volátiles: se pierden al reiniciar el contenedor).
# ---------------------------------------------------------------------------

_METRICS_LOCK = Lock()
_REQUESTS_BY_ENDPOINT: dict[str, int] = {}
_REQUESTS_TOTAL = 0
_ERRORS_TOTAL = 0
_DURATION_SUM_MS = 0.0
_DURATION_MAX_MS = 0.0
_SLOW_REQUESTS: deque[dict] = deque(maxlen=10)


def record_request(
    method: str, path: str, status: int, duration_ms: float, slow_ms: int
) -> None:
    """Registra una solicitud completada y actualiza las métricas."""
    global _REQUESTS_TOTAL, _ERRORS_TOTAL, _DURATION_SUM_MS, _DURATION_MAX_MS
    with _METRICS_LOCK:
        key = f"{method} {path}"
        _REQUESTS_BY_ENDPOINT[key] = _REQUESTS_BY_ENDPOINT.get(key, 0) + 1
        _REQUESTS_TOTAL += 1
        _DURATION_SUM_MS += duration_ms
        _DURATION_MAX_MS = max(_DURATION_MAX_MS, duration_ms)
        if status >= 400:
            _ERRORS_TOTAL += 1
        if duration_ms >= slow_ms:
            _SLOW_REQUESTS.append(
                {
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration_ms": round(duration_ms, 2),
                    "at": time.time(),
                }
            )


def snapshot_metrics() -> dict:
    """Devuelve una copia consistente de las métricas actuales."""
    with _METRICS_LOCK:
        avg = (_DURATION_SUM_MS / _REQUESTS_TOTAL) if _REQUESTS_TOTAL else 0.0
        return {
            "requests_total": _REQUESTS_TOTAL,
            "errors_total": _ERRORS_TOTAL,
            "avg_duration_ms": round(avg, 2),
            "max_duration_ms": round(_DURATION_MAX_MS, 2),
            "requests_by_endpoint": dict(_REQUESTS_BY_ENDPOINT),
            "slow_requests": list(_SLOW_REQUESTS),
        }
