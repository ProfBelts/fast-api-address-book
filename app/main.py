"""Address book API: create, update, delete and search addresses by distance."""

import logging
import sqlite3
from contextlib import asynccontextmanager
from math import asin, cos, radians, sin, sqrt
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from app.database import get_db, init_db
from app.schemas import Address, AddressIn, NearbyAddress, NearbyQuery

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("address_book")

EARTH_RADIUS_KM = 6371.0088

Db = Annotated[sqlite3.Connection, Depends(get_db)]


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle (haversine) distance between two coordinates, in kilometers."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, h)))  # min() guards float rounding


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database ready")
    yield


app = FastAPI(title="Address Book API", lifespan=lifespan)


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Address not found")


@app.post("/addresses", response_model=Address, status_code=201)
def create_address(body: AddressIn, db: Db):
    cursor = db.execute(
        "INSERT INTO addresses (address, latitude, longitude) VALUES (?, ?, ?)",
        (body.address, body.latitude, body.longitude),
    )
    logger.info("Created address id=%s", cursor.lastrowid)
    return {"id": cursor.lastrowid, **body.model_dump()}


@app.get("/addresses", response_model=list[Address])
def list_addresses(db: Db):
    return [dict(row) for row in db.execute("SELECT * FROM addresses ORDER BY id")]


# Declared before /addresses/{address_id} so "nearby" is not parsed as an ID.
@app.get("/addresses/nearby", response_model=list[NearbyAddress])
def nearby_addresses(query: Annotated[NearbyQuery, Query()], db: Db):
    """List addresses within radius_km of the given coordinates, nearest first."""
    # Scans every row: fine for a small address book. Add a bounding-box WHERE clause if it grows.
    results = []
    for row in db.execute("SELECT * FROM addresses"):
        distance = distance_km(query.latitude, query.longitude, row["latitude"], row["longitude"])
        if distance <= query.radius_km:
            results.append(dict(row, distance_km=distance))
    return sorted(results, key=lambda address: address["distance_km"])


@app.get("/addresses/{address_id}", response_model=Address)
def get_address(address_id: int, db: Db):
    row = db.execute("SELECT * FROM addresses WHERE id = ?", (address_id,)).fetchone()
    if row is None:
        raise not_found()
    return dict(row)


@app.put("/addresses/{address_id}", response_model=Address)
def update_address(address_id: int, body: AddressIn, db: Db):
    cursor = db.execute(
        "UPDATE addresses SET address = ?, latitude = ?, longitude = ? WHERE id = ?",
        (body.address, body.latitude, body.longitude, address_id),
    )
    if cursor.rowcount == 0:
        raise not_found()
    logger.info("Updated address id=%s", address_id)
    return {"id": address_id, **body.model_dump()}


@app.delete("/addresses/{address_id}", status_code=204)
def delete_address(address_id: int, db: Db):
    if db.execute("DELETE FROM addresses WHERE id = ?", (address_id,)).rowcount == 0:
        raise not_found()
    logger.info("Deleted address id=%s", address_id)
