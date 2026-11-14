# ingenuity_data.py
# ─────────────────────────────────────────────────────────────────────────────
# All 72 Ingenuity flights, read from NASA's Mars 2020 map layers:
#   data/raw/m20_heli_waypoints.json    one point per landing, with flight stats
#   data/raw/m20_heli_flight_path.json  the flown path of every flight
# Refresh the raw files with:  python fetch_nasa_data.py
# ─────────────────────────────────────────────────────────────────────────────

import json
import os

import pandas as pd

RAW_DIR = "data/raw"
WAYPOINTS_FILE = f"{RAW_DIR}/m20_heli_waypoints.json"
FLIGHT_PATH_FILE = f"{RAW_DIR}/m20_heli_flight_path.json"

# Flights 1-5 were the technology demonstration and its transition; everything
# after is the operations demonstration, split here by Earth year.
PHASES = ["Tech Demo", "Ops 2021", "Ops 2022", "Ops 2023", "Ops 2024"]
TECH_DEMO_LAST_FLIGHT = 5

RECORD_METRICS = {
    "duration_s":   "duration",
    "max_alt_m":    "altitude",
    "distance_m":   "distance",
    "max_speed_ms": "speed",
}

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _parse_nasa_date(text):
    """'April 4, 2021' / 'Sept. 3, 2021' / 'Jan. 18, 2024' → Timestamp."""
    month, day, year = text.replace(",", "").replace(".", "").split()
    return pd.Timestamp(int(year), _MONTHS[month[:3].lower()], int(day))


def load_waypoint_features():
    if not os.path.exists(WAYPOINTS_FILE):
        raise FileNotFoundError(
            f"{WAYPOINTS_FILE} is missing — run `python fetch_nasa_data.py` first")
    with open(WAYPOINTS_FILE) as f:
        feats = json.load(f)["features"]
    return sorted((ft["properties"] for ft in feats), key=lambda p: p["Flight"])


def build_dataframe():
    """One row per flight (1-72). Flight 0 in the source is the deployment spot."""
    rows = []
    for p in load_waypoint_features():
        if p["Flight"] < 1:
            continue
        rows.append({
            "flight_num":     int(p["Flight"]),
            "sol":            int(p["Sol"]),
            "earth_date":     _parse_nasa_date(p["Earth_Date"]),
            "duration_s":     float(p["Duration_s"]),
            "max_alt_m":      float(p["Max_Alt_m"]),
            "distance_m":     round(float(p["Dist_m"]), 1),
            "max_speed_ms":   float(p["Max_Spd_m"]),
            "from_airfield":  p["FromAirfld"],
            "to_airfield":    p["ToAirfld"],
            "landing_lat":    float(p["Lat"]),
            "landing_lon":    float(p["Lon"]),
            "landing_elev_m": float(p["Elev_Geoid"]),
        })
    df = pd.DataFrame(rows)

    df["avg_speed_ms"] = (df["distance_m"] / df["duration_s"]).round(2)
    df["days_since_f1"] = (df["earth_date"] - df["earth_date"].min()).dt.days
    df["mission_phase"] = [
        "Tech Demo" if fn <= TECH_DEMO_LAST_FLIGHT else f"Ops {d.year}"
        for fn, d in zip(df["flight_num"], df["earth_date"])
    ]
    df["relocated"] = df["from_airfield"] != df["to_airfield"]
    df["route"] = [
        f"{a} → {b}" if a != b else f"Local flight at {a}"
        for a, b in zip(df["from_airfield"], df["to_airfield"])
    ]

    # A flight sets a record when it strictly beats every earlier flight
    record_lists = [[] for _ in range(len(df))]
    for col, label in RECORD_METRICS.items():
        previous_best = df[col].cummax().shift(1)
        for i in df.index[(df[col] > previous_best) & (df["flight_num"] > 1)]:
            record_lists[i].append(label)
    df["records"] = [", ".join(r) for r in record_lists]
    df["record_flag"] = df["records"] != ""
    df["final_flag"] = df["flight_num"] == df["flight_num"].max()
    df["notes"] = [
        route + (f" · new {rec} record" if rec else "") + (" · final flight" if final else "")
        for route, rec, final in zip(df["route"], df["records"], df["final_flag"])
    ]

    df["cumulative_distance_m"] = df["distance_m"].cumsum().round(1)
    df["cumulative_duration_s"] = df["duration_s"].cumsum().round(1)
    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = build_dataframe()
    df.to_csv("data/ingenuity_flights.csv", index=False)

    def best(col):
        r = df.loc[df[col].idxmax()]
        return f"{r[col]:g} (Flight {r.flight_num})"

    print(f"✅ {len(df)} flights exported → data/ingenuity_flights.csv")
    print(f"   Dates:           {df.earth_date.min():%Y-%m-%d} → {df.earth_date.max():%Y-%m-%d}")
    print(f"   Total airtime:   {df.duration_s.sum()/60:.1f} minutes")
    print(f"   Total distance:  {df.distance_m.sum()/1000:.2f} km")
    print(f"   Max altitude:    {best('max_alt_m')} m")
    print(f"   Longest flight:  {best('duration_s')} s")
    print(f"   Farthest flight: {best('distance_m')} m")
    print(f"   Top groundspeed: {best('max_speed_ms')} m/s")
    print(f"   Phases:          {df.mission_phase.value_counts(sort=False).to_dict()}")
