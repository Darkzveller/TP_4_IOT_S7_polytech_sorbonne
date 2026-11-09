"""Démo sans ESP32 ni carte Wi-Fi, à exécuter après le démarrage du serveur."""
import json
import math
from urllib.request import Request, urlopen

SERVER = "http://127.0.0.1:8000"
# Emplacements fictifs autour de Jussieu pour visualiser la démo sur la carte.
ORIGIN_LAT, ORIGIN_LON = 48.8470, 2.3571
EARTH_RADIUS = 6_371_000


def gps_from_local(x, y):
    return (
        ORIGIN_LAT + math.degrees(y / EARTH_RADIUS),
        ORIGIN_LON + math.degrees(x / (EARTH_RADIUS * math.cos(math.radians(ORIGIN_LAT)))),
    )


APS = []
for i, (x, y) in enumerate([(0, 0), (30, 0), (0, 30), (30, 30)], start=1):
    lat, lon = gps_from_local(x, y)
    APS.append({
        "bssid": f"02:00:00:00:00:{i:02X}",
        "ssid": f"TP-DEMO-{i}", "latitude": lat, "longitude": lon,
        "x_demo": x, "y_demo": y,
    })
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
        # Le serveur attend des coordonnées géographiques ou X/Y, pas x_demo/y_demo.
        post("/access-points", {k: v for k, v in ap.items() if k not in ("x_demo", "y_demo")})
    print(f"{len(APS)} points d'accès fictifs ajoutés.")
    for x, y in ROUTE:
        readings = []
        for ap in APS:
            distance = max(1, math.hypot(x - ap["x_demo"], y - ap["y_demo"]))
            rssi = max(-100, round(-45 - 30 * math.log10(distance)))
            readings.append({"bssid": ap["bssid"], "ssid": ap["ssid"], "rssi": rssi})
        result = post("/scans", {"tracker_id": "demo", "readings": readings})
        print(f"scan #{result['scan_id']}: position estimée = {result['position']}")
    print("Ouvrir : http://127.0.0.1:8000/map")
