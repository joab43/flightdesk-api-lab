"""Pruebas de la API REST de vuelos.

Cobertura de la Fase 7:
 - listar, consultar (existente e inexistente)
 - crear (válido e inválido), duplicados
 - actualizar (PUT completo y PATCH parcial)
 - eliminar
 - filtros
 - salud, estadísticas y métricas
"""

from datetime import datetime, timedelta, timezone


def _future(hours: float) -> str:
    """ISO timestamp UTC (naive) dentro de N horas."""
    dt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours)
    return dt.isoformat()


def _payload(**overrides) -> dict:
    """Cuerpo válido de creación con sobreescrituras opcionales."""
    base = {
        "flight_number": "AV101",
        "origin": "PTY",
        "destination": "MIA",
        "departure_time": _future(1),
        "arrival_time": _future(5),
        "status": "SCHEDULED",
    }
    base.update(overrides)
    return base


def _create(client, **overrides):
    response = client.post("/api/v1/flights", json=_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# --- Salud y métricas -----------------------------------------------------

def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_metrics_records_requests(client):
    client.get("/api/v1/flights")
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["requests_total"] >= 1


# --- Creación ------------------------------------------------------------

def test_create_flight_returns_201(client):
    response = client.post("/api/v1/flights", json=_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["flight_number"] == "AV101"
    assert data["origin"] == "PTY"
    assert data["status"] == "SCHEDULED"
    assert "created_at" in data


def test_create_rejects_invalid_airport_code(client):
    # "PTYXX" no cumple el patrón de 3 letras.
    response = client.post("/api/v1/flights", json=_payload(origin="PTYXX"))
    assert response.status_code == 422


def test_create_rejects_arrival_before_departure(client):
    response = client.post(
        "/api/v1/flights",
        json=_payload(departure_time=_future(5), arrival_time=_future(1)),
    )
    assert response.status_code == 422


def test_create_rejects_same_origin_and_destination(client):
    response = client.post("/api/v1/flights", json=_payload(destination="PTY"))
    assert response.status_code == 422


def test_create_rejects_unknown_status(client):
    response = client.post("/api/v1/flights", json=_payload(status="FLYING"))
    assert response.status_code == 422


def test_create_rejects_duplicate_flight_number(client):
    _create(client)
    response = client.post(
        "/api/v1/flights", json=_payload(destination="BOG")
    )
    assert response.status_code == 409


# --- Lectura --------------------------------------------------------------

def test_list_flights_empty_at_start(client):
    response = client.get("/api/v1/flights")
    assert response.status_code == 200
    assert response.json() == []


def test_get_flight_found(client):
    created = _create(client)
    response = client.get(f"/api/v1/flights/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_flight_not_found(client):
    response = client.get("/api/v1/flights/999")
    assert response.status_code == 404


# --- Actualización ---------------------------------------------------------

def test_put_replaces_editable_fields(client):
    created = _create(client)
    updated = _payload(
        flight_number="AV202",
        origin="BOG",
        destination="MIA",
        status="DELAYED",
    )
    response = client.put(
        f"/api/v1/flights/{created['id']}", json=updated
    )
    assert response.status_code == 200
    data = response.json()
    assert data["flight_number"] == "AV202"
    assert data["origin"] == "BOG"
    assert data["status"] == "DELAYED"
    assert data["id"] == created["id"]


def test_put_conflicts_with_existing_flight_number(client):
    first = _create(client)
    second = _create(client, flight_number="AV202")
    response = client.put(
        f"/api/v1/flights/{first['id']}", json=_payload(flight_number="AV202")
    )
    assert response.status_code == 409


def test_patch_updates_single_field(client):
    created = _create(client)
    response = client.patch(
        f"/api/v1/flights/{created['id']}", json={"status": "BOARDING"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BOARDING"
    assert data["flight_number"] == created["flight_number"]


def test_patch_rejects_empty_body(client):
    created = _create(client)
    response = client.patch(f"/api/v1/flights/{created['id']}", json={})
    assert response.status_code == 422


def test_patch_rejects_invalid_crossed_times(client):
    created = _create(client)
    # La llegada propuesta es anterior a la salida existente.
    earlier_arrival = (
        datetime.fromisoformat(created["departure_time"])
        - timedelta(hours=1)
    ).isoformat()
    response = client.patch(
        f"/api/v1/flights/{created['id']}", json={"arrival_time": earlier_arrival}
    )
    assert response.status_code == 400


def test_patch_conflicts_when_renaming_to_existing_number(client):
    _create(client)
    second = _create(client, flight_number="AV202")
    response = client.patch(
        f"/api/v1/flights/{second['id']}", json={"flight_number": "AV101"}
    )
    assert response.status_code == 409


# --- Eliminación -----------------------------------------------------------

def test_delete_flight_returns_204(client):
    created = _create(client)
    response = client.delete(f"/api/v1/flights/{created['id']}")
    assert response.status_code == 204
    assert response.text == ""
    follow_up = client.get(f"/api/v1/flights/{created['id']}")
    assert follow_up.status_code == 404


def test_delete_missing_flight_returns_404(client):
    response = client.delete("/api/v1/flights/999")
    assert response.status_code == 404


# --- Filtros y búsqueda ----------------------------------------------------

def test_filters_by_origin_and_destination(client):
    _create(client, flight_number="AV101", origin="PTY", destination="MIA")
    _create(client, flight_number="AV102", origin="PTY", destination="BOG")
    _create(client, flight_number="AV103", origin="MEX", destination="PTY")

    by_origin = client.get("/api/v1/flights", params={"origin": "PTY"})
    assert by_origin.status_code == 200
    assert {f["flight_number"] for f in by_origin.json()} == {"AV101", "AV102"}

    by_route = client.get(
        "/api/v1/flights", params={"origin": "PTY", "destination": "BOG"}
    )
    assert [f["flight_number"] for f in by_route.json()] == ["AV102"]


def test_filter_by_status_and_search(client):
    _create(client, flight_number="AV101", status="DELAYED")
    _create(client, flight_number="UA999", origin="MIA", destination="PTY", status="SCHEDULED")

    delayed = client.get("/api/v1/flights", params={"status": "DELAYED"})
    assert [f["flight_number"] for f in delayed.json()] == ["AV101"]

    found = client.get("/api/v1/flights", params={"search": "ua9"})
    assert [f["flight_number"] for f in found.json()] == ["UA999"]


# --- Estadísticas -----------------------------------------------------------

def test_stats_aggregates(client):
    _create(client, flight_number="AV101", status="SCHEDULED")
    _create(client, flight_number="AV102", status="SCHEDULED")
    _create(client, flight_number="AV103", status="DELAYED", origin="MIA", destination="PTY")

    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_flights"] == 3
    assert stats["by_status"]["SCHEDULED"] == 2
    assert stats["by_status"]["DELAYED"] == 1
    assert stats["distinct_origins"] == 2
