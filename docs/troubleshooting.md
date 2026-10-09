# Troubleshooting: laboratorio de diagnóstico

> **Método:** para cada escenario, primero intenta resolverlo tú mismo.
> Las soluciones razonadas están en la sección "Soluciones" al final.
> Regla de oro: **observa antes de actuar** (logs, estado, código HTTP).

---

## Escenario 1: El frontend se muestra, pero no carga los vuelos

**Síntomas:** La página abre, los stats quedan en "–", la tabla vacía,
aparece un toast de error.

**Comandos de diagnóstico:**

```bash
# ¿El backend responde?
curl -i http://localhost:8000/api/v1/health

# ¿El proxy del frontend reenvía correctamente?
curl -i http://localhost:8080/api/v1/health

# ¿Qué dice el log del backend?
docker compose logs --tail=50 backend

# En el navegador: F12 -> pestaña Network -> filtrar "api"
# Inspecciona el estado HTTP y la respuesta de /api/v1/flights
```

**Posibles causas:** backend caído; proxy mal configurado (502); CORS
(mensaje de consola "blocked by CORS policy"); API_BASE incorrecta.

---

## Escenario 2: El backend devuelve HTTP 500

**Síntomas:** La API responde `{"detail": "Error interno del servidor"}`
con un `request_id`.

**Comandos:**

```bash
# Busca el request_id en los logs (correlación)
docker compose logs backend | grep "<request_id>"

# O busca la traza registrada como ERROR
docker compose logs backend | grep '"level": "ERROR"'
```

**Posibles causas:** error de código no manejado, fallo de disco del volumen,
permisos del volumen (SQLite no puede escribir).

---

## Escenario 3: Una solicitud devuelve HTTP 404

**Síntomas:** Recurso no encontrado.

**Comandos:**

```bash
# ¿Existe ese id?
curl http://localhost:8000/api/v1/flights

# ¿La ruta es correcta? (compara con /docs)
curl -i http://localhost:8000/api/v1/flights/999
curl -i http://localhost:8000/api/v1/flight/1     # <- ruta mal escrita
```

**Posibles causas:** id inexistente (correcto), ruta mal escrita,
proxy que no reenvía `/api/` (cuando usas :8080).

---

## Escenario 4: El navegador bloquea una solicitud por CORS

**Síntomas:** En consola: `Access to fetch ... has been blocked by CORS
policy`. La solicitud ni siquiera llega (preflight OPTIONS rechazado).

**Comandos:**

```bash
# Simula un preflight desde un origen
curl -i -X OPTIONS http://localhost:8000/api/v1/flights \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"

# Revisa la configuración de orígenes del backend
docker compose exec backend env | grep CORS
```

**Posibles causas:** `FLIGHTDESK_CORS_ORIGINS` no incluye el origen del
frontend; estás usando `?api_base=http://localhost:8000/...` desde
`http://localhost:8080` (orígenes distintos). En despliegue Docker normal
el proxy hace innecesario CORS.

---

## Escenario 5: El backend no puede iniciar

**Síntomas:** `docker compose ps` muestra `Restarting` o `Exited`; el
frontend queda en `waiting` ( unhealthy dependency).

**Comandos:**

```bash
docker compose logs backend | head -50      # traza del arranque
docker compose ps -a                        # estado y códigos de salida
docker compose exec backend python -c "import app.main"   # importa la app
```

**Posibles causas:** error de sintaxis/importación, dependencias no
instaladas (caché de build vieja), variable de entorno inválida,
volumen con permisos incorrectos.

---

## Escenario 6: Docker Compose no encuentra una variable de entorno

**Síntomas:** El backend arranca con valores por defecto (o aviso
"variable is not set"), puertos inesperados.

**Comandos:**

```bash
# ¿Existe .env? ¿Está escrito el nombre exacto?
ls -la .env
cat .env

# ¿Qué valores ve compose?
docker compose exec backend env | grep FLIGHTDESK

# ¿Qué resuelve la interpolación?
docker compose config | grep -A2 environment
```

**Posibles causas:** `.env` no copiado de `.env.example`, nombre de
variable mal escrito, espacios sin comillas, `.env` en otro directorio
(compose lee el `.env` del directorio de proyecto).

---

## Escenario 7: La base de datos pierde sus datos tras recrear el contenedor

**Síntomas:** Vuelos creados desaparecen después de `docker compose up`
o de una reconstrucción.

**Comandos:**

```bash
# ¿Existe el volumen?
docker volume ls | grep flightdesk

# ¿El volumen está montado en /app/data?
docker compose exec backend ls -la /app/data

# ¿Qué contiene el montaje según compose?
docker compose config | grep -A3 volumes:
```

**Posibles causas:** se usó `docker compose down --volumes` (elimina el
volumen a propósito); el volumen no está declarado en compose; la URL de
BD apunta fuera del directorio montado; se recreó el volumen con
`scripts/reset-lab.sh`.

---

## Escenario 8: El frontend no puede resolver el nombre del backend

**Síntomas:** Logs de nginx: `host not found in upstream "backend"`.

**Comandos:**

```bash
# ¿Ambos servicios están en la misma red?
docker network inspect flightdesk-api-lab_flightdesk_net \
  --format '{{range .Containers}}{{.Name}} {{end}}'

# ¿nginx resuelve "backend"?
docker compose exec frontend wget -q -O - http://backend:8000/api/v1/health
```

**Posibles causas:** servicios en redes distintas, backend sin healthcheck
(apagado al iniciar frontend), error tipográfico en `proxy_pass`.

---

## Escenario 9: Un endpoint devuelve datos incorrectos

**Síntomas:** Filtros que devuelven vuelos equivocados, stats que no
coinciden.

**Comandos:**

```bash
# Compara la respuesta cruda con lo esperado
curl -s "http://localhost:8000/api/v1/flights?origin=PTY" | python3 -m json.tool

# Consulta directa a la base de datos
docker compose exec backend python - <<'EOF'
from app.database import SessionLocal
from app.models.flight import Flight
db = SessionLocal()
for f in db.query(Flight).all():
    print(f.id, f.flight_number, f.origin, f.destination, f.status)
EOF
```

**Posibles causas:** filtros mal formados (case sensitivity), caché del
navegador, lógica de consulta en el servicio. Verifica siempre contra la
BD directa para aislar frontend vs backend vs datos.

---

## Escenario 10: Una modificación del código no aparece tras reconstruir

**Síntomas:** Editaste código, corriste `docker compose up --build -d`,
pero el comportamiento es idéntico.

**Comandos:**

```bash
# ¿El build realmente reconstruyó? (observa el paso "COPY app ./app")
docker compose build --no-cache backend

# ¿El código dentro del contenedor es el nuevo?
docker compose exec backend cat app/api/flights.py | head -5

# ¿Estás editando en el directorio correcto?
pwd
```

**Posibles causas:** caché de capas de Docker (la capa COPY no se
invalidó porque... sí lo hace si el contenido cambió; más común: edición
en otro directorio/proyecto, o `up` sin `--build`), contenedor antiguo
todavía atendiendo el puerto.

---

## Escenario 11: El health check falla aunque el contenedor esté ejecutándose

**Síntomas:** `docker compose ps` muestra backend como `unhealthy`; el
frontend no arranca.

**Comandos:**

```bash
# ¿El healthcheck manual funciona dentro del contenedor?
docker compose exec backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).read())"

# ¿La app escucha en el puerto esperado?
docker compose exec backend sh -c "netstat -tlnp 2>/dev/null || ss -tlnp"

# ¿El healthcheck del Dockerfile está definido?
docker inspect $(docker compose ps -q backend) --format '{{json .Config.Healthcheck}}'
```

**Posibles causas:** app escucha en 127.0.0.1 vs 0.0.0.0 (en este caso
el healthcheck usa localhost, que sí funciona; el problema típico es otro:
puerto distinto, tiempo de arranque insuficiente `start-period`, o el
endpoint /health devuelve 503 porque la BD no responde).

---

## Escenario 12: El backend responde lentamente

**Síntomas:** El navegador tarda; los toasts tardan en aparecer.

**Comandos:**

```bash
# Métricas de duración de la propia API
curl http://localhost:8000/api/v1/metrics | python3 -m json.tool

# ¿Hay solicitudes lentas registradas en logs?
docker compose logs backend | grep "Solicitud lenta"

# Recursos del contenedor
docker stats

# ¿Cuántas filas tiene la tabla?
docker compose exec backend python -c \
  "from app.database import SessionLocal; from app.models.flight import Flight; \
   print(SessionLocal().query(Flight).count())"
```

**Posibles causas:** consulta sin índices (revisa EXPLAIN), volumen con
I/O lenta, `limit` enorme, red congestionada, contenedor con CPU/memoria
limitada. Procedimiento: usa `/metrics` y los logs de "solicitud lenta"
para identificar el endpoint; luego aísla si es DB (consulta directa es
rápida pero el endpoint no) o infraestructura.

---

## Soluciones razonadas

**1.** Verifica con `curl` al backend directo (:8000) y a través del proxy
(:8080). Si :8000 funciona y :8080 no → el `proxy_pass` de nginx está
mal (revisa `docker compose logs frontend`). Si ambos fallan → el backend
está caído (logs). Si el curl funciona pero el navegador no → CORS o
`api_base` incorrecto (F12 → Network).

**2.** El 500 es genérico por diseño (no filtra trazas). El `request_id`
de la respuesta es la clave: búscalo en `docker compose logs backend`
para ver la excepción completa y la línea del código. Causas típicas:
fallo de escritura del volumen (permisos) o bug no manejado.

**3.** Primero distingue 404 "correcto" (id inexistente) de 404 de
enrutamiento: pide `/api/v1/flights` y verifica los ids existentes;
compara tu ruta con la tabla de `/docs`. Un 404 en `/api/v1/flight/1`
(es sin "s") es un error de ruta, no de recurso.

**4.** CORS es una política del navegador, no del servidor: el backend
solo incluye headers `Access-Control-Allow-Origin` cuando el `Origin`
coincide con `FLIGHTDESK_CORS_ORIGINS`. Solución: añade tu origen a la
variable y reconstruye, o mejor, usa el proxy del frontend (mismo origen,
CORS innecesario). Verifica el preflight con `curl -X OPTIONS`.

**5.** `docker compose logs backend` muestra la traza de arranque. Las
causas más comunes: import error (verifica con `python -c "import
app.main"`), `FLIGHTDESK_DATABASE_URL` mal formada, o falta de permiso
de escritura en `/app/data` (el usuario `appuser` debe ser dueño;
reconstruye la imagen).

**6.** Compose lee `.env` del directorio del proyecto al resolver
`${VAR}`. Verifica: existe `.env`, nombres exactos, sin espacios.
`docker compose config` muestra los valores resueltos finales — ahí se
ve si la interpolación falló.

**7.** El volumen `flightdesk_data` es el único almacenamiento. Si se
perdieron datos, casi siempre fue `docker compose down --volumes` o
`scripts/reset-lab.sh` (ambos eliminan el volumen a propósito). Comprueba
con `docker volume ls`. Para conservar datos: `docker compose down`
(sin `--volumes`).

**8.** Todos los servicios de compose comparten la red `flightdesk_net`
y se resuelven por nombre de servicio. Si nginx no resuelve `backend`,
los servicios están en redes distintas o el backend no estaba levantado
cuando nginx arrancó (por eso existe `depends_on: service_healthy`).
Verifica con `docker network inspect` y `wget` desde el contenedor
frontend.

**9.** Aísla capas: (a) consulta directa a la BD → si los datos son
correctos ahí, el problema es del endpoint; (b) curl al endpoint → si es
correcto, el problema es del frontend (caché o parsing). Filtra siempre
con mayúsculas (`PTY`), porque los filtros distinguen mayúsculas.

**10.** `docker compose up --build` reconstruye con caché de capas: si el
contenido cambió, la capa COPY se invalida y se copia el código nuevo. Si
no ves cambios: verifica `pwd` (¿editaste el archivo correcto?), usa
`docker compose build --no-cache` y verifica el contenido dentro del
contenedor con `docker compose exec backend cat ...`.

**11.** El healthcheck ejecuta `GET /api/v1/health` **dentro** del
contenedor. Si la app no escucha (host/port incorrectos), tarda más que
`start-period` (arranque lento por instalación/sembrado) o el endpoint
devuelve 503 (BD no disponible), el contenedor se marca `unhealthy`.
Ejecuta el healthcheck manualmente con `docker compose exec` para aislar.

**12.** Procedimiento: `/api/v1/metrics` → `avg_duration_ms` y
`slow_requests` identifican el endpoint lento; logs de "Solicitud lenta"
dan el `request_id`. Si una consulta directa a la BD es rápida pero el
endpoint no, el cuello de botella está en la aplicación; si ambas son
lentas, es la BD o el volumen. `docker stats` descarta saturación de
CPU/memoria del contenedor.
