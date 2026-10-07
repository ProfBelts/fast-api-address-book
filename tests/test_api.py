import math

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import EARTH_RADIUS_KM, app, distance_km

MANILA = {"address": "Manila City Hall", "latitude": 14.5896, "longitude": 120.9816}
CEBU = {"address": "Cebu City", "latitude": 10.3157, "longitude": 123.8854}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        yield client


def test_crud(client):
    created = client.post("/addresses", json={**MANILA, "address": "  Manila City Hall  "})
    assert created.status_code == 201
    assert created.json() == {"id": 1, **MANILA}  # whitespace trimmed
    assert client.get("/addresses/1").json() == {"id": 1, **MANILA}
    assert client.get("/addresses").json() == [{"id": 1, **MANILA}]

    assert client.put("/addresses/1", json=CEBU).json() == {"id": 1, **CEBU}
    assert client.get("/addresses/1").json() == {"id": 1, **CEBU}

    assert client.delete("/addresses/1").status_code == 204
    assert client.get("/addresses/1").status_code == 404
    assert client.put("/addresses/1", json=CEBU).status_code == 404
    assert client.delete("/addresses/1").status_code == 404


@pytest.mark.parametrize(
    "change",
    [
        {"address": "   "},
        {"address": "x" * 501},
        {"latitude": 90.1},
        {"latitude": -90.1},
        {"longitude": 180.1},
        {"longitude": -180.1},
        {"latitude": None},
    ],
)
def test_invalid_address_rejected(client, change):
    assert client.post("/addresses", json={**MANILA, **change}).status_code == 422
    assert client.get("/addresses").json() == []


def test_nearby(client):
    for longitude in (2, 1, 0):
        client.post("/addresses", json={"address": f"lon {longitude}", "latitude": 0, "longitude": longitude})
    one_degree = distance_km(0, 0, 0, 1)  # ~111.2 km

    found = client.get("/addresses/nearby", params={"latitude": 0, "longitude": 0, "radius_km": one_degree})
    assert [a["address"] for a in found.json()] == ["lon 0", "lon 1"]  # nearest first, edge included
    assert found.json()[1]["distance_km"] == pytest.approx(111.195, abs=0.001)

    for bad in ({"radius_km": 0}, {"latitude": 91}, {"longitude": "nan"}):
        params = {"latitude": 0, "longitude": 0, "radius_km": 1, **bad}
        assert client.get("/addresses/nearby", params=params).status_code == 422


def test_distance():
    assert distance_km(0, 179.9, 0, -179.9) == pytest.approx(22.239, abs=0.001)  # across date line
    assert distance_km(0, 0, 0, 180) == pytest.approx(math.pi * EARTH_RADIUS_KM)  # antipodes
