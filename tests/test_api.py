import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.api import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "EnergyPlus HVAC Sizing API",
    }


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }


def test_calculate_valid_request():
    payload = {
        "rooms": [
            {
                "name": "AUTOMATED TEST ROOM",
                "area_m2": 20,
                "volume_m3": 60,
            }
        ]
    }

    response = client.post("/calculate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["engine"] == "EnergyPlus"
    assert data["version"] == "23.2.0"
    assert data["source"] == "epluszsz.csv"
    assert data["zone_count"] == 1
    assert data["timestep_row_count"] == 98

    assert len(data["zones"]) == 1

    zone = data["zones"][0]

    assert zone["zone_name"] == "AUTOMATED TEST ROOM"

    assert "design_conditions" in zone
    assert "heating" in zone
    assert "cooling" in zone
    assert "no_doas" in zone

    assert zone["heating"]["design_load_w"] > 0
    assert zone["cooling"]["sensible_load_w"] > 0


def test_calculate_empty_rooms():
    response = client.post(
        "/calculate",
        json={"rooms": []},
    )

    assert response.status_code == 422


def test_calculate_empty_room_name():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "name": "",
                    "area_m2": 20,
                    "volume_m3": 60,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_zero_area():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "name": "INVALID AREA",
                    "area_m2": 0,
                    "volume_m3": 60,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_zero_volume():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "name": "INVALID VOLUME",
                    "area_m2": 20,
                    "volume_m3": 0,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_missing_rooms():
    response = client.post(
        "/calculate",
        json={},
    )

    assert response.status_code == 422


def test_calculate_missing_room_name():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "area_m2": 20,
                    "volume_m3": 60,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_missing_area():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "name": "MISSING AREA",
                    "volume_m3": 60,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_missing_volume():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "name": "MISSING VOLUME",
                    "area_m2": 20,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_invalid_area_type():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "name": "INVALID AREA TYPE",
                    "area_m2": "twenty",
                    "volume_m3": 60,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_invalid_volume_type():
    response = client.post(
        "/calculate",
        json={
            "rooms": [
                {
                    "name": "INVALID VOLUME TYPE",
                    "area_m2": 20,
                    "volume_m3": "sixty",
                }
            ]
        },
    )

    assert response.status_code == 422


def test_calculate_multiple_rooms():
    payload = {
        "rooms": [
            {
                "name": "AUTOMATED ROOM 1",
                "area_m2": 20,
                "volume_m3": 60,
            },
            {
                "name": "AUTOMATED ROOM 2",
                "area_m2": 30,
                "volume_m3": 90,
            },
        ]
    }

    response = client.post("/calculate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["engine"] == "EnergyPlus"
    assert data["zone_count"] == 2
    assert len(data["zones"]) == 2

    zone_names = [zone["zone_name"] for zone in data["zones"]]

    assert zone_names == [
        "AUTOMATED ROOM 1",
        "AUTOMATED ROOM 2",
    ]

    for zone in data["zones"]:
        assert zone["heating"]["design_load_w"] > 0
        assert zone["cooling"]["sensible_load_w"] > 0


def test_calculate_energyplus_failure(monkeypatch):
    import subprocess

    def mock_run(*args, **kwargs):
        command = args[0]

        if command and "energyplus-23.2.0" in str(command[0]):
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=command,
            )

        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    payload = {
        "rooms": [
            {
                "name": "ENERGYPLUS FAILURE TEST",
                "area_m2": 20,
                "volume_m3": 60,
            }
        ]
    }

    response = client.post("/calculate", json=payload)

    assert response.status_code == 500
    assert response.json() == {
        "detail": "EnergyPlus simulation failed."
    }
