# tableau_export.py
# Writes everything Tableau needs into tableau/:
#   tableau_ingenuity_paths.csv      one row per path vertex, flight metrics repeated
#   tableau_ingenuity_flights.csv    one row per flight (use for metric sheets)
#   tableau_ingenuity_locations.csv  airfields
#   mars_terrain_tableau.png         decorative background matched to the map window
import os

from PIL import Image

from ingenuity_data import build_dataframe
from ingenuity_map import synthetic_terrain
from ingenuity_positions import (X_MAX, X_MIN, Y_MAX, Y_MIN,
                                 build_location_dataframe, build_path_dataframe)

OUT_DIR = "tableau"

FLIGHT_COLS = [
    "flight_num", "sol", "earth_date", "duration_s", "max_alt_m", "distance_m",
    "max_speed_ms", "avg_speed_ms", "mission_phase", "from_airfield", "to_airfield",
    "route", "records", "record_flag", "final_flag", "landing_elev_m", "notes",
]


def export_tableau_files():
    flight_df = build_dataframe()
    flight_df[FLIGHT_COLS].to_csv(f"{OUT_DIR}/tableau_ingenuity_flights.csv", index=False)
    print(f"✅ Flights: {len(flight_df)} rows")

    paths = build_path_dataframe().merge(flight_df[FLIGHT_COLS], on="flight_num") \
        .rename(columns={"step": "path_order", "east_m": "x_meters_east",
                         "north_m": "y_meters_north", "is_takeoff": "is_takeoff_point",
                         "is_landing": "is_landing_point"})
    paths.to_csv(f"{OUT_DIR}/tableau_ingenuity_paths.csv", index=False)
    print(f"✅ Paths: {len(paths):,} rows")

    build_location_dataframe().to_csv(f"{OUT_DIR}/tableau_ingenuity_locations.csv",
                                      index=False)
    print("✅ Locations exported")

    # Remove the old endpoints file if it is still around from an earlier version
    old = f"{OUT_DIR}/tableau_ingenuity_endpoints.csv"
    if os.path.exists(old):
        os.remove(old)


def create_tableau_background(px_per_m=0.5):
    width = int((X_MAX - X_MIN) * px_per_m)
    height = int((Y_MAX - Y_MIN) * px_per_m)
    path = f"{OUT_DIR}/mars_terrain_tableau.png"
    Image.fromarray(synthetic_terrain(width, height, seed=2021)).save(path)
    print(f"✅ Background: {path} ({width}×{height}px, decorative)")
    print(f"   X field = x_meters_east   Left={X_MIN}  Right={X_MAX}")
    print(f"   Y field = y_meters_north  Bottom={Y_MIN}  Top={Y_MAX}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    export_tableau_files()
    create_tableau_background()
