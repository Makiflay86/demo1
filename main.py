from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import os

from database import get_db, init_db, Room, RoomType, RoomStatus

app = FastAPI(title="Hotel Lumière API")


# ── Schemas ──────────────────────────────────────────────────────────────────


class RoomCreate(BaseModel):
    number: str = Field(..., min_length=1)
    type: RoomType
    price: float = Field(..., gt=0)
    status: RoomStatus = RoomStatus.disponible


class RoomUpdate(BaseModel):
    status: RoomStatus


class RoomOut(BaseModel):
    id: int
    number: str
    type: RoomType
    price: float
    status: RoomStatus

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    total: int
    disponible: int
    ocupada: int
    mantenimiento: int
    ingresos_estimados: float


# ── Startup ───────────────────────────────────────────────────────────────────


@app.on_event("startup")
def startup():
    init_db()


# ── API routes ────────────────────────────────────────────────────────────────


@app.get("/api/rooms", response_model=list[RoomOut])
def list_rooms(status: Optional[RoomStatus] = None, db: Session = Depends(get_db)):
    q = db.query(Room)
    if status:
        q = q.filter(Room.status == status)
    return q.order_by(Room.number).all()


@app.post("/api/rooms", response_model=RoomOut, status_code=201)
def create_room(data: RoomCreate, db: Session = Depends(get_db)):
    if db.query(Room).filter(Room.number == data.number).first():
        raise HTTPException(400, f"La habitación {data.number} ya existe.")
    room = Room(**data.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@app.patch("/api/rooms/{room_id}", response_model=RoomOut)
def update_room_status(room_id: int, data: RoomUpdate, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(404, "Habitación no encontrada.")
    room.status = data.status
    db.commit()
    db.refresh(room)
    return room


@app.delete("/api/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(404, "Habitación no encontrada.")
    db.delete(room)
    db.commit()


@app.get("/api/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    rooms = db.query(Room).all()
    ocupadas = [r for r in rooms if r.status == RoomStatus.ocupada]
    return StatsOut(
        total=len(rooms),
        disponible=sum(1 for r in rooms if r.status == RoomStatus.disponible),
        ocupada=len(ocupadas),
        mantenimiento=sum(1 for r in rooms if r.status == RoomStatus.mantenimiento),
        ingresos_estimados=sum(r.price for r in ocupadas),
    )


# ── Static frontend ───────────────────────────────────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(static_dir, "index.html"))
