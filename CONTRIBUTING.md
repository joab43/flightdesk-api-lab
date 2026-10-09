# Contribuir a FlightDesk API Lab

Gracias por querer contribuir. Este es un proyecto educativo, así que la
claridad vale más que la complejidad.

## Cómo proponer cambios

1. Abre un *issue* describiendo el problema o la idea antes de codificar.
2. Trabaja en una rama con nombre descriptivo:
   `git checkout -b feat/agregar-paginacion`.
3. Escribe o actualiza pruebas para tu cambio (`backend/tests/`).
4. Verifica que todo pase: `cd backend && python -m pytest -q`.
5. Documenta: si cambias endpoints, actualiza `docs/api-reference.md`;
   si cambias la infraestructura, `docs/docker-guide.md`.
6. Abre un *pull request* explicando **qué** cambia y **por qué**.

## Convenciones

- **Español** en docs, logs y mensajes de error; código e identificadores
  en inglés (`flight_number`, `created_at`).
- Una responsabilidad por capa: `api/` traduce HTTP, `services/` contiene
  reglas, `models/` persistencia, `schemas/` contratos.
- Errores de dominio como excepciones de Python (`FlightNotFound`),
  traducidas a HTTP en el router.
- Nunca registres cuerpos de solicitudes, tokens ni datos personales.
- Dependencias nuevas: añádelas con pin exacto en `requirements.txt` y
  justifica su necesidad en el PR.

## Estructura de commits

Mensajes descriptivos en español, por ejemplo:

- `feat(api): agregar filtro de búsqueda textual a GET /flights`
- `fix(backend): validar unicidad de flight_number en PATCH`
- `docs: ampliar guía de troubleshooting con escenario de CORS`

## Reporte de problemas de seguridad

Este laboratorio no maneja datos reales. Si encuentras un problema de
seguridad, abre un issue normal (no hay datos que proteger, pero la
mejora beneficia a todos los alumnos).
