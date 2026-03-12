from sqlalchemy import create_engine, Column, Integer, String, Float, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum

DATABASE_URL = "sqlite:///./hotel.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class RoomType(str, enum.Enum):
    suite = "suite"
    doble = "doble"
    individual = "individual"


class RoomStatus(str, enum.Enum):
    disponible = "disponible"
    ocupada = "ocupada"
    mantenimiento = "mantenimiento"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    type = Column(SAEnum(RoomType), nullable=False)
    price = Column(Float, nullable=False)
    status = Column(SAEnum(RoomStatus), default=RoomStatus.disponible, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Room).count() == 0:
        sample_rooms = [
            Room(number="101", type=RoomType.individual, price=120.0, status=RoomStatus.disponible),
            Room(number="201", type=RoomType.doble, price=220.0, status=RoomStatus.ocupada),
            Room(number="301", type=RoomType.suite, price=480.0, status=RoomStatus.disponible),
            Room(number="202", type=RoomType.doble, price=220.0, status=RoomStatus.mantenimiento),
            Room(number="401", type=RoomType.suite, price=650.0, status=RoomStatus.ocupada),
        ]
        db.add_all(sample_rooms)
        db.commit()
    db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
