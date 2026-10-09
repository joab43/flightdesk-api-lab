#!/usr/bin/env bash
# Smoke test: verifica los endpoints principales contra un backend
# en ejecución. Uso:
#   ./scripts/smoke_test.sh [URL_BASE]
# Ejemplo:
#   ./scripts/smoke_test.sh http://localhost:8000
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0

check() {
  local description="$1" expected="$2" method="$3" path="$4" data="${5:-}"
  local args=(-s -o /dev/null -w "%{http_code}" -X "$method" "${BASE_URL}${path}")
  if [ -n "$data" ]; then
    args+=(-H "Content-Type: application/json" -d "$data")
  fi
  local code
  code="$(curl "${args[@]}")" || code="000"
  if [ "$code" = "$expected" ]; then
    echo "  ✅ $description -> HTTP $code"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $description -> esperado HTTP $expected, recibido HTTP $code"
    FAIL=$((FAIL + 1))
  fi
}

echo "Smoke test contra $BASE_URL"
echo "────────────────────────────────────────"

check "Salud del backend"              200 GET  "/api/v1/health"
check "Listar vuelos"                  200 GET  "/api/v1/flights"
check "Filtrar por origen PTY"         200 GET  "/api/v1/flights?origin=PTY"
check "Filtrar por estado DELAYED"     200 GET  "/api/v1/flights?status=DELAYED"
check "Estadísticas"                   200 GET  "/api/v1/stats"
check "Métricas"                       200 GET  "/api/v1/metrics"
check "Vuelo inexistente (404)"        404 GET  "/api/v1/flights/999999"
check "Crear vuelo válido (201)"       201 POST "/api/v1/flights" \
  '{"flight_number":"SMOKE01","origin":"PTY","destination":"MIA","departure_time":"2030-01-01T10:00:00","arrival_time":"2030-01-01T14:00:00","status":"SCHEDULED"}'
check "Crear duplicado (409)"          409 POST "/api/v1/flights" \
  '{"flight_number":"SMOKE01","origin":"PTY","destination":"MIA","departure_time":"2030-01-01T10:00:00","arrival_time":"2030-01-01T14:00:00","status":"SCHEDULED"}'
check "Crear inválido (422)"           422 POST "/api/v1/flights" \
  '{"flight_number":"SMOKE02","origin":"PTY","destination":"PTY","departure_time":"2030-01-01T10:00:00","arrival_time":"2030-01-01T09:00:00","status":"SCHEDULED"}'
check "Actualizar vuelo (200)"         200 PATCH "/api/v1/flights/1" '{"status":"DELAYED"}'
check "Reemplazar vuelo (200)"         200 PUT    "/api/v1/flights/1" \
  '{"flight_number":"SMOKE02","origin":"PTY","destination":"BOG","departure_time":"2030-01-02T10:00:00","arrival_time":"2030-01-02T13:00:00","status":"SCHEDULED"}'
check "Eliminar vuelo (204)"           204 DELETE "/api/v1/flights/1"

echo "────────────────────────────────────────"
echo "Resultado: $PASS correctas, $FAIL fallidas"
[ "$FAIL" -eq 0 ]
