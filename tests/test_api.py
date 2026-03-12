"""
Test suite for Hotel Lumière FastAPI endpoints.

Uses an in-memory SQLite database so the real hotel.db is never touched.
Each test gets a fresh database via the client fixture, ensuring full isolation.
"""

import sys
import os

# Make sure the project root is importable when running pytest from any cwd.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db, RoomType, RoomStatus
from main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# StaticPool forces SQLAlchemy to reuse a single in-memory connection for the
# lifetime of the engine.  Without it every new Session would open a new
# sqlite3 connection, which in ":memory:" mode gives an entirely empty DB
# (tables created on one connection are not visible on another).
_TEST_ENGINE = None


@pytest.fixture()
def client():
    """
    Provide a TestClient backed by a fresh in-memory SQLite database.

    StaticPool is used so that every Session shares the same underlying
    connection — a requirement for SQLite :memory: databases where each
    connection otherwise gets its own isolated, empty database.

    A new engine is created for every test function so that no state leaks
    between tests.  The get_db dependency is overridden for the duration of
    the test and restored afterwards.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables in the shared in-memory connection (no sample data).
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    # Tear down: remove the override and drop all tables.
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _room_payload(number="101", room_type="individual", price=100.0, status=None):
    """Return a minimal valid room creation payload."""
    payload = {"number": number, "type": room_type, "price": price}
    if status is not None:
        payload["status"] = status
    return payload


# ---------------------------------------------------------------------------
# GET /api/rooms
# ---------------------------------------------------------------------------

class TestListRooms:

    def test_list_rooms_empty(self, client):
        """When the DB has no rooms the endpoint must return an empty list."""
        response = client.get("/api/rooms")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_rooms_returns_all(self, client):
        """All rooms created in the DB are returned without filtering."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0))
        client.post("/api/rooms", json=_room_payload("301", "suite", 400.0))

        response = client.get("/api/rooms")
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_list_rooms_ordered_by_number(self, client):
        """Rooms must come back sorted ascending by room number."""
        client.post("/api/rooms", json=_room_payload("301", "suite", 400.0))
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0))

        response = client.get("/api/rooms")
        numbers = [r["number"] for r in response.json()]
        assert numbers == sorted(numbers)

    def test_list_rooms_filter_by_status_disponible(self, client):
        """Only rooms with status=disponible are returned when that filter is applied."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "disponible"))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0, "ocupada"))
        client.post("/api/rooms", json=_room_payload("301", "suite", 400.0, "mantenimiento"))

        response = client.get("/api/rooms?status=disponible")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "disponible"

    def test_list_rooms_filter_by_status_ocupada(self, client):
        """Only rooms with status=ocupada are returned when that filter is applied."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "disponible"))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0, "ocupada"))

        response = client.get("/api/rooms?status=ocupada")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "ocupada"

    def test_list_rooms_filter_by_status_mantenimiento(self, client):
        """Only rooms with status=mantenimiento are returned when that filter is applied."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "mantenimiento"))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0, "disponible"))

        response = client.get("/api/rooms?status=mantenimiento")
        assert response.status_code == 200
        data = response.json()
        assert all(r["status"] == "mantenimiento" for r in data)

    def test_list_rooms_filter_no_match_returns_empty(self, client):
        """A valid status filter that matches no rooms must return an empty list."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "disponible"))

        response = client.get("/api/rooms?status=ocupada")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_rooms_invalid_status_returns_422(self, client):
        """An unrecognised status value must be rejected with HTTP 422."""
        response = client.get("/api/rooms?status=invalido")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/rooms
# ---------------------------------------------------------------------------

class TestCreateRoom:

    def test_create_room_success(self, client):
        """A valid payload creates a room and returns 201 with the new room data."""
        payload = _room_payload("101", "suite", 350.0, "disponible")
        response = client.post("/api/rooms", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["number"] == "101"
        assert data["type"] == "suite"
        assert data["price"] == 350.0
        assert data["status"] == "disponible"
        assert "id" in data

    def test_create_room_default_status_is_disponible(self, client):
        """When status is omitted the created room must default to 'disponible'."""
        payload = {"number": "202", "type": "doble", "price": 180.0}
        response = client.post("/api/rooms", json=payload)

        assert response.status_code == 201
        assert response.json()["status"] == "disponible"

    def test_create_room_duplicate_number_returns_400(self, client):
        """Creating two rooms with the same number must return HTTP 400."""
        payload = _room_payload("101", "individual", 100.0)
        client.post("/api/rooms", json=payload)

        response = client.post("/api/rooms", json=payload)
        assert response.status_code == 400
        assert "101" in response.json()["detail"]

    def test_create_room_missing_number_returns_422(self, client):
        """Omitting the required 'number' field must return HTTP 422."""
        response = client.post("/api/rooms", json={"type": "doble", "price": 150.0})
        assert response.status_code == 422

    def test_create_room_missing_type_returns_422(self, client):
        """Omitting the required 'type' field must return HTTP 422."""
        response = client.post("/api/rooms", json={"number": "101", "price": 150.0})
        assert response.status_code == 422

    def test_create_room_missing_price_returns_422(self, client):
        """Omitting the required 'price' field must return HTTP 422."""
        response = client.post("/api/rooms", json={"number": "101", "type": "suite"})
        assert response.status_code == 422

    def test_create_room_zero_price_returns_422(self, client):
        """A price of 0 is not allowed (must be > 0); the endpoint must return 422."""
        payload = {"number": "101", "type": "suite", "price": 0}
        response = client.post("/api/rooms", json=payload)
        assert response.status_code == 422

    def test_create_room_negative_price_returns_422(self, client):
        """A negative price must be rejected with HTTP 422."""
        payload = {"number": "101", "type": "suite", "price": -50.0}
        response = client.post("/api/rooms", json=payload)
        assert response.status_code == 422

    def test_create_room_invalid_type_returns_422(self, client):
        """An unrecognised room type must be rejected with HTTP 422."""
        payload = {"number": "101", "type": "penthouse", "price": 500.0}
        response = client.post("/api/rooms", json=payload)
        assert response.status_code == 422

    def test_create_room_empty_number_returns_422(self, client):
        """An empty string for 'number' (min_length=1) must return HTTP 422."""
        payload = {"number": "", "type": "suite", "price": 300.0}
        response = client.post("/api/rooms", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/rooms/{id}
# ---------------------------------------------------------------------------

class TestUpdateRoomStatus:

    def test_update_room_status_success(self, client):
        """Patching an existing room's status must return 200 with the updated room."""
        create_resp = client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "disponible"))
        room_id = create_resp.json()["id"]

        response = client.patch(f"/api/rooms/{room_id}", json={"status": "ocupada"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == room_id
        assert data["status"] == "ocupada"

    def test_update_room_status_to_mantenimiento(self, client):
        """A room can be moved to 'mantenimiento' status via PATCH."""
        create_resp = client.post("/api/rooms", json=_room_payload("202", "doble", 200.0, "ocupada"))
        room_id = create_resp.json()["id"]

        response = client.patch(f"/api/rooms/{room_id}", json={"status": "mantenimiento"})
        assert response.status_code == 200
        assert response.json()["status"] == "mantenimiento"

    def test_update_room_status_to_disponible(self, client):
        """A room can be moved back to 'disponible' status via PATCH."""
        create_resp = client.post("/api/rooms", json=_room_payload("303", "suite", 400.0, "mantenimiento"))
        room_id = create_resp.json()["id"]

        response = client.patch(f"/api/rooms/{room_id}", json={"status": "disponible"})
        assert response.status_code == 200
        assert response.json()["status"] == "disponible"

    def test_update_room_not_found_returns_404(self, client):
        """PATCH on a non-existent room ID must return HTTP 404."""
        response = client.patch("/api/rooms/99999", json={"status": "ocupada"})
        assert response.status_code == 404

    def test_update_room_invalid_status_returns_422(self, client):
        """PATCH with an unrecognised status value must return HTTP 422."""
        create_resp = client.post("/api/rooms", json=_room_payload("101", "individual", 100.0))
        room_id = create_resp.json()["id"]

        response = client.patch(f"/api/rooms/{room_id}", json={"status": "limpieza"})
        assert response.status_code == 422

    def test_update_room_preserves_other_fields(self, client):
        """PATCH must update only the status; number, type, and price stay the same."""
        payload = _room_payload("505", "suite", 750.0, "disponible")
        create_resp = client.post("/api/rooms", json=payload)
        room_id = create_resp.json()["id"]

        client.patch(f"/api/rooms/{room_id}", json={"status": "ocupada"})

        get_resp = client.get("/api/rooms")
        room = next(r for r in get_resp.json() if r["id"] == room_id)
        assert room["number"] == "505"
        assert room["type"] == "suite"
        assert room["price"] == 750.0


# ---------------------------------------------------------------------------
# DELETE /api/rooms/{id}
# ---------------------------------------------------------------------------

class TestDeleteRoom:

    def test_delete_room_success(self, client):
        """Deleting an existing room must return HTTP 204 with no body."""
        create_resp = client.post("/api/rooms", json=_room_payload("101", "individual", 100.0))
        room_id = create_resp.json()["id"]

        response = client.delete(f"/api/rooms/{room_id}")
        assert response.status_code == 204
        assert response.content == b""

    def test_delete_room_is_actually_removed(self, client):
        """After a successful DELETE the room must no longer appear in GET /api/rooms."""
        create_resp = client.post("/api/rooms", json=_room_payload("101", "individual", 100.0))
        room_id = create_resp.json()["id"]

        client.delete(f"/api/rooms/{room_id}")

        list_resp = client.get("/api/rooms")
        ids = [r["id"] for r in list_resp.json()]
        assert room_id not in ids

    def test_delete_room_not_found_returns_404(self, client):
        """DELETE on a non-existent room ID must return HTTP 404."""
        response = client.delete("/api/rooms/99999")
        assert response.status_code == 404

    def test_delete_room_second_attempt_returns_404(self, client):
        """Attempting to delete the same room twice must fail with 404 on the second call."""
        create_resp = client.post("/api/rooms", json=_room_payload("101", "individual", 100.0))
        room_id = create_resp.json()["id"]

        client.delete(f"/api/rooms/{room_id}")
        response = client.delete(f"/api/rooms/{room_id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/stats
# ---------------------------------------------------------------------------

class TestGetStats:

    def test_stats_empty_db(self, client):
        """Stats on an empty database must show all zeros."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["disponible"] == 0
        assert data["ocupada"] == 0
        assert data["mantenimiento"] == 0
        assert data["ingresos_estimados"] == 0.0

    def test_stats_correct_counts(self, client):
        """Stats must correctly count rooms in each status bucket."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "disponible"))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0, "disponible"))
        client.post("/api/rooms", json=_room_payload("301", "suite", 400.0, "ocupada"))
        client.post("/api/rooms", json=_room_payload("401", "suite", 650.0, "mantenimiento"))

        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert data["disponible"] == 2
        assert data["ocupada"] == 1
        assert data["mantenimiento"] == 1

    def test_stats_ingresos_estimados_only_from_ocupada(self, client):
        """ingresos_estimados must sum the prices of 'ocupada' rooms only."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "disponible"))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0, "ocupada"))
        client.post("/api/rooms", json=_room_payload("301", "suite", 400.0, "ocupada"))
        client.post("/api/rooms", json=_room_payload("401", "suite", 650.0, "mantenimiento"))

        response = client.get("/api/stats")
        data = response.json()
        # Only rooms 201 (200.0) and 301 (400.0) are ocupada → 600.0
        assert data["ingresos_estimados"] == pytest.approx(600.0)

    def test_stats_ingresos_estimados_zero_when_no_ocupadas(self, client):
        """ingresos_estimados must be 0.0 when no rooms have status 'ocupada'."""
        client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "disponible"))
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0, "mantenimiento"))

        response = client.get("/api/stats")
        assert response.json()["ingresos_estimados"] == 0.0

    def test_stats_total_matches_room_count(self, client):
        """The 'total' field must equal the number of rooms regardless of status."""
        for i in range(5):
            client.post("/api/rooms", json=_room_payload(str(100 + i), "individual", 80.0))

        response = client.get("/api/stats")
        assert response.json()["total"] == 5

    def test_stats_reflects_deletion(self, client):
        """Stats must update correctly after a room is deleted."""
        r1 = client.post("/api/rooms", json=_room_payload("101", "individual", 100.0, "ocupada")).json()
        client.post("/api/rooms", json=_room_payload("201", "doble", 200.0, "disponible"))

        client.delete(f"/api/rooms/{r1['id']}")

        data = client.get("/api/stats").json()
        assert data["total"] == 1
        assert data["ocupada"] == 0
        assert data["ingresos_estimados"] == 0.0

    def test_stats_reflects_status_update(self, client):
        """Stats must reflect the new status after a room is patched."""
        room = client.post("/api/rooms", json=_room_payload("101", "individual", 300.0, "disponible")).json()

        client.patch(f"/api/rooms/{room['id']}", json={"status": "ocupada"})

        data = client.get("/api/stats").json()
        assert data["disponible"] == 0
        assert data["ocupada"] == 1
        assert data["ingresos_estimados"] == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# GET /  (static frontend)
# ---------------------------------------------------------------------------

class TestIndexPage:

    def test_index_returns_200(self, client):
        """GET / must respond with HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_returns_html_content_type(self, client):
        """GET / must serve an HTML document (Content-Type: text/html)."""
        response = client.get("/")
        assert "text/html" in response.headers.get("content-type", "")

    def test_index_body_is_not_empty(self, client):
        """GET / must return a non-empty response body."""
        response = client.get("/")
        assert len(response.content) > 0
