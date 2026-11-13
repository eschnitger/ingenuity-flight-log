# tableau_export.py
# Writes everything Tableau needs into tableau/:
#   tableau_ingenuity_paths.csv      one row per waypoint, flight metrics repeated
#   tableau_ingenuity_endpoints.csv  takeoff/landing rows only (dot layer)
#   tableau_ingenuity_locations.csv  airfields + named features
#   mars_terrain_tableau.png         background image matched to the map window
import os

from PIL import Image

from ingenuity_data import build_dataframe
from ingenuity_map import X_MAX, X_MIN, Y_MAX, Y_MIN, synthetic_terrain
from ingenuity_positions import build_location_dataframe, build_path_dataframe

OUT_DIR = "tableau"


def export_tableau_path_format():
    path_df = build_path_dataframe()
    flight_df = build_dataframe()

    tableau_df = path_df.merge(
        flight_df[[
            "flight_num", "duration_s", "max_alt_m", "distance_m",
            "battery_used", "battery_start_pct", "battery_end_pct",
            "images_taken", "science_measurements",
            "flight_type", "mission_phase", "earth_date", "sol",
            "anomaly_flag", "record_flag", "notes", "speed_ms", "age_bucket",
        ]],
        on="flight_num", how="left",
    ).rename(columns={
        "step":       "path_order",
        "east_m":     "x_meters_east",
        "north_m":    "y_meters_north",
        "is_takeoff": "is_takeoff_point",
        "is_landing": "is_landing_point",
    })

    tableau_df.to_csv(f"{OUT_DIR}/tableau_ingenuity_paths.csv", index=False)
    print(f"✅ Paths: {len(tableau_df):,} rows, {tableau_df.flight_num.nunique()} flights")

    endpoints = tableau_df[tableau_df["is_takeoff_point"] | tableau_df["is_landing_point"]]
    endpoints.to_csv(f"{OUT_DIR}/tableau_ingenuity_endpoints.csv", index=False)
    print(f"✅ Endpoints: {len(endpoints)} rows")

    build_location_dataframe().to_csv(
        f"{OUT_DIR}/tableau_ingenuity_locations.csv", index=False)
    print("✅ Locations exported")


def create_tableau_background(px_per_m=1.0):
    """Terrain image whose edges are exactly the map window, so in Tableau:
    Map → Background Images → Left/Right/Bottom/Top = the numbers printed below."""
    width = int((X_MAX - X_MIN) * px_per_m)
    height = int((Y_MAX - Y_MIN) * px_per_m)
    path = f"{OUT_DIR}/mars_terrain_tableau.png"
    Image.fromarray(synthetic_terrain(width, height, seed=2021)).save(path)
    print(f"✅ Background: {path} ({width}×{height}px)")
    print(f"   X field = x_meters_east   Left={X_MIN}  Right={X_MAX}")
    print(f"   Y field = y_meters_north  Bottom={Y_MIN}  Top={Y_MAX}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    export_tableau_path_format()
    create_tableau_background()
