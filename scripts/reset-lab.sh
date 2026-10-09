#!/usr/bin/env bash
# Reinicia el laboratorio desde cero, ELIMINANDO los datos persistentes.
# Útil para los ejercicios de troubleshooting (ver docs/troubleshooting.md).
# Uso: ./scripts/reset-lab.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Deteniendo servicios y eliminando el volumen de datos..."
docker compose down --volumes --remove-orphans

echo "Levantando servicios de nuevo (se sembrarán datos de demostración)..."
docker compose up --build -d

echo "Esperando a que el backend esté saludable..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ Laboratorio listo en http://localhost:8080"
    exit 0
  fi
  sleep 1
done

echo "❌ El backend no respondió. Revisa los logs con: docker compose logs backend" >&2
exit 1
