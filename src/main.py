"""TP4 IoT : serveur local de localisation Wi-Fi (FastAPI + SQLite).

Les coordonnées x/y sont des mètres dans un repère local choisi par l'équipe.
La localisation est une estimation pédagogique basée sur les RSSI, pas du GPS.
"""

from __future__ import annotations

import re
import math
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "tracker.sqlite3"
BSSID_RE = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")
# Repère métrique pédagogique commun à toute la France métropolitaine.
# Les distances géographiques réelles ne sont pas déduites de ce repère :
# il sert seulement à conserver la compatibilité avec les anciennes colonnes x/y.
FRANCE_ORIGIN_LAT = 46.603354
FRANCE_ORIGIN_LON = 1.888334
EARTH_RADIUS_M = 6_371_000.0


def gps_to_xy(latitude: float, longitude: float) -> tuple[float, float]:
    x = EARTH_RADIUS_M * math.radians(longitude - FRANCE_ORIGIN_LON) * math.cos(math.radians(FRANCE_ORIGIN_LAT))
    y = EARTH_RADIUS_M * math.radians(latitude - FRANCE_ORIGIN_LAT)
    return x, y


def xy_to_gps(x: float, y: float) -> tuple[float, float]:
    latitude = FRANCE_ORIGIN_LAT + math.degrees(y / EARTH_RADIUS_M)
    longitude = FRANCE_ORIGIN_LON + math.degrees(x / (EARTH_RADIUS_M * math.cos(math.radians(FRANCE_ORIGIN_LAT))))
    return latitude, longitude


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@contextmanager
def database():
    db = sqlite3.connect(DB_FILE, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def init_database() -> None:
    with database() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS access_points (
                bssid TEXT PRIMARY KEY,
                ssid TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracker_id TEXT NOT NULL,
                scanned_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
                bssid TEXT NOT NULL,
                ssid TEXT NOT NULL,
                rssi INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
                tracker_id TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                ap_count INTEGER NOT NULL,
                method TEXT NOT NULL,
                estimated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_scans_tracker ON scans(tracker_id, scanned_at);
            CREATE INDEX IF NOT EXISTS idx_positions_tracker ON positions(tracker_id, estimated_at);
            """
        )
        # Migration non destructive d'une ancienne base (x/y uniquement).
        for table in ("access_points", "positions"):
            columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
            for column in ("latitude", "longitude"):
                if column not in columns:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} REAL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="TP4 IoT — Tracker Wi-Fi",
    description="Serveur local REST : points d'accès, scans RSSI, positions, trajets.",
    version="1.0.0",
    lifespan=lifespan,
)


def normalize_bssid(value: str) -> str:
    bssid = value.strip().replace("-", ":").upper()
    if not BSSID_RE.fullmatch(bssid):
        raise ValueError("BSSID attendu au format AA:BB:CC:DD:EE:FF")
    return bssid


class AccessPoint(BaseModel):
    bssid: str
    ssid: str = Field(default="", max_length=128)
    # Ancien format : coordonnées X/Y locales en mètres.
    x: float | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    y: float | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    # Nouveau format : point choisi sur la carte OpenStreetMap.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def valid_coordinates(self):
        if (self.x is None) != (self.y is None):
            raise ValueError("x et y doivent être fournis ensemble")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude et longitude doivent être fournies ensemble")
        if self.latitude is None and self.x is None:
            raise ValueError("Fournir latitude/longitude ou x/y")
        if self.latitude is not None:
            # Priorité au GPS : x/y dérivés pour la compatibilité SQL existante.
            self.x, self.y = gps_to_xy(self.latitude, self.longitude)
        return self

    @field_validator("bssid")
    @classmethod
    def valid_bssid(cls, value: str) -> str:
        return normalize_bssid(value)


class Observation(BaseModel):
    bssid: str
    ssid: str = Field(default="", max_length=128)
    rssi: int = Field(ge=-100, le=0)

    @field_validator("bssid")
    @classmethod
    def valid_bssid(cls, value: str) -> str:
        return normalize_bssid(value)


class Scan(BaseModel):
    tracker_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    readings: list[Observation] = Field(min_length=1, max_length=200)


def estimate_position(readings: list[Observation], known: dict) -> dict | None:
    """Estimation RSSI pédagogique, pas une triangulation ni une position GPS mesurée.

    Ne mélange pas les vieux AP en x/y local avec ceux placés sur une carte GPS.
    Si au moins un AP géoréférencé est détecté, on calcule dans leur seul repère.
    """
    strongest = {}
    for r in readings:
        if r.bssid in known and (
            r.bssid not in strongest or r.rssi > strongest[r.bssid].rssi
        ):
            strongest[r.bssid] = r
    if not strongest:
        return None

    geocoded = {
        bssid: reading for bssid, reading in strongest.items()
        if known[bssid]["latitude"] is not None and known[bssid]["longitude"] is not None
    }
    selected = geocoded if geocoded else strongest
    xw = yw = total = 0.0
    for bssid, reading in selected.items():
        ap = known[bssid]
        distance_m = min(60.0, max(1.0, 10 ** ((-45 - reading.rssi) / 30.0)))
        weight = 1.0 / (distance_m * distance_m)
        xw += ap["x"] * weight
        yw += ap["y"] * weight
        total += weight
    x, y = xw / total, yw / total
    latitude = longitude = None
    if geocoded:
        latitude, longitude = xy_to_gps(x, y)
    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "latitude": round(latitude, 7) if latitude is not None else None,
        "longitude": round(longitude, 7) if longitude is not None else None,
        "ap_count": len(selected),
        "method": "weighted_centroid_rssi_geo" if geocoded else "weighted_centroid_rssi",
    }


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/map", include_in_schema=False)
def map_page():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "database": str(DB_FILE.name)}


@app.get("/access-points")
def list_access_points():
    with database() as db:
        rows = db.execute("SELECT * FROM access_points ORDER BY bssid").fetchall()
    return [dict(row) for row in rows]


@app.post("/access-points", status_code=201)
def save_access_point(ap: AccessPoint):
    with database() as db:
        db.execute(
            """INSERT INTO access_points(bssid, ssid, x, y, latitude, longitude, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(bssid) DO UPDATE SET
               ssid=excluded.ssid, x=excluded.x, y=excluded.y,
               latitude=excluded.latitude, longitude=excluded.longitude,
               updated_at=excluded.updated_at""",
            (ap.bssid, ap.ssid, ap.x, ap.y, ap.latitude, ap.longitude, now_utc()),
        )
    return {"saved": True, **ap.model_dump()}


@app.delete("/access-points/{bssid}", status_code=204)
def delete_access_point(bssid: str):
    try:
        bssid = normalize_bssid(bssid)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    with database() as db:
        result = db.execute("DELETE FROM access_points WHERE bssid=?", (bssid,))
        if result.rowcount == 0:
            raise HTTPException(404, "Point d'accès inconnu")
    return Response(status_code=204)


@app.post("/scans", status_code=201)
def receive_scan(scan: Scan):
    scanned_at = now_utc()  # timestamp serveur, pas d'horloge du tracker à synchroniser
    with database() as db:
        cursor = db.execute(
            "INSERT INTO scans(tracker_id, scanned_at) VALUES (?, ?)",
            (scan.tracker_id, scanned_at),
        )
        scan_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO observations(scan_id, bssid, ssid, rssi) VALUES (?, ?, ?, ?)",
            [(scan_id, r.bssid, r.ssid, r.rssi) for r in scan.readings],
        )
        bssids = tuple({r.bssid for r in scan.readings})
        placeholders = ",".join("?" for _ in bssids)
        aps = db.execute(
            f"SELECT bssid, x, y, latitude, longitude FROM access_points WHERE bssid IN ({placeholders})",
            bssids,
        ).fetchall()
        known = {r["bssid"]: dict(r) for r in aps}
        position = estimate_position(scan.readings, known)
        if position is not None:
            db.execute(
                """INSERT INTO positions(
                       scan_id, tracker_id, x, y, latitude, longitude,
                       ap_count, method, estimated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scan_id, scan.tracker_id, position["x"], position["y"],
                    position["latitude"], position["longitude"],
                    position["ap_count"], position["method"], scanned_at,
                ),
            )
    return {
        "scan_id": scan_id,
        "tracker_id": scan.tracker_id,
        "scanned_at": scanned_at,
        "readings_saved": len(scan.readings),
        "known_ap_count": len(known),
        "position": position,
        "notice": None if position else "Scan enregistré, mais aucun BSSID n'est référencé avec des coordonnées.",
    }


@app.get("/scans")
def list_scans(limit: Annotated[int, Query(ge=1, le=500)] = 100):
    with database() as db:
        rows = db.execute(
            """SELECT s.id, s.tracker_id, s.scanned_at,
                      COUNT(o.id) AS reading_count
               FROM scans s LEFT JOIN observations o ON o.scan_id=s.id
               GROUP BY s.id ORDER BY s.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/scans/{scan_id}")
def scan_details(scan_id: int):
    with database() as db:
        scan = db.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
        if not scan:
            raise HTTPException(404, "Scan introuvable")
        readings = db.execute(
            "SELECT bssid, ssid, rssi FROM observations WHERE scan_id=? ORDER BY rssi DESC",
            (scan_id,),
        ).fetchall()
        pos = db.execute("SELECT * FROM positions WHERE scan_id=?", (scan_id,)).fetchone()
    return {
        **dict(scan),
        "readings": [dict(r) for r in readings],
        "position": dict(pos) if pos else None,
    }


@app.get("/trackers")
def list_trackers():
    with database() as db:
        rows = db.execute(
            """SELECT tracker_id, COUNT(*) AS scan_count, MAX(scanned_at) AS last_scan
               FROM scans GROUP BY tracker_id ORDER BY last_scan DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(422, "Les dates doivent comporter un fuseau horaire (ex. Z).")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


@app.get("/trackers/{tracker_id}/positions")
def get_positions(
    tracker_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 1000,
):
    start_iso, end_iso = to_utc_iso(start), to_utc_iso(end)
    if start_iso and end_iso and start_iso > end_iso:
        raise HTTPException(422, "La date de début doit précéder la date de fin")
    sql = """SELECT id, scan_id, tracker_id, x, y, latitude, longitude,
                    ap_count, method, estimated_at
             FROM positions WHERE tracker_id=?"""
    args = [tracker_id]
    if start_iso:
        sql += " AND estimated_at >= ?"
        args.append(start_iso)
    if end_iso:
        sql += " AND estimated_at <= ?"
        args.append(end_iso)
    sql += " ORDER BY id ASC LIMIT ?"
    args.append(limit)
    with database() as db:
        rows = db.execute(sql, args).fetchall()
    return [dict(row) for row in rows]
