# Seguridad

## Prácticas aplicadas en este laboratorio

| Práctica | Implementación |
|---|---|
| Validación de datos | Pydantic valida tipos, patrones (IATA, número de vuelo), reglas de negocio (horarios, rutas) y enums cerrados *antes* de tocar la lógica. |
| Consultas parametrizadas | SQLAlchemy ORM genera SQL parametrizado; no hay concatenación de strings → sin inyección SQL. |
| CORS restringido | `CORSMiddleware` solo permite los orígenes de `FLIGHTDESK_CORS_ORIGINS` (no `*` con credenciales). |
| Sin secretos en Git | `.gitignore` excluye `.env` y `*.db`; `.env.example` no contiene valores reales; no hay secretos en el laboratorio. |
| Manejo seguro de excepciones | El handler global devuelve 500 genérico + `request_id`; la traza solo va a los logs del servidor. |
| Dependencias fijadas | `requirements.txt` con `==` por paquete; imágenes base con pin de versión. |
| Privilegios mínimos | Contenedores ejecutan como `appuser` (UID 1000) y `nginx` (UID 101), nunca root. |
| Separación código/configuración | Toda la configuración viaja por variables de entorno (ver `config.py`). |
| Sin logging de datos sensibles | No se registran bodies de solicitudes, cookies ni headers de autorización (ver `logging_config.py`). |

## Limitaciones importantes (léelas antes de "desplegar")

1. **Sin autenticación ni autorización.** Cualquiera con acceso al puerto
   puede crear, editar o eliminar vuelos. Esto es deliberado: añadir
   seguridad *ficticia* (un token hardcodeado) es peor que nada, porque
   da falsa sensación de protección.
2. **No expuestas a Internet.** Este laboratorio es para tu máquina. Si lo
   expones, cualquiera puede leer y borrar los datos.
3. **SQLite** no está diseñado para escritura concurrente intensa ni para
   múltiples instancias.
4. **Sin HTTPS propio.** En un despliegue real, termina TLS en un proxy
   (Traefik, Caddy, un balanceador de carga).
5. **Sin rate limiting** ni protección contra abusos.
6. **Sin copia de seguridad automatizada** del volumen (ejercicio para
   ti: `docker run --rm -v flightdesk_data:/data -v "$PWD:/backup" alpine tar czf /backup/flights.tar.gz /data`).

## Registro de excepciones sin revelar secretos

- Los logs de error incluyen la traza **solo del lado del servidor**.
- No se registran: cuerpos de solicitudes, headers de autorización,
  cookies, ni valores de variables de entorno.
- El cliente recibe `{"detail": "Error interno del servidor",
  "request_id": "..."}`: suficiente para reportar, insuficiente para
  explotar.

## Cómo evolucionar hacia observabilidad profesional (Fase opcional)

Sin cuentas de pago para la versión local:

- **Azure Application Insights:** en Azure, añadirías el SDK de OpenTelemetry
  (`opentelemetry-instrumentation-fastapi`) exportando a la connection
  string de Application Insights. Métricas de solicitudes, dependencias
  (SQL) y excepciones se correlacionan automáticamente por
  `operation_id` (equivalente a nuestro `request_id`).
- **Dynatrace:** con OneAgent o el operador de OpenTelemetry, las trazas
  y métricas se inyectan automáticamente; el `X-Request-ID` de este
  laboratorio mapea al `trace_id` de Dynatrace.
- **Puente local gratuito:** exportar trazas OTLP a un contenedor
  Jaeger/Tempo es la forma más económica de ver el recorrido de
  solicitudes antes de subir a la nube.

Nuestro middleware de request-id es exactamente el mismo concepto que la
correlación de trazas distribuidas: un identificador que viaja en el
header y aparece en todos los logs de la cadena.

## Autenticación futura (si la añades)

Si decides incorporarla en una fase avanzada:

- OAuth2 con Password Flow (FastAPI lo soporta de forma nativa) o JWT.
- **Implicaciones:** almacenamiento de hashes (bcrypt/argon2, nunca
  contraseñas en claro), expiración de tokens, refresh tokens, roles
  (autorización: solo operadores pueden DELETE), y CORS con
  `allow_credentials=True`.
- **Nunca** implementes tu propia criptografía ni inventes esquemas
  de token "obscuros".
