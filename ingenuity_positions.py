# ingenuity_positions.py
# ─────────────────────────────────────────────────────────────────────────────
# Real flight paths and airfields from NASA's Mars 2020 map layers, converted
# from areocentric lat/lon to local ENU meters.
#
# Origin = Wright Brothers Field (where Ingenuity was deployed, "Flight 0" in
# the waypoint file). East = +X, North = +Y.
# ─────────────────────────────────────────────────────────────────────────────

import json
import os

import numpy as np
import pandas as pd

from ingenuity_data import FLIGHT_PATH_FILE, load_waypoint_features

MARS_RADIUS_M = 3_396_190      # IAU equatorial radius used by the NASA map
SIMPLIFY_TOLERANCE_M = 0.5     # path simplification; well below plot resolution

_wp = load_waypoint_features()
LANDING_LAT = float(_wp[0]["Lat"])
LANDING_LON = float(_wp[0]["Lon"])


def latlon_to_enu(lat, lon):
    """Mars lat/lon (degrees) → local ENU meters from Wright Brothers Field."""
    north_m = np.radians(np.asarray(lat) - LANDING_LAT) * MARS_RADIUS_M
    east_m = (np.radians(np.asarray(lon) - LANDING_LON) * MARS_RADIUS_M
              * np.cos(np.radians(LANDING_LAT)))
    return east_m, north_m


def enu_to_latlon(east_m, north_m):
    d_lat = np.degrees(np.asarray(north_m) / MARS_RADIUS_M)
    d_lon = np.degrees(np.asarray(east_m) / (MARS_RADIUS_M * np.cos(np.radians(LANDING_LAT))))
    return LANDING_LAT + d_lat, LANDING_LON + d_lon


def _simplify(points, tolerance):
    """Ramer–Douglas–Peucker (iterative). points: (n, 2) array."""
    n = len(points)
    if n < 3:
        return points
    keep = np.zeros(n, dtype=bool)
    keep[[0, n - 1]] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        seg = points[b] - points[a]
        rel = points[a + 1:b] - points[a]
        seg_len = np.hypot(*seg)
        if seg_len == 0:
            dist = np.hypot(rel[:, 0], rel[:, 1])
        else:
            dist = np.abs(seg[0] * rel[:, 1] - seg[1] * rel[:, 0]) / seg_len
        i = int(dist.argmax())
        if dist[i] > tolerance:
            mid = a + 1 + i
            keep[mid] = True
            stack += [(a, mid), (mid, b)]
    return points[keep]


def _load_flight_paths():
    with open(FLIGHT_PATH_FILE) as f:
        feats = json.load(f)["features"]
    paths = {}
    for ft in sorted(feats, key=lambda x: x["properties"]["Flight"]):
        coords = np.asarray(ft["geometry"]["coordinates"], dtype=float)
        east, north = latlon_to_enu(coords[:, 1], coords[:, 0])
        pts = _simplify(np.column_stack([east, north]), SIMPLIFY_TOLERANCE_M)
        paths[int(ft["properties"]["Flight"])] = [
            (round(float(x), 1), round(float(y), 1)) for x, y in pts]
    return paths


# flight number → [(east_m, north_m), ...]; first = takeoff, last = landing
FLIGHT_PATHS = _load_flight_paths()


def _airfields():
    """Airfield name → (east_m, north_m) of the first landing there."""
    out = {}
    for p in _wp:
        name = p["ToAirfld"]
        if name not in out:
            e, n = latlon_to_enu(p["Lat"], p["Lon"])
            out[name] = (round(float(e), 1), round(float(n), 1), int(p["Flight"]))
    return out


AIRFIELDS = _airfields()

_all = np.array([pt for pts in FLIGHT_PATHS.values() for pt in pts])
PAD_M = 250
# Map window (ENU meters), rounded outward to the nearest 100 m
X_MIN = int(np.floor((_all[:, 0].min() - PAD_M) / 100) * 100)
X_MAX = int(np.ceil((_all[:, 0].max() + PAD_M) / 100) * 100)
Y_MIN = int(np.floor((_all[:, 1].min() - PAD_M) / 100) * 100)
Y_MAX = int(np.ceil((_all[:, 1].max() + PAD_M) / 100) * 100)


# ─────────────────────────────────────────────────────────────────────────────
# TIDY DATAFRAMES
# ─────────────────────────────────────────────────────────────────────────────
def build_path_dataframe():
    """One row per path vertex."""
    rows = []
    for flight_num, waypoints in FLIGHT_PATHS.items():
        for step, (east_m, north_m) in enumerate(waypoints):
            lat, lon = enu_to_latlon(east_m, north_m)
            rows.append({
                "flight_num":  flight_num,
                "step":        step,
                "is_takeoff":  step == 0,
                "is_landing":  step == len(waypoints) - 1,
                "east_m":      east_m,
                "north_m":     north_m,
                "lat":         round(float(lat), 7),
                "lon":         round(float(lon), 7),
            })
    return pd.DataFrame(rows)


def build_endpoint_dataframe(flight_df):
    """Takeoff/landing positions merged onto flight metrics: one row per flight."""
    ends = pd.DataFrame([
        {"flight_num": fn,
         "takeoff_east": pts[0][0], "takeoff_north": pts[0][1],
         "landing_east": pts[-1][0], "landing_north": pts[-1][1]}
        for fn, pts in FLIGHT_PATHS.items()
    ])
    return flight_df.merge(ends, on="flight_num", how="left")


def build_location_dataframe():
    """Named airfields, in the order Ingenuity first reached them."""
    rows = []
    for name, (east_m, north_m, first_flight) in AIRFIELDS.items():
        lat, lon = enu_to_latlon(east_m, north_m)
        rows.append({
            "location":     name,
            "short_name":   "WBF" if name == "Wright Brothers Field"
                            else name.replace("Airfield ", ""),
            "east_m":       east_m,
            "north_m":      north_m,
            "lat":          round(float(lat), 7),
            "lon":          round(float(lon), 7),
            "first_flight": first_flight,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    path_df = build_path_dataframe()
    loc_df = build_location_dataframe()
    path_df.to_csv("data/ingenuity_paths.csv", index=False)
    loc_df.to_csv("data/ingenuity_locations.csv", index=False)

    print(f"✅ Paths: {len(path_df):,} vertices across {path_df.flight_num.nunique()} flights "
          f"(simplified to {SIMPLIFY_TOLERANCE_M} m)")
    print(f"✅ Airfields: {len(loc_df)}")
    print(f"   Origin: {LANDING_LAT:.5f}°N {LANDING_LON:.5f}°E")
    print(f"   Map window: East {X_MIN} → {X_MAX} m, North {Y_MIN} → {Y_MAX} m")
