"""Tracker Wi-Fi Windows facultatif : scans locaux via netsh, envoyés à FastAPI.

Fonctionne sans ESP32. Les scans ne deviennent des positions qu'après
référencement des BSSID et de leurs coordonnées sur le serveur.
"""
import argparse
import json
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SSID_RE = re.compile(r"^\s*SSID\s+\d+\s*:\s*(.*)$", re.IGNORECASE)
BSSID_RE = re.compile(r"^\s*BSSID\s+\d+\s*:\s*([\da-fA-F:]{17})", re.IGNORECASE)
SIGNAL_RE = re.compile(r"^\s*Signal\s*:\s*(\d+)\s*%", re.IGNORECASE)


def windows_scan():
    completed = subprocess.run(
        ["netsh", "wlan", "show", "networks", "mode=bssid"],
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    )
    current_ssid = ""
    current_bssid = None
    readings = {}
    for line in completed.stdout.splitlines():
        match_ssid = SSID_RE.match(line)
        if match_ssid:
            current_ssid = match_ssid.group(1).strip()
            current_bssid = None
            continue
        match_bssid = BSSID_RE.match(line)
        if match_bssid:
            current_bssid = match_bssid.group(1).upper()
            continue
        match_signal = SIGNAL_RE.match(line)
        if match_signal and current_bssid:
            signal_percent = max(0, min(100, int(match_signal.group(1))))
            # Conversion approximative en dBm, pas une mesure RSSI native.
            rssi_estimated = round(-100 + signal_percent / 2)
            readings[current_bssid] = {
                "bssid": current_bssid,
                "ssid": current_ssid,
                "rssi": rssi_estimated,
            }
    return list(readings.values())


def send(server, tracker_id, readings):
    payload = json.dumps({"tracker_id": tracker_id, "readings": readings}).encode("utf-8")
    req = Request(
        server.rstrip("/") + "/scans", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(req, timeout=15) as response:
        return json.load(response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scanner les réseaux Wi-Fi visibles depuis un PC Windows")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--tracker-id", default="pc-windows")
    parser.add_argument("--interval", type=float, default=60.0, help="Intervalle entre les scans (secondes)")
    parser.add_argument("--once", action="store_true", help="Effectuer un seul relevé")
    args = parser.parse_args()
    if args.interval < 1:
        parser.error("L'intervalle doit être d'au moins une seconde")
    try:
        while True:
            readings = windows_scan()
            if not readings:
                print("Aucun BSSID trouvé. Vérifiez le Wi-Fi et les autorisations de localisation Windows.")
            else:
                result = send(args.server, args.tracker_id, readings)
                print(f"{len(readings)} BSSID envoyés ; scan #{result['scan_id']}; position = {result['position']}")
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nArrêt du tracker.")
    except (OSError, subprocess.CalledProcessError, HTTPError, URLError) as exc:
        print(f"Erreur : {exc}")
        raise SystemExit(1) from exc
