# Imagen del backend: Python + FastAPI + uvicorn.
# Imagen base estable y específica (pin por versión).
FROM python:3.12.8-slim-bookworm

LABEL org.opencontainers.image.title="FlightDesk API Lab - Backend"
LABEL org.opencontainers.image.description="API REST de gestión de vuelos (FastAPI + SQLAlchemy + SQLite)"
LABEL org.opencontainers.image.version="1.0.0"

# Entorno Python predecible: sin caché de bytecode y salida
# de logs sin búfer (importante para docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLIGHTDESK_DATABASE_URL=sqlite:////app/data/flights.db

WORKDIR /app

# Instalación de dependencias en capa separada: aprovecha la
# caché de Docker mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación.
COPY app ./app

# Usuario sin privilegios de root.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

# Publicar internamente el puerto (documentación; el mapeo
# real ocurre en docker compose.yaml).
EXPOSE 8000

# Healthcheck sin curl (la imagen slim no lo incluye):
# usa urllib de la propia imagen Python.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).read()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
