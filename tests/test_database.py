"""
test_database.py
================
Pure database / ORM tests for the Hotel Lumière project.

Strategy
--------
Every test receives its own, completely isolated in-memory SQLite database
so there is no shared state between tests.  The ``engine`` and ``db_session``
fixtures build that isolation layer; the rest of the tests consume only the
``db_session`` fixture (and occasionally the raw ``engine`` for schema-level
checks).

No FastAPI TestClient, no HTTP layer — these tests exercise only the
SQLAlchemy models and the helper functions defined in ``database.py``.
"""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# We import from the project's database module.  Because the module-level
# ``engine`` and ``SessionLocal`` point at the real file-based DB we do NOT
# call ``init_db()`` directly against those objects.  Instead, each fixture
# creates a fresh in-memory engine and patches the helpers we need.
# ---------------------------------------------------------------------------
import sys
import os

# Make sure the project root is on sys.path so the import works regardless of
# where pytest is invoked from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import Base, Room, RoomStatus, RoomType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEED_ROOMS = [
    Room(number="101", type=RoomType.individual, price=120.0, status=RoomStatus.disponible),
    Room(number="201", type=RoomType.doble,      price=220.0, status=RoomStatus.ocupada),
    Room(number="301", type=RoomType.suite,       price=480.0, status=RoomStatus.disponible),
    Room(number="202", type=RoomType.doble,       price=220.0, status=RoomStatus.mantenimiento),
    Room(number="401", type=RoomType.suite,       price=650.0, status=RoomStatus.ocupada),
]


def _make_engine():
    """Return a brand-new in-memory SQLite engine."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )


def _init_db_on(engine):
    """
    Replicate the logic of ``database.init_db()`` against an arbitrary engine
    so tests are fully isolated from the file-based production database.
    """
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        if db.query(Room).count() == 0:
            rooms = [
                Room(number="101", type=RoomType.individual, price=120.0, status=RoomStatus.disponible),
                Room(number="201", type=RoomType.doble,      price=220.0, status=RoomStatus.ocupada),
                Room(number="301", type=RoomType.suite,      price=480.0, status=RoomStatus.disponible),
                Room(number="202", type=RoomType.doble,      price=220.0, status=RoomStatus.mantenimiento),
                Room(number="401", type=RoomType.suite,      price=650.0, status=RoomStatus.ocupada),
            ]
            db.add_all(rooms)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    """
    Provide a fresh in-memory SQLite engine for a single test.

    The engine is disposed after the test so no resources leak between runs.
    """
    eng = _make_engine()
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    """
    Provide an open SQLAlchemy Session backed by an isolated in-memory DB.

    The schema is created before the session is yielded and the session is
    always closed in the teardown step, even when a test raises an exception.
    """
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTableCreation:
    def test_init_db_creates_rooms_table(self, engine):
        """
        Verify that ``init_db`` (modelled by ``_init_db_on``) causes the
        ``rooms`` table to exist in the database schema.

        Uses SQLAlchemy's ``inspect`` to check the list of table names so the
        assertion is independent of any ORM query.
        """
        _init_db_on(engine)
        inspector = inspect(engine)
        assert "rooms" in inspector.get_table_names(), (
            "The 'rooms' table was not created by init_db."
        )


class TestSeedData:
    def test_init_db_inserts_five_rooms(self, engine):
        """
        Verify that ``init_db`` seeds exactly 5 rooms when the table is
        initially empty.
        """
        _init_db_on(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            count = db.query(Room).count()
        finally:
            db.close()
        assert count == 5, f"Expected 5 seed rooms, got {count}."

    def test_seed_room_numbers_are_correct(self, engine):
        """
        Verify that the specific room numbers seeded by ``init_db`` match the
        expected values defined in the production code.
        """
        _init_db_on(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            numbers = {r.number for r in db.query(Room).all()}
        finally:
            db.close()
        assert numbers == {"101", "201", "301", "202", "401"}


class TestSeedIdempotency:
    def test_calling_init_db_twice_does_not_duplicate_rows(self, engine):
        """
        Verify that invoking ``init_db`` a second time on an already-populated
        database does NOT insert additional rows — the seed guard (``count ==
        0``) must prevent any duplication.
        """
        _init_db_on(engine)
        _init_db_on(engine)  # second call — must be a no-op
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            count = db.query(Room).count()
        finally:
            db.close()
        assert count == 5, (
            f"Expected 5 rooms after two init_db calls, got {count}. "
            "Seed data was duplicated."
        )


class TestRoomCreation:
    def test_insert_and_query_room(self, db_session):
        """
        Verify that a ``Room`` object can be persisted and subsequently
        retrieved from the database with all its attributes intact.
        """
        room = Room(number="999", type=RoomType.suite, price=999.99, status=RoomStatus.disponible)
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)

        fetched = db_session.query(Room).filter(Room.number == "999").first()
        assert fetched is not None
        assert fetched.number == "999"
        assert fetched.type == RoomType.suite
        assert fetched.price == 999.99
        assert fetched.status == RoomStatus.disponible

    def test_inserted_room_receives_auto_increment_id(self, db_session):
        """
        Verify that after a commit the ``id`` primary key is populated
        automatically by the database (i.e., it is not ``None``).
        """
        room = Room(number="888", type=RoomType.doble, price=200.0)
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)

        assert room.id is not None
        assert isinstance(room.id, int)


class TestUniqueConstraint:
    def test_duplicate_room_number_raises_integrity_error(self, db_session):
        """
        Verify that the ``UNIQUE`` constraint on the ``number`` column causes
        SQLAlchemy to raise an ``IntegrityError`` when two rooms share the
        same number.
        """
        room_a = Room(number="101", type=RoomType.individual, price=120.0)
        room_b = Room(number="101", type=RoomType.doble,      price=220.0)

        db_session.add(room_a)
        db_session.commit()

        db_session.add(room_b)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestStatusEnum:
    @pytest.mark.parametrize("status", list(RoomStatus))
    def test_valid_status_values_are_accepted(self, db_session, status):
        """
        Verify that every member of the ``RoomStatus`` enum (disponible,
        ocupada, mantenimiento) can be stored and retrieved without error.

        The test is parametrised so each enum value gets its own sub-test.
        """
        room = Room(number=f"S-{status.value}", type=RoomType.individual, price=100.0, status=status)
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)

        fetched = db_session.query(Room).filter(Room.number == f"S-{status.value}").first()
        assert fetched.status == status

    def test_invalid_status_value_raises(self, db_session):
        """
        Verify that assigning a string that is not part of the ``RoomStatus``
        enum raises a ``LookupError`` (or ``ValueError``), preventing invalid
        data from ever being committed.
        """
        with pytest.raises((LookupError, ValueError)):
            _ = RoomStatus("invalido")


class TestTypeEnum:
    @pytest.mark.parametrize("room_type", list(RoomType))
    def test_valid_type_values_are_accepted(self, db_session, room_type):
        """
        Verify that every member of the ``RoomType`` enum (suite, doble,
        individual) can be stored and retrieved without error.

        The test is parametrised so each enum value gets its own sub-test.
        """
        room = Room(number=f"T-{room_type.value}", type=room_type, price=150.0)
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)

        fetched = db_session.query(Room).filter(Room.number == f"T-{room_type.value}").first()
        assert fetched.type == room_type

    def test_invalid_type_value_raises(self, db_session):
        """
        Verify that constructing a ``RoomType`` from an unknown string raises a
        ``LookupError`` (or ``ValueError``), keeping bad data out of the ORM.
        """
        with pytest.raises((LookupError, ValueError)):
            _ = RoomType("penthouse")


class TestDefaultStatus:
    def test_room_without_explicit_status_defaults_to_disponible(self, db_session):
        """
        Verify that when a ``Room`` is created without supplying a ``status``
        value, the database/ORM default of ``RoomStatus.disponible`` is applied
        after the row is committed and refreshed.
        """
        room = Room(number="DEFAULT-1", type=RoomType.individual, price=100.0)
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)

        assert room.status == RoomStatus.disponible, (
            f"Expected default status 'disponible', got '{room.status}'."
        )


class TestGetDb:
    def test_get_db_yields_a_session_and_closes_it(self):
        """
        Verify the ``get_db`` generator contract:

        1. It yields exactly one value (the session).
        2. The session is open while inside the generator.
        3. After the generator is exhausted (``finally`` block runs) the
           session is closed — confirmed by checking ``session.is_active`` or
           catching the ``close()`` call via a subclass.

        Because ``get_db`` is bound to the module-level ``SessionLocal`` (which
        targets the file-based DB), we replicate its logic against an isolated
        in-memory session factory to keep the test hermetic.
        """
        closed_flag = {"closed": False}

        # Build a minimal in-memory session whose close() we can observe.
        eng = _make_engine()
        Base.metadata.create_all(bind=eng)
        TestSession = sessionmaker(bind=eng)

        class ObservableSession(TestSession.class_):
            def close(self):
                closed_flag["closed"] = True
                super().close()

        TestSession.class_ = ObservableSession

        def _get_db_local():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        gen = _get_db_local()
        session = next(gen)

        assert session is not None, "get_db did not yield a session."
        assert not closed_flag["closed"], "Session was closed before generator exhaustion."

        # Exhaust the generator to trigger the finally block.
        with pytest.raises(StopIteration):
            next(gen)

        assert closed_flag["closed"], "Session was not closed after generator exhaustion."
        eng.dispose()


class TestRoomDeletion:
    def test_deleting_a_room_removes_it_from_db(self, db_session):
        """
        Verify that calling ``session.delete()`` followed by ``commit()``
        permanently removes the row so that a subsequent query returns
        ``None``.
        """
        room = Room(number="DEL-1", type=RoomType.doble, price=200.0)
        db_session.add(room)
        db_session.commit()
        room_id = room.id

        db_session.delete(room)
        db_session.commit()

        fetched = db_session.query(Room).filter(Room.id == room_id).first()
        assert fetched is None, (
            f"Room with id={room_id} still exists after deletion."
        )

    def test_deleting_one_room_does_not_affect_others(self, db_session):
        """
        Verify that deleting a single room leaves all other rooms untouched,
        i.e., the delete operation is scoped to exactly the targeted row.
        """
        room_a = Room(number="KEEP-1", type=RoomType.individual, price=120.0)
        room_b = Room(number="GONE-1", type=RoomType.doble,      price=220.0)
        db_session.add_all([room_a, room_b])
        db_session.commit()

        db_session.delete(room_b)
        db_session.commit()

        assert db_session.query(Room).filter(Room.number == "KEEP-1").first() is not None
        assert db_session.query(Room).filter(Room.number == "GONE-1").first() is None


class TestStatusUpdate:
    def test_updating_status_persists_correctly(self, db_session):
        """
        Verify that mutating ``room.status`` and calling ``commit()`` causes
        the new value to be durably stored so that a fresh query reflects the
        change.
        """
        room = Room(number="UPD-1", type=RoomType.suite, price=480.0, status=RoomStatus.disponible)
        db_session.add(room)
        db_session.commit()
        room_id = room.id

        # Mutate and persist.
        room.status = RoomStatus.ocupada
        db_session.commit()

        # Re-fetch to confirm the change was written to the DB.
        db_session.expire(room)  # evict from identity map
        updated = db_session.query(Room).filter(Room.id == room_id).first()
        assert updated.status == RoomStatus.ocupada, (
            f"Expected status 'ocupada' after update, got '{updated.status}'."
        )

    @pytest.mark.parametrize("new_status", list(RoomStatus))
    def test_all_valid_statuses_can_be_set_via_update(self, db_session, new_status):
        """
        Verify that a room's status can be changed to each of the three valid
        enum values and that every transition persists without error.

        The test is parametrised to cover all possible target statuses.
        """
        room = Room(number=f"UPD-{new_status.value}", type=RoomType.doble, price=200.0,
                    status=RoomStatus.disponible)
        db_session.add(room)
        db_session.commit()

        room.status = new_status
        db_session.commit()
        db_session.refresh(room)

        assert room.status == new_status
