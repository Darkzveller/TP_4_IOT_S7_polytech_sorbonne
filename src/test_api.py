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


def test_geographic_access_points_and_route(tmp_path, monkeypatch):
    """Un clic sur la carte envoie un AP géographique ; les scans restent compatibles."""
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "geo.sqlite3")
    with TestClient(main.app) as client:
        for suffix, lat, lon in [("01", 48.8470000, 2.3570000), ("02", 48.8471000, 2.3572000)]:
            r = client.post('/access-points', json={
                'bssid': f'AA:BB:CC:DD:EE:{suffix}',
                'ssid': 'Campus Wi-Fi', 'latitude': lat, 'longitude': lon,
            })
            assert r.status_code == 201, r.text
            assert r.json()['latitude'] == lat
            assert r.json()['x'] is not None
        points = client.get('/access-points').json()
        assert len(points) == 2
        assert all(ap['latitude'] is not None and ap['longitude'] is not None for ap in points)

        for strength in (-48, -72):
            result = client.post('/scans', json={'tracker_id': 'portable-01', 'readings': [
                {'bssid': 'AA:BB:CC:DD:EE:01', 'ssid': 'Campus Wi-Fi', 'rssi': strength},
                {'bssid': 'AA:BB:CC:DD:EE:02', 'ssid': 'Campus Wi-Fi', 'rssi': -60},
            ]})
            assert result.status_code == 201, result.text
            geo = result.json()['position']
            assert geo['latitude'] is not None
            assert 48.8469 <= geo['latitude'] <= 48.8472
            assert 2.3569 <= geo['longitude'] <= 2.3573
            assert geo['ap_count'] == 2
            assert geo['method'] == 'weighted_centroid_rssi_geo'

        history = client.get('/trackers/portable-01/positions').json()
        assert len(history) == 2
        assert history[0]['latitude'] != history[1]['latitude']
        assert 'tile.openstreetmap.org' in client.get('/map').text
        assert 'leaflet@1.9.4' in client.get('/map').text
        assert client.post('/access-points', json={
            'bssid':'AA:BB:CC:DD:EE:FF', 'ssid':'Erreur', 'latitude':48.8
        }).status_code == 422
        assert client.delete('/access-points/AA:BB:CC:DD:EE:01').status_code == 204
        assert len(client.get('/access-points').json()) == 1
        assert len(client.get('/trackers/portable-01/positions').json()) == 2


def test_migration_legacy_sqlite_preserves_records(tmp_path, monkeypatch):
    """La nouvelle version ne supprime ni bornes ni positions X/Y préexistantes."""
    import sqlite3
    db_file = tmp_path / 'existing.sqlite3'
    with sqlite3.connect(db_file) as db:
        db.executescript('''
            CREATE TABLE access_points (bssid TEXT PRIMARY KEY, ssid TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE scans (id INTEGER PRIMARY KEY AUTOINCREMENT, tracker_id TEXT NOT NULL, scanned_at TEXT NOT NULL);
            CREATE TABLE observations (id INTEGER PRIMARY KEY AUTOINCREMENT, scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE, bssid TEXT NOT NULL, ssid TEXT NOT NULL, rssi INTEGER NOT NULL);
            CREATE TABLE positions (id INTEGER PRIMARY KEY AUTOINCREMENT, scan_id INTEGER NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE, tracker_id TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL, ap_count INTEGER NOT NULL, method TEXT NOT NULL, estimated_at TEXT NOT NULL);
            INSERT INTO access_points VALUES ('AA:BB:CC:DD:EE:01', 'Ancien AP', 5, 12, '2026-11-09T00:00:00+00:00');
            INSERT INTO scans VALUES (1, 'ancien-pc', '2026-11-09T00:00:00+00:00');
            INSERT INTO positions VALUES (1, 1, 'ancien-pc', 5, 12, 1, 'weighted_centroid_rssi', '2026-11-09T00:00:00+00:00');
        ''')
    monkeypatch.setattr(main, 'DB_FILE', db_file)
    with TestClient(main.app) as client:
        aps = client.get('/access-points').json()
        assert len(aps) == 1
        assert aps[0]['x'] == 5 and aps[0]['y'] == 12
        assert aps[0]['latitude'] is None
        positions = client.get('/trackers/ancien-pc/positions').json()
        assert len(positions) == 1
        assert positions[0]['latitude'] is None and positions[0]['x'] == 5
        # On peut ensuite géoréférencer ce même BSSID sans perdre le passé.
        assert client.post('/access-points', json={
            'bssid': 'AA:BB:CC:DD:EE:01', 'ssid':'Ancien AP',
            'latitude':48.847, 'longitude':2.357,
        }).status_code == 201
        assert client.get('/access-points').json()[0]['latitude'] == 48.847
        assert client.get('/trackers/ancien-pc/positions').json()[0]['latitude'] is None
