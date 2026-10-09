# Referencia de la API

Base: `http://localhost:8000` (directo) o `http://localhost:8080/api`
(a través del proxy del frontend).

Todos los endpoints devuelven JSON. Errores:
`{"detail": "mensaje"}` (o un arreglo de errores en validaciones 422).

---

## GET /api/v1/health

Comprueba la salud del backend **y** de la base de datos.

| Código | Cuándo |
|---|---|
| 200 OK | API y base de datos responden |
| 503 Service Unavailable | La base de datos no responde |

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok", "database": "ok", "service": "flightdesk-backend"}
```

Docker Compose usa este endpoint como `healthcheck` del contenedor.

---

## GET /api/v1/stats

Estadísticas agregadas.

```bash
curl http://localhost:8000/api/v1/stats
```

```json
{
  "total_flights": 8,
  "by_status": {"SCHEDULED": 3, "BOARDING": 2, "DELAYED": 1},
  "distinct_origins": 7,
  "distinct_destinations": 4
}
```

---

## GET /api/v1/metrics

Métricas en memoria del proceso (se reinician al recrear el contenedor).

```json
{
  "requests_total": 42,
  "errors_total": 3,
  "avg_duration_ms": 4.21,
  "max_duration_ms": 120.5,
  "requests_by_endpoint": {"GET /api/v1/flights": 20},
  "slow_requests": []
}
```

---

## GET /api/v1/flights

Lista vuelos. **Query parameters opcionales:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| origin | string(3) | Filtrar por origen (ej. `PTY`) |
| destination | string(3) | Filtrar por destino (ej. `MIA`) |
| status | enum | Filtrar por estado |
| search | string | Búsqueda textual en número/origen/destino |
| limit | int | Máximo de resultados (1–500, default 100) |
| offset | int | Desplazamiento para paginación (default 0) |

```bash
curl "http://localhost:8000/api/v1/flights?origin=PTY&destination=MIA"
curl "http://localhost:8000/api/v1/flights?status=DELAYED&limit=5"
```

Respuesta: `200 OK` con un arreglo de vuelos.

---

## GET /api/v1/flights/{flight_id}

| Código | Cuándo |
|---|---|
| 200 OK | El vuelo existe |
| 404 Not Found | No existe un vuelo con ese id |
| 422 | El id no es un entero positivo |

```bash
curl http://localhost:8000/api/v1/flights/1
```

**¿Por qué 404?** El recurso identificado no existe; es un error del
cliente (pidió algo inexistente), no del servidor.

---

## POST /api/v1/flights

Crea un vuelo. Todos los campos son obligatorios.

| Código | Cuándo |
|---|---|
| 201 Created | Vuelo creado |
| 409 Conflict | `flight_number` ya registrado |
| 422 | Validación: tipos, patrones, llegada ≤ salida, origen = destino, estado desconocido |

```bash
curl -X POST http://localhost:8000/api/v1/flights \
  -H "Content-Type: application/json" \
  -d '{
    "flight_number": "AV101",
    "origin": "PTY",
    "destination": "MIA",
    "departure_time": "2026-10-10T10:00:00",
    "arrival_time": "2026-10-10T14:00:00",
    "status": "SCHEDULED"
  }'
```

Respuesta `201 Created` con el vuelo creado (incluye `id`, `created_at`,
`updated_at` generados por el servidor).

**¿Por qué 201?** Se creó un recurso nuevo; el cuerpo lo contiene.
**¿Por qué 409 y no 400?** El pedido es sintácticamente válido, pero
colisiona con el estado actual del recurso (unicidad).

---

## PUT /api/v1/flights/{flight_id}

**Reemplazo completo** de los campos editables. Todos los campos obligatorios.

| Código | Cuándo |
|---|---|
| 200 OK | Reemplazo realizado |
| 404 | El vuelo no existe |
| 409 | El nuevo `flight_number` ya existe en otro vuelo |
| 422 | Validación del esquema |

```bash
curl -X PUT http://localhost:8000/api/v1/flights/1 \
  -H "Content-Type: application/json" \
  -d '{
    "flight_number": "AV101",
    "origin": "PTY",
    "destination": "BOG",
    "departure_time": "2026-10-11T09:00:00",
    "arrival_time": "2026-10-11T12:00:00",
    "status": "DELAYED"
  }'
```

---

## PATCH /api/v1/flights/{flight_id}

**Actualización parcial:** solo se aplican los campos enviados.

| Código | Cuándo |
|---|---|
| 200 OK | Actualización aplicada |
| 400 Bad Request | Regla cruzada violada (ej. nueva llegada ≤ salida actual) |
| 404 | El vuelo no existe |
| 409 | Renombrar a un `flight_number` ya usado |
| 422 | Cuerpo vacío, tipos o patrones inválidos |

```bash
curl -X PATCH http://localhost:8000/api/v1/flights/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "DELAYED"}'
```

**PUT vs PATCH:** PUT reemplaza todo (envías la representación completa);
PATCH toca solo lo que envías. Si solo cambias el estado, PATCH es más
eficiente y menos propenso a sobrescribir campos por accidente.

---

## DELETE /api/v1/flights/{flight_id}

| Código | Cuándo |
|---|---|
| 204 No Content | Vuelo eliminado (sin cuerpo) |
| 404 | El vuelo no existe |

```bash
curl -X DELETE http://localhost:8000/api/v1/flights/1
```

**¿Por qué 204?** Éxito sin contenido que devolver. No hay representación
del recurso tras su eliminación.

---

## Errores 422 (validación)

FastAPI/Pydantic devuelven detalle de qué campo falló:

```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["body", "origin"],
      "msg": "String should match pattern '^[A-Z]{3}$'",
      "input": "PTYXX"
    }
  ]
}
```

## Errores 500

Fallos inesperados. El cliente recibe `{"detail": "Error interno del
servidor", "request_id": "..."}`; la traza completa **solo** aparece en
los logs del backend (correlacionada por `request_id`). Nunca se exponen
trazas internas en la respuesta.
