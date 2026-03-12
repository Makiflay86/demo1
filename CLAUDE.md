# CLAUDE.md — Hotel Lumière

## Idioma

**El idioma principal y único de este proyecto es el español.**

- Todo el código nuevo (nombres de variables, funciones, clases, comentarios, docstrings, mensajes de error, tests) debe escribirse en español.
- Las únicas excepciones permitidas son palabras técnicas sin traducción natural: `id`, `status`, `endpoint`, `commit`, `query`, nombres de librerías externas y similares.
- Si Claude genera código en inglés sin que se le pida explícitamente, es un error.

---

## Descripción

Sistema de gestión de habitaciones para el **Hotel Lumière**. Permite crear, reservar, liberar y eliminar habitaciones, con estadísticas en tiempo real.

Stack completo en un solo proceso:
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: HTML/CSS/JS estático servido por el mismo servidor FastAPI
- **Puerto**: `http://localhost:8000`

---

## Arquitectura

```
  Navegador (HTML + CSS + JS)
        │
        │  HTTP (fetch /api/...)
        ▼
  ┌─────────────────────────────┐
  │         main.py             │  ← FastAPI: rutas API + sirve estáticos
  │                             │
  │  Schemas Pydantic           │  ← validación de entrada/salida
  └──────────┬──────────────────┘
             │  SQLAlchemy ORM
             ▼
  ┌─────────────────────────────┐
  │        database.py          │  ← modelos, enums, sesión, seed
  └──────────┬──────────────────┘
             │
             ▼
          hotel.db               ← SQLite (generado automáticamente)
```

El frontend es **completamente estático**: no hay framework JS, no hay build step, no hay SSR. El servidor FastAPI monta `/static` y devuelve `index.html` en la raíz.

---

## Estructura de archivos

```
demo-1/
├── main.py              # App FastAPI: endpoints API + montaje de estáticos
├── database.py          # Motor SQLite, modelos ORM, enums, seed inicial
├── requirements.txt     # Dependencias Python
├── hotel.db             # Base de datos SQLite (auto-generada, no commitear)
├── venv/                # Entorno virtual Python (no commitear)
│
├── static/
│   ├── index.html       # Estructura HTML de la SPA
│   ├── style.css        # Tema oscuro/dorado: variables CSS, animaciones
│   └── app.js           # Lógica frontend: fetch API, render, modales, filtros
│
└── tests/
    ├── test_api.py      # 38 tests de endpoints HTTP con TestClient
    └── test_database.py # 23 tests de capa ORM con SQLite en memoria
```

---

## Modelos de datos

### Habitación (`Room`)

| Campo    | Tipo    | Restricciones              |
|----------|---------|----------------------------|
| `id`     | int     | PK, autoincremento         |
| `number` | string  | único, no nulo             |
| `type`   | enum    | `suite` / `doble` / `individual` |
| `price`  | float   | > 0                        |
| `status` | enum    | `disponible` / `ocupada` / `mantenimiento` (default: `disponible`) |

### Seed inicial

Al arrancar por primera vez se insertan 5 habitaciones de ejemplo:

| Número | Tipo       | Precio  | Estado         |
|--------|------------|---------|----------------|
| 101    | individual | €120    | disponible     |
| 201    | doble      | €220    | ocupada        |
| 202    | doble      | €220    | mantenimiento  |
| 301    | suite      | €480    | disponible     |
| 401    | suite      | €650    | ocupada        |

---

## Endpoints de la API

Todos los endpoints JSON están bajo el prefijo `/api`.

### `GET /api/rooms`
Lista todas las habitaciones ordenadas por número.

**Query params opcionales:**
- `status` — filtra por estado (`disponible`, `ocupada`, `mantenimiento`)

**Respuesta 200:**
```json
[
  { "id": 1, "number": "101", "type": "individual", "price": 120.0, "status": "disponible" }
]
```

---

### `POST /api/rooms`
Crea una nueva habitación.

**Body JSON:**
```json
{
  "number": "305",
  "type": "suite",
  "price": 500.0,
  "status": "disponible"
}
```
- `status` es opcional (default: `disponible`)
- Devuelve `400` si el número de habitación ya existe
- Devuelve `422` si faltan campos o los valores son inválidos

**Respuesta 201:** objeto `RoomOut` completo.

---

### `PATCH /api/rooms/{room_id}`
Cambia el estado de una habitación.

**Body JSON:**
```json
{ "status": "ocupada" }
```
- Devuelve `404` si el ID no existe
- Devuelve `422` si el status es inválido

**Respuesta 200:** objeto `RoomOut` actualizado.

---

### `DELETE /api/rooms/{room_id}`
Elimina una habitación permanentemente.

- Devuelve `404` si el ID no existe

**Respuesta 204:** sin cuerpo.

---

### `GET /api/stats`
Devuelve contadores en tiempo real y los ingresos estimados (suma de precios de habitaciones ocupadas).

**Respuesta 200:**
```json
{
  "total": 5,
  "disponible": 2,
  "ocupada": 2,
  "mantenimiento": 1,
  "ingresos_estimados": 870.0
}
```

---

### `GET /`
Devuelve `static/index.html`. Punto de entrada de la interfaz web.

---

## Comandos

### Instalar dependencias (primera vez)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Arrancar el servidor

```bash
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

O con recarga automática en desarrollo:

```bash
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

La app queda disponible en `http://localhost:8000`.

### Ejecutar todos los tests

```bash
./venv/bin/pytest tests/ -v
```

### Ejecutar solo tests de API o de base de datos

```bash
./venv/bin/pytest tests/test_api.py -v
./venv/bin/pytest tests/test_database.py -v
```

### Borrar la base de datos y empezar limpio

```bash
rm hotel.db
```
La próxima vez que arranque el servidor, `init_db()` recreará la tabla e insertará el seed.

---

## Convenciones de código

### General
- **Idioma: español** en todo lo que se escriba (ver sección Idioma arriba).
- Sin comentarios obvios. Solo comentar lo que no es evidente.
- No añadir docstrings a funciones simples. Solo donde la lógica lo justifique.
- No sobre-ingeniería: si algo se usa una sola vez, no abstraerlo.

### Python (backend)
- Formato: [PEP 8](https://peps.python.org/pep-0008/). Indentación de 4 espacios.
- Los schemas Pydantic viven en `main.py` junto a los endpoints que los usan.
- Toda validación de entrada se hace en los schemas Pydantic, no en los endpoints.
- Los endpoints no hacen lógica de negocio compleja: delegan en la sesión SQLAlchemy.
- Usar `Depends(get_db)` para inyectar la sesión en cada endpoint — nunca instanciar `SessionLocal` directamente dentro de un endpoint.
- Los errores HTTP se lanzan con `raise HTTPException(código, "mensaje en español")`.

### Tests
- Cada test es independiente: no depende del orden de ejecución ni del estado de otro test.
- Los tests de API usan SQLite en memoria con `StaticPool` para aislar la BD real (`hotel.db`).
- Los tests de base de datos no importan ni usan `TestClient`.
- Los nombres de los tests describen qué se verifica: `test_crear_habitacion_duplicada_devuelve_400`.
- No mockear SQLAlchemy ni FastAPI internals — usar la pila real con BD en memoria.

### JavaScript (frontend)
- Vanilla JS, sin frameworks. Sin build step.
- Todas las llamadas HTTP pasan por `apiFetch()` — nunca usar `fetch` directamente.
- El HTML de las tarjetas de habitaciones se genera dinámicamente en `renderRooms()`.
- Los modales se controlan añadiendo/quitando la clase CSS `hidden`.

### CSS
- Variables de color definidas en `:root` — nunca usar valores de color hardcodeados fuera de `:root`.
- Las animaciones van en bloques `@keyframes` al final de su sección.
- El estado visual de las tarjetas se controla con `data-status` en el atributo HTML.

---

## Lo que NO hacer

- No commitear `hotel.db` ni `venv/`.
- No usar `db.add()` sin `db.commit()` después.
- No instanciar `SessionLocal()` fuera de `get_db()` o `init_db()`.
- No añadir endpoints que no tengan su test correspondiente.
- No cambiar el puerto por defecto (8000) sin actualizar este documento.
- No escribir código, comentarios ni mensajes en inglés.
