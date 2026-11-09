"""Tests de non-régression des principales étapes du TP."""
from fastapi.testclient import TestClient
import main


def test_full_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "test.sqlite3")
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        payload = {"tracker_id": "pc-01", "readings": [
            {"bssid": "AA:BB:CC:DD:EE:01", "ssid": "wifi", "rssi": -53},
            {"bssid": "AA:BB:CC:DD:EE:02", "ssid": "wifi", "rssi": -64},
        ]}
        unknown = client.post("/scans", json=payload)
        assert unknown.status_code == 201
        assert unknown.json()["position"] is None
        for id_, x in [("01", 0), ("02", 30)]:
            response = client.post("/access-points", json={
                "bssid": f"AA:BB:CC:DD:EE:{id_}", "ssid": "wifi", "x": x, "y": 4
            })
            assert response.status_code == 201
        result = client.post("/scans", json=payload)
        assert result.status_code == 201
        pos = result.json()["position"]
        assert pos is not None and 0 <= pos["x"] <= 30 and pos["y"] == 4
        assert pos["ap_count"] == 2
        positions = client.get("/trackers/pc-01/positions").json()
        assert len(positions) == 1
        details = client.get(f"/scans/{result.json()['scan_id']}").json()
        assert len(details["readings"]) == 2
        assert details["position"]["x"] == pos["x"]
        assert client.get("/map").status_code == 200
        assert client.get("/trackers").json()[0]["tracker_id"] == "pc-01"
        assert client.post("/scans", json={"tracker_id": "pc-01", "readings": []}).status_code == 422
        assert client.get("/trackers/pc-01/positions?start=2026-11-09T20:00:00Z&end=2026-11-09T10:00:00Z").status_code == 422
