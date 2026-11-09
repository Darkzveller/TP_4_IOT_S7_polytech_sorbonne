"""Démo sans ESP32 ni carte Wi-Fi, à exécuter après le démarrage du serveur."""
import json
import math
from urllib.request import Request, urlopen

SERVER = "http://127.0.0.1:8000"
APS = [
    {"bssid": "02:00:00:00:00:01", "ssid": "TP-AP-1", "x": 0, "y": 0},
    {"bssid": "02:00:00:00:00:02", "ssid": "TP-AP-2", "x": 30, "y": 0},
    {"bssid": "02:00:00:00:00:03", "ssid": "TP-AP-3", "x": 0, "y": 30},
    {"bssid": "02:00:00:00:00:04", "ssid": "TP-AP-4", "x": 30, "y": 30},
]
ROUTE = [(3, 4), (8, 5), (13, 8), (19, 11), (25, 16), (28, 22), (26, 28)]


def post(path, data):
    request = Request(
        SERVER + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


if __name__ == "__main__":
    for ap in APS:
        post("/access-points", ap)
    print(f"{len(APS)} points d'accès fictifs ajoutés.")
    for x, y in ROUTE:
        readings = []
        for ap in APS:
            distance = max(1, math.hypot(x - ap["x"], y - ap["y"]))
            rssi = max(-100, round(-45 - 30 * math.log10(distance)))
            readings.append({"bssid": ap["bssid"], "ssid": ap["ssid"], "rssi": rssi})
        result = post("/scans", {"tracker_id": "demo", "readings": readings})
        print(f"scan #{result['scan_id']}: position estimée = {result['position']}")
    print("Ouvrir : http://127.0.0.1:8000/map")
