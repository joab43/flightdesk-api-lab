"use strict";

/* ---------------------------------------------------------------------------
 * FlightDesk API Lab — cliente HTTP del frontend.
 *
 * - Toda la comunicación con el backend ocurre mediante fetch().
 * - API_BASE apunta por defecto al proxy del frontend ("/api/v1"),
 *   lo que evita problemas de CORS en el despliegue con Docker.
 *   Para desarrollo local contra el backend directo:
 *     http://localhost:8080/?api_base=http://localhost:8000/api/v1
 * - Ninguna operación se simula: el UI solo cambia de estado
 *   después de que la API lo confirme.
 * ------------------------------------------------------------------------- */

const API_BASE =
  new URLSearchParams(window.location.search).get("api_base") || "/api/v1";

const STATUS_LABELS = {
  SCHEDULED: "Programado",
  BOARDING: "Abordando",
  DEPARTED: "Salido",
  ARRIVED: "Llegado",
  DELAYED: "Retrasado",
  CANCELLED: "Cancelado",
};

const state = {
  flights: [],
  filters: { search: "", origin: "", destination: "", status: "" },
};

const elements = {};

/* -------------------------------------------------------------------------
 * Utilidades de presentación
 * ------------------------------------------------------------------------- */

function formatDateTime(isoString) {
  // La API devuelve UTC "naive" (sin zona horaria). Al añadir "Z"
  // el navegador lo interpreta como UTC y lo muestra en hora local.
  const value = isoString.endsWith("Z") || isoString.includes("+")
    ? isoString
    : isoString + "Z";
  return new Date(value).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function toLocalInputValue(isoString) {
  // Convierte un ISO de la API al formato requerido por
  // <input type="datetime-local"> (hora local del navegador).
  const value = isoString.endsWith("Z") || isoString.includes("+")
    ? isoString
    : isoString + "Z";
  const date = new Date(value);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

function defaultFormTime(hoursFromNow) {
  const date = new Date(Date.now() + hoursFromNow * 3600 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/* -------------------------------------------------------------------------
 * Capa de acceso a la API (fetch)
 * ------------------------------------------------------------------------- */

function extractErrorMessage(data, status) {
  if (data && typeof data.detail === "string") {
    return data.detail;
  }
  // FastAPI devuelve 422 con un arreglo de errores de validación.
  if (data && Array.isArray(data.detail) && data.detail.length > 0) {
    const first = data.detail[0];
    if (first && typeof first.msg === "string") {
      return `${first.msg}${first.loc && first.loc.length ? ` (${first.loc.join(" → ")})` : ""}`;
    }
  }
  const known = {
    400: "La solicitud es incorrecta",
    404: "Recurso no encontrado",
    409: "Conflicto: el recurso ya existe",
    422: "Los datos enviados no son válidos",
    500: "Error interno del servidor",
    503: "Servicio no disponible",
  };
  return known[status] || `Error HTTP ${status}`;
}

async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(API_BASE + path, options);
  } catch (networkError) {
    // fetch() lanza TypeError solo ante fallos de red (DNS, servidor caído,
    // CORS preflight rechazado). No hubo respuesta HTTP.
    const error = new Error(
      "No se pudo conectar con la API. Comprueba que el backend esté activo."
    );
    error.kind = "network";
    throw error;
  }

  const raw = await response.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch (parseError) {
      data = { detail: raw };
    }
  }

  if (!response.ok) {
    const error = new Error(extractErrorMessage(data, response.status));
    error.status = response.status;
    throw error;
  }
  return data;
}

/* -------------------------------------------------------------------------
 * UI: notificaciones, carga, estado
 * ------------------------------------------------------------------------- */

function toast(message, type = "info") {
  const node = document.createElement("div");
  node.className = `toast toast-${type}`;
  node.textContent = message;
  elements.toastContainer.appendChild(node);
  setTimeout(() => node.remove(), 4500);
}

function setLoading(active) {
  elements.loadingOverlay.hidden = !active;
  document
    .querySelectorAll("button")
    .forEach((button) => (button.disabled = active));
}

function renderApiStatus(ok) {
  const pill = elements.apiStatus;
  pill.textContent = ok ? "API: conectada" : "API: sin conexión";
  pill.className = `status-pill ${ok ? "status-ok" : "status-error"}`;
}

/* -------------------------------------------------------------------------
 * UI: estadísticas
 * ------------------------------------------------------------------------- */

async function loadStats() {
  try {
    const stats = await api("GET", "/stats");
    elements.statTotal.textContent = stats.total_flights;
    elements.statScheduled.textContent = stats.by_status.SCHEDULED || 0;
    elements.statBoarding.textContent = stats.by_status.BOARDING || 0;
    elements.statDelayed.textContent = stats.by_status.DELAYED || 0;
  } catch (error) {
    // Las estadísticas son secundarias: se muestran sin bloquear la tabla.
    elements.statTotal.textContent = "–";
  }
}

/* -------------------------------------------------------------------------
 * UI: tabla de vuelos
 * ------------------------------------------------------------------------- */

function buildQueryString(filters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value && value.trim()) {
      params.set(key, value.trim());
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function badgeFor(status) {
  return `<span class="badge badge-${status}">${
    STATUS_LABELS[status] || status
  }</span>`;
}

function renderTable() {
  const rows = state.flights.map((flight) => {
    const cells = [
      `<td data-label="ID">${flight.id}</td>`,
      `<td data-label="Vuelo">${escapeHtml(flight.flight_number)}</td>`,
      `<td data-label="Ruta"><span class="route">${escapeHtml(
        flight.origin
      )}<span class="arrow">→</span>${escapeHtml(flight.destination)}</span></td>`,
      `<td data-label="Salida">${formatDateTime(flight.departure_time)}</td>`,
      `<td data-label="Llegada">${formatDateTime(flight.arrival_time)}</td>`,
      `<td data-label="Estado">${badgeFor(flight.status)}</td>`,
      `<td data-label="Acciones" class="actions-col">
         <button class="btn btn-secondary btn-small" data-action="edit" data-id="${flight.id}">Editar</button>
         <button class="btn btn-danger btn-small" data-action="delete" data-id="${flight.id}">Eliminar</button>
       </td>`,
    ];
    return `<tr>${cells.join("")}</tr>`;
  });

  elements.flightsBody.innerHTML = rows.join("");
  elements.emptyState.hidden = state.flights.length > 0;
}

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]
  );
}

async function loadFlights() {
  setLoading(true);
  try {
    const query = buildQueryString(state.filters);
    state.flights = await api("GET", `/flights${query}`);
    renderTable();
    return true;
  } catch (error) {
    toast(error.message, "error");
    renderApiStatus(false);
    return false;
  } finally {
    setLoading(false);
  }
}

/* -------------------------------------------------------------------------
 * Operaciones CRUD
 * ------------------------------------------------------------------------- */

function readForm(form) {
  return {
    flight_number: form.flight_number.value.trim().toUpperCase(),
    origin: form.origin.value.trim().toUpperCase(),
    destination: form.destination.value.trim().toUpperCase(),
    departure_time: form.departure_time.value,
    arrival_time: form.arrival_time.value,
    status: form.status.value,
  };
}

async function handleCreate(event) {
  event.preventDefault();
  const form = event.target;
  const payload = readForm(form);

  if (payload.departure_time >= payload.arrival_time) {
    toast("La llegada debe ser posterior a la salida.", "error");
    return;
  }

  setLoading(true);
  try {
    const created = await api("POST", "/flights", payload);
    toast(`Vuelo ${created.flight_number} creado (id ${created.id}).`, "success");
    form.reset();
    form.departure_time.value = defaultFormTime(1);
    form.arrival_time.value = defaultFormTime(5);
    await Promise.all([loadFlights(), loadStats()]);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(false);
  }
}

function openEditDialog(flight) {
  const form = elements.editForm;
  form.id.value = flight.id;
  form.flight_number.value = flight.flight_number;
  form.origin.value = flight.origin;
  form.destination.value = flight.destination;
  form.status.value = flight.status;
  form.departure_time.value = toLocalInputValue(flight.departure_time);
  form.arrival_time.value = toLocalInputValue(flight.arrival_time);
  elements.editId.textContent = `#${flight.id}`;
  elements.editDialog.showModal();
}

async function handleEdit(event) {
  event.preventDefault();
  const form = event.target;
  const flightId = form.id.value;
  // PUT: enviamos el conjunto COMPLETO de campos editables.
  const payload = readForm(form);

  if (payload.departure_time >= payload.arrival_time) {
    toast("La llegada debe ser posterior a la salida.", "error");
    return;
  }

  setLoading(true);
  try {
    const updated = await api("PUT", `/flights/${flightId}`, payload);
    toast(`Vuelo ${updated.flight_number} actualizado.`, "success");
    elements.editDialog.close();
    await Promise.all([loadFlights(), loadStats()]);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(false);
  }
}

async function handleDelete(flightId) {
  const flight = state.flights.find((item) => item.id === Number(flightId));
  const label = flight ? `${flight.flight_number} (${flight.origin}→${flight.destination})` : `id ${flightId}`;

  // Confirmación explícita antes de una operación destructiva.
  if (!window.confirm(`¿Eliminar el vuelo ${label}? Esta acción no se puede deshacer.`)) {
    return;
  }

  setLoading(true);
  try {
    await api("DELETE", `/flights/${flightId}`);
    toast("Vuelo eliminado.", "success");
    await Promise.all([loadFlights(), loadStats()]);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(false);
  }
}

/* -------------------------------------------------------------------------
 * Inicialización
 * ------------------------------------------------------------------------- */

function collectFilters() {
  state.filters = {
    search: elements.filterSearch.value,
    origin: elements.filterOrigin.value,
    destination: elements.filterDestination.value,
    status: elements.filterStatus.value,
  };
}

function wireEvents() {
  elements.refreshBtn.addEventListener("click", () => {
    loadFlights();
    loadStats();
  });

  elements.filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    collectFilters();
    loadFlights();
  });

  elements.clearFilters.addEventListener("click", () => {
    elements.filterForm.reset();
    collectFilters();
    loadFlights();
  });

  elements.createForm.addEventListener("submit", handleCreate);
  elements.editForm.addEventListener("submit", handleEdit);
  elements.editCancel.addEventListener("click", () => elements.editDialog.close());

  // Delegación de eventos para los botones dinámicos de la tabla.
  elements.flightsBody.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    if (button.dataset.action === "edit") {
      const flight = state.flights.find(
        (item) => item.id === Number(button.dataset.id)
      );
      if (flight) openEditDialog(flight);
    } else if (button.dataset.action === "delete") {
      handleDelete(button.dataset.id);
    }
  });
}

async function init() {
  ["apiStatus", "statTotal", "statScheduled", "statBoarding", "statDelayed",
   "flightsBody", "emptyState", "loadingOverlay", "toastContainer",
   "refreshBtn", "filterForm", "filterSearch", "filterOrigin",
   "filterDestination", "filterStatus", "clearFilters",
   "createForm", "editDialog", "editForm", "editCancel", "editId"]
    .forEach((id) => {
      elements[toCamelCase(id)] = document.getElementById(id);
    });

  wireEvents();
  elements.createForm.departure_time.value = defaultFormTime(1);
  elements.createForm.arrival_time.value = defaultFormTime(5);

  const flightsOk = await loadFlights();
  await loadStats();
  renderApiStatus(flightsOk);
}

function toCamelCase(id) {
  return id.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

document.addEventListener("DOMContentLoaded", init);
