# Guía de aprendizaje: API REST desde cero

> Cada concepto incluye: **definición**, **ejemplo práctico** (FlightDesk),
> **fragmento de código** cuando corresponde, **error común** y
> **pregunta de comprobación**.

---

## 1. ¿Qué es una API?

**Definición:** Una API (Application Programming Interface) es un contrato:
define cómo un programa puede pedirle cosas a otro sin conocer sus
detalles internos.

**Ejemplo:** El frontend de FlightDesk no sabe cómo está implementado el
backend (Python, SQLite…); solo sabe que `GET /api/v1/flights` le devuelve
una lista de vuelos en JSON.

**Código:**

```http
GET /api/v1/flights HTTP/1.1
Host: localhost:8000
```

**Error común:** Tratar la API como "la base de datos del frontend" y
pedirle al endpoint que haga filtrados complejos que deberían ser del
cliente, o viceversa.

**Pregunta de comprobación:** ¿Por qué el frontend podría cambiar de
React a Vue sin tocar el backend?

---

## 2. ¿Qué significa REST?

**Definición:** REST (Representational State Transfer) es un estilo
arquitectónico para APIs sobre HTTP con reglas prácticas: recursos
identificados por URLs, uso de verbos HTTP estándar, mensajes
autodescriptivos y sin estado del servidor.

**Ejemplo:** En FlightDesk, el recurso "vuelo" se manipula así:

| Acción | Verbo HTTP | URL |
|---|---|---|
| Listar vuelos | GET | `/api/v1/flights` |
| Ver uno | GET | `/api/v1/flights/1` |
| Crear | POST | `/api/v1/flights` |
| Reemplazar | PUT | `/api/v1/flights/1` |
| Actualizar parcial | PATCH | `/api/v1/flights/1` |
| Eliminar | DELETE | `/api/v1/flights/1` |

**Error común:** Usar POST para todo (`POST /getFlight`) — es una RPC,
no REST.

**Pregunta de comprobación:** ¿Qué verbo y URL usarías para eliminar el
vuelo 7?

---

## 3. ¿Qué es un recurso?

**Definición:** Un recurso es la "cosa" que la API expone (un sustantivo):
un vuelo, un usuario, un pedido. Se identifica con un nombre y, opcionalmente,
un identificador.

**Ejemplo:** `Flight` con sus campos `flight_number`, `origin`,
`destination`, `departure_time`, `arrival_time`, `status`.

**Código (esquema JSON de un vuelo):**

```json
{
  "id": 1,
  "flight_number": "AV101",
  "origin": "PTY",
  "destination": "MIA",
  "departure_time": "2026-10-10T10:00:00",
  "arrival_time": "2026-10-10T14:00:00",
  "status": "SCHEDULED",
  "created_at": "2026-10-09T12:00:00"
}
```

**Error común:** Poner verbos en la URL (`/api/v1/getFlight`) o recursos
que son acciones (`/api/v1/searchFlights` en vez de `GET /flights?search=...`).

**Pregunta de comprobación:** ¿Es "estadísticas" (`/stats`) un recurso o
una vista de un recurso? (Respuesta: una vista calculada del conjunto de
vuelos — aceptable en REST.)

---

## 4. ¿Qué es un endpoint?

**Definición:** Un endpoint es una combinación concreta de **verbo HTTP +
ruta** que realiza una operación específica.

**Ejemplo:** `GET /api/v1/flights` y `POST /api/v1/flights` son **dos
endpoints distintos** aunque compartan la ruta.

**Código:**

```python
@router.get("/flights")          # endpoint 1: listar
def list_flights(...): ...

@router.post("/flights")         # endpoint 2: crear
def create_flight(...): ...
```

**Error común:** Crear un endpoint "genérico" que recibe una cadena con la
operación a realizar (vuelve imposible cachear, auditar y documentar).

**Pregunta de comprobación:** ¿Cuántos endpoints tiene FlightDesk para la
entidad flights? (Respuesta: 6 CRUD + stats.)

---

## 5. ¿Qué diferencia hay entre URL, URI y endpoint?

**Definición:**

- **URI**: identificador de recurso genérico (`/api/v1/flights/1`).
- **URL**: URI que además indica *cómo* acceder (protocolo + host):
  `http://localhost:8000/api/v1/flights/1`.
- **Endpoint**: el punto de acceso concreto en el servidor, es decir,
  verbo + ruta (`GET /api/v1/flights/{id}`).

**Ejemplo:** La URL `http://localhost:8000/api/v1/flights/1` apunta al
endpoint `GET /api/v1/flights/{flight_id}`.

**Error común:** Usar los términos como sinónimos en código o documentación,
lo que confunde al hablar de "la URL del endpoint de crear".

**Pregunta de comprobación:** Si cambio el backend de puerto 8000 a 9000,
¿cambia el endpoint? (No: cambia la URL, no el endpoint.)

---

## 6. ¿Qué es HTTP?

**Definición:** Protocolo de aplicación sin conexión persistente obligatoria:
el cliente envía una **solicitud** (método, ruta, headers, cuerpo) y el
servidor devuelve una **respuesta** (código de estado, headers, cuerpo).

**Ejemplo de solicitud y respuesta:**

```http
POST /api/v1/flights HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{"flight_number":"AV101","origin":"PTY","destination":"MIA", ...}

HTTP/1.1 201 Created
Content-Type: application/json

{"id": 1, "flight_number": "AV101", ...}
```

**Error común:** Creer que HTTP "guarda" algo entre peticiones (no: ver
*stateless* más abajo).

**Pregunta de comprobación:** ¿Qué parte de la respuesta te dice si la
operación funcionó? (El código de estado.)

---

## 7. ¿Cómo funcionan cliente y servidor?

**Definición:** El **cliente** inicia la comunicación (navegador, app);
el **servidor** escucha, procesa y responde. Nadie "empuja" datos:
siempre hay una solicitud previa.

**Ejemplo:** Al abrir `http://localhost:8080`, el navegador (cliente) pide
`index.html` a nginx; luego `app.js` ejecuta `fetch()` contra
`/api/v1/flights`, que nginx reenvía al backend (otro servidor para el
navegador, pero cliente de nginx... en realidad backend es el servidor
final de esa cadena).

**Código:**

```javascript
// app.js: el navegador actúa como cliente HTTP
const response = await fetch("/api/v1/flights");
const flights = await response.json();
```

**Error común:** Pensar que el servidor puede avisar al navegador cuando
cambia algo (para eso están WebSockets/SSE, fuera del alcance de este lab).

**Pregunta de comprobación:** ¿Quién inicia la petición cuando haces clic
en "Actualizar"? (El navegador.)

---

## 8. Solicitudes y respuestas HTTP

**Definición:** La **solicitud** tiene: línea de inicio (método + ruta),
headers y cuerpo opcional. La **respuesta** tiene: código de estado,
headers y cuerpo opcional.

**Ejemplo en la app:** Al crear un vuelo, el frontend envía el vuelo en el
cuerpo; el backend responde 201 con el vuelo creado (ahora con `id` y
`created_at` generados por el servidor).

**Error común:** Ignorar el código de estado y parsear el cuerpo como si
siempre fuera el recurso (un 404 puede traer `{"detail": "..."}`).

**Pregunta de comprobación:** ¿En un DELETE exitoso de FlightDesk, qué
cuerpo trae la respuesta? (Ninguno: 204 No Content.)

---

## 9. ¿Qué es JSON?

**Definición:** Formato de texto ligero para estructuras de datos
(objetos `{}` y arreglos `[]`), derivado de la sintaxis de JavaScript.

**Ejemplo:** Una lista de vuelos:

```json
[
  {"id": 1, "flight_number": "AV101", "status": "SCHEDULED"},
  {"id": 2, "flight_number": "AV205", "status": "DELAYED"}
]
```

**Código (serialización automática con Pydantic):**

```python
@router.get("/flights", response_model=list[FlightResponse])
def list_flights(...): ...   # FastAPI convierte objetos -> JSON
```

**Error común:** Enviar JSON sin el header `Content-Type:
application/json` (el servidor no lo parseará).

**Pregunta de comprobación:** ¿Por qué `201 Created` con un cuerpo JSON es
mejor que devolver solo el id como texto plano? (Contrato auto-descriptivo.)

---

## 10. ¿Qué son los headers?

**Definición:** Metadatos de la solicitud/respuesta: tipo de contenido,
autenticación, cookies, control de caché, etc.

**Ejemplo:** `Content-Type: application/json` le dice al servidor cómo
interpretar el cuerpo; `X-Request-ID` correlaciona logs.

**Código:**

```http
GET /api/v1/flights HTTP/1.1
Accept: application/json
X-Request-ID: 9f8c6e2a-...
```

**Error común:** Poner tokens o datos sensibles en la URL en vez de en un
header (las URLs quedan en logs de proxies).

**Pregunta de comprobación:** ¿Qué header usarías para decirle al servidor
que aceptas JSON? (`Accept: application/json`.)

---

## 11. ¿Qué es el body de una solicitud?

**Definición:** La carga útil (payload) que el cliente envía, habitualmente
en POST/PUT/PATCH. GET y DELETE normalmente no llevan body.

**Ejemplo:** Crear un vuelo:

```json
{
  "flight_number": "AV101",
  "origin": "PTY",
  "destination": "MIA",
  "departure_time": "2026-10-10T10:00:00",
  "arrival_time": "2026-10-10T14:00:00",
  "status": "SCHEDULED"
}
```

**Código (validación automática con Pydantic):**

```python
class FlightCreate(BaseModel):
    flight_number: str   # min 2, máx 8, alfanumérico
    origin: str          # exactamente 3 letras
    ...
# Si falla la validación -> FastAPI responde 422 automáticamente
```

**Error común:** Enviar el body sin `Content-Type: application/json`, o
enviar form-urlencoded donde se espera JSON.

**Pregunta de comprobación:** ¿Qué body llevaría un PATCH que solo cambia el
estado? (`{"status": "DELAYED"}` — solo los campos a cambiar.)

---

## 12. Parámetros de ruta y de consulta

**Definición:**

- **De ruta (path)**: forman parte de la URL e identifican un recurso:
  `/api/v1/flights/1`.
- **De consulta (query)**: vienen después de `?` y filtran/ordenan:
  `/api/v1/flights?origin=PTY&status=DELAYED`.

**Código:**

```python
@router.get("/flights/{flight_id}")            # path parameter
def get_flight(flight_id: int, db=Depends(get_db)): ...

@router.get("/flights")
def list_flights(origin: str | None = Query(default=None)): ...  # query
```

**Error común:** Usar path params para filtros (`/flights/PTY/MIA`) —
rompe la semántica de recurso y dificulta opcionalidad.

**Pregunta de comprobación:** ¿Cómo filtrarías vuelos de PTY a MIA?
(`GET /api/v1/flights?origin=PTY&destination=MIA`.)

---

## 13. Autenticación vs autorización

**Definición:**

- **Autenticación**: *quién eres* (verificar identidad: usuario/contraseña,
  token).
- **Autorización**: *qué puedes hacer* (permisos: ¿puede este usuario
  eliminar vuelos?).

**Ejemplo:** FlightDesk v1 **no tiene autenticación** (laboratorio
educativo). En una segunda fase se añadiría un token en el header
`Authorization: Bearer ...` y reglas por rol.

**Error común:** Añadir "autenticación ficticia" (un token hardcodeado) que
parece segura pero no lo es. Mejor ninguna que seguridad de mentira.

**Pregunta de comprobación:** ¿Autenticar es suficiente para permitir
borrar? (No: falta autorización.)

---

## 14. ¿Qué significa que una API sea stateless?

**Definición:** El servidor no guarda estado de la conversación entre
solicitudes: cada request debe contener todo lo necesario para procesarse.

**Ejemplo:** Cada llamada a FlightDesk incluye sus propios datos; el
servidor no "recuerda" qué filtros usaste antes. Escalar horizontalmente
es trivial: cualquier instancia puede atender cualquier petición.

**Error común:** Guardar en el servidor "el último vuelo consultado" como
estado de sesión (rompe statelessness y complica el escalado).

**Pregunta de comprobación:** ¿Por qué con stateless puedes matar un
contenor backend a mitad de uso sin perder la siguiente petición?

---

## 15. Códigos de estado HTTP

**Definición:** Números de 3 dígitos que clasifican el resultado:

| Rango | Significado | Ejemplo en FlightDesk |
|---|---|---|
| 2xx | Éxito | `200 OK`, `201 Created`, `204 No Content` |
| 4xx | Error del cliente | `400`, `404 Not Found`, `409 Conflict`, `422` |
| 5xx | Error del servidor | `500 Internal Server Error`, `503` |

**Por qué usamos cada uno:**

- `200 OK`: lectura/actualización exitosa.
- `201 Created`: recurso creado (POST). Incluye el recurso en el body.
- `204 No Content`: éxito sin cuerpo (DELETE).
- `400 Bad Request`: regla de negocio violada (llegada < salida en PATCH).
- `404 Not Found`: el recurso con ese id no existe.
- `409 Conflict`: conflicto semántico (flight_number duplicado).
- `422 Unprocessable Content`: la sintaxis JSON es válida pero la
  validación del esquema falla (origen de 2 letras, estado desconocido).
- `500`: fallo inesperado del servidor (el cliente no puede hacer nada).

**Error común:** Devolver siempre `200` y "esconder" el error en el body
(`{"success": false}`) — rompe el contrato HTTP y confunde clientes.

**Pregunta de comprobación:** ¿200 o 201 para crear un vuelo? ¿Por qué?
(201: se creó un recurso nuevo.)

---

## 16. ¿Qué diferencia hay entre REST y "una API cualquiera"?

**Definición:** "API" es el concepto general (cualquier interfaz entre
programas). REST es un **subconjunto** con convenciones concretas sobre
HTTP: recursos con URLs, verbos estándar, sin estado, representaciones
(JSON), hipermedia (opcional en la práctica).

**Ejemplo:** `POST /api/v1/flights/search?q=PTY` es una API HTTP pero no
RESTful (verbo en la ruta). `GET /api/v1/flights?search=PTY` sí lo es.

**Error común:** Creer que "usar HTTP y JSON" ya hace a algo REST.

**Pregunta de comprobación:** ¿`GET /api/v1/flights/1/delete` es REST?
(No: usa la ruta para expresar una acción en vez del verbo DELETE.)

---

## Ejercicios interactivos (intenta antes de ver la solución)

Las soluciones razonadas están al final de este archivo. **¡No las mires
primero!**

1. Quieres que el frontend muestre solo vuelos con destino MIA. ¿Qué
   solicitud haces?
2. El usuario envía `PATCH /api/v1/flights/1` con `{"status": "VOLANDO"}`.
   ¿Qué código esperas y por qué?
3. Necesitas cambiar el número de vuelo AV101 a AV102 y también su estado.
   ¿Un PUT o un PATCH? Justifica.
4. ¿Por qué `DELETE /api/v1/flights/1` devuelve 204 y no 200 con un
   mensaje "eliminado"?
5. ¿Qué pasa si haces `PUT` sobre un vuelo que no existe (id 999)?

### Soluciones

1. `GET /api/v1/flights?destination=MIA` — filtro por query parameter.
2. `422`: el enum `FlightStatus` no contiene "VOLANDO". La validación de
   esquemas ocurre antes de tocar la lógica de negocio.
3. Ambos funcionan, pero **PATCH** es más adecuado si solo cambias esos
   dos campos (menos datos en la red, menos riesgo de sobrescribir otros
   campos que no querías tocar). Usa PUT cuando quieras reemplazo completo.
4. 204 significa "éxito sin contenido". No hay nada útil que devolver tras
   eliminar; un body vacío evita interpretaciones. Es la convención REST
   para DELETE exitoso.
5. `404 Not Found` — el recurso no existe. No tiene sentido "reemplazar"
   algo que no existe (para crear existe POST).
