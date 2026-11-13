# ingenuity_data.py
# ─────────────────────────────────────────────────────────────────────────────
# All 72 Ingenuity flights
# Sources: NASA JPL press releases, Mars Exploration Program,
#          https://mars.nasa.gov/technology/helicopter/
# NOTE: per-flight values are an illustrative dataset, not the official
#       JPL flight log. See README.md before citing any number.
# ─────────────────────────────────────────────────────────────────────────────

import os

import numpy as np
import pandas as pd

# Columns: flight, sol, earth_date, duration_s, max_alt_m,
#          distance_m, battery_start_pct, battery_end_pct,
#          images_taken, science_measurements, flight_type, notes
RAW_FLIGHTS = [
    [1,  58,  "2021-04-19", 39.1,  3.0,    0,    93, 88, 0,   0,  "tech_demo",  "First powered flight on another planet"],
    [2,  61,  "2021-04-22", 51.9,  5.0,    0,    91, 85, 0,   0,  "tech_demo",  "First color image from hover"],
    [3,  64,  "2021-04-25", 80.3,  5.0,   50,    92, 84, 10,  0,  "tech_demo",  "First downrange flight"],
    [4,  69,  "2021-04-30", 117.0, 5.0,  133,    90, 81, 60,  0,  "tech_demo",  "Farthest/fastest flight to date"],
    [5,  76,  "2021-05-07", 108.0, 5.0,  129,    91, 82, 10,  0,  "tech_demo",  "Round trip to new waypoint"],
    [6,  91,  "2021-05-22", 140.0, 10.0, 215,    90, 79, 20,  2,  "ops",        "First operational flight, new airfield"],
    [7,  97,  "2021-05-29", 62.8,  10.0,  106,   89, 82, 15,  2,  "ops",        "Scout for Perseverance"],
    [8,  102, "2021-06-05", 77.4,  10.0,  160,   91, 83, 18,  2,  "scout",      "Scouting Séítah region"],
    [9,  107, "2021-06-12", 166.4, 10.0,  625,   90, 77, 35,  3,  "scout",      "Longest flight to date"],
    [10, 113, "2021-06-19", 165.4, 12.0,  215,   92, 79, 28,  3,  "scout",      "Ingenuity's shadow visible on surface"],
    [11, 117, "2021-06-23", 130.7, 12.0,  360,   90, 80, 22,  3,  "scout",      "South Séítah scout"],
    [12, 121, "2021-06-29", 169.5, 10.0,  450,   91, 78, 30,  4,  "scout",      "Southernmost point so far"],
    [13, 126, "2021-07-04", 160.5, 8.0,   222,   89, 80, 26,  4,  "scout",      "July 4th flight"],
    [14, 130, "2021-07-11", 101.9, 5.0,   393,   90, 82, 16,  3,  "scout",      "Return to Wright Brothers Field area"],
    [15, 135, "2021-07-19", 176.3, 10.0,  689,   91, 77, 40,  4,  "scout",      "New distance record: 689m"],
    [16, 138, "2021-07-22", 109.0, 10.0,  588,   90, 80, 25,  4,  "scout",      "Delta region approach"],
    [17, 142, "2021-07-29", 114.9, 10.0,  142,   89, 81, 20,  3,  "ops",        "Surveying ancient river delta"],
    [18, 146, "2021-08-04", 61.7,  10.0,   34,   91, 85, 10,  2,  "ops",        "Repositioning flight"],
    [19, 152, "2021-08-10", 129.4, 10.0,  188,   90, 80, 22,  3,  "scout",      "Searching for Perseverance landing hardware"],
    [20, 164, "2021-08-23", 130.3, 10.0,  392,   89, 79, 28,  4,  "scout",      "First flight since software update"],
    [21, 172, "2021-09-03", 121.5, 10.0,  370,   90, 80, 24,  4,  "scout",      "Artuby ridge survey"],
    [22, 177, "2021-09-09", 129.5, 10.0,  382,   91, 80, 26,  4,  "scout",      "Crater rim scouting"],
    [23, 181, "2021-09-14", 130.9, 10.0,  458,   90, 79, 28,  4,  "scout",      "Approaching Raised Ridges"],
    [24, 185, "2021-09-18", 169.5, 10.0,  616,   89, 77, 38,  5,  "scout",      "Scouting Raised Ridges"],
    [25, 196, "2021-09-30", 129.0, 10.0,  704,   91, 79, 32,  5,  "scout",      "Longest distance yet: 704m"],
    [26, 200, "2021-10-08", 125.0, 10.0,  574,   90, 80, 30,  5,  "scout",      "Escaping Séítah"],
    [27, 204, "2021-10-24", 65.0,  10.0,  122,   91, 84, 14,  2,  "ops",        "Short repositioning"],
    [28, 211, "2021-11-02", 117.8, 10.0,  160,   89, 81, 20,  3,  "ops",        "South Séítah departure"],
    [29, 218, "2021-11-11", 126.0, 10.0,  372,   90, 80, 26,  4,  "scout",      "Transition toward delta"],
    [30, 228, "2021-11-21", 54.3,  10.0,   94,   91, 85, 12,  2,  "ops",        "Short repositioning hop"],
    [31, 237, "2021-12-02", 88.4,  10.0,  202,   90, 82, 18,  3,  "scout",      "Approaching delta front"],
    [32, 245, "2021-12-12", 109.1, 10.0,  348,   89, 80, 24,  4,  "scout",      "Delta fan front survey"],
    [33, 249, "2021-12-18", 56.4,  10.0,  35,    91, 85, 10,  2,  "ops",        "Minor repositioning"],
    [34, 257, "2021-12-29", 117.0, 10.0,  141,   90, 81, 20,  3,  "ops",        "Year-end survey flight"],
    [35, 263, "2022-01-06", 109.6, 10.0,  310,   89, 81, 22,  4,  "scout",      "New year scouting"],
    [36, 267, "2022-01-10", 167.7, 10.0,  528,   90, 77, 36,  5,  "scout",      "Approaching Kodiak butte"],
    [37, 277, "2022-01-22", 160.0, 12.0,  482,   91, 78, 34,  5,  "scout",      "Kodiak butte approach"],
    [38, 285, "2022-02-01", 155.5, 12.0,  389,   90, 78, 32,  5,  "scout",      "Surveying Kodiak"],
    [39, 290, "2022-02-09", 117.0, 10.0,  319,   89, 80, 24,  4,  "scout",      "Post-Kodiak repositioning"],
    [40, 295, "2022-02-16", 157.4, 12.0,  428,   91, 78, 30,  5,  "scout",      "Hawksbill Gap approach"],
    [41, 302, "2022-02-26", 136.9, 10.0,  342,   90, 79, 26,  4,  "scout",      "Entering Hawksbill Gap"],
    [42, 308, "2022-03-08", 97.5,  10.0,  246,   89, 82, 20,  3,  "scout",      "Through the gap"],
    [43, 316, "2022-03-16", 161.3, 12.0,  478,   90, 77, 32,  5,  "scout",      "Upper delta approach"],
    [44, 323, "2022-03-24", 128.6, 12.0,  340,   91, 79, 26,  5,  "science",    "Delta stratigraphy imaging"],
    [45, 330, "2022-04-01", 123.8, 10.0,  296,   90, 80, 24,  6,  "science",    "First dedicated science flight"],
    [46, 335, "2022-04-08", 186.0, 12.0,  565,   89, 76, 42,  6,  "science",    "Detailed delta layer imaging"],
    [47, 350, "2022-04-24", 124.0, 12.0,  297,   91, 80, 26,  6,  "science",    "Castaic Lake area survey"],
    [48, 357, "2022-05-03", 174.9, 12.0,  466,   90, 77, 36,  7,  "science",    "Extended science run"],
    [49, 362, "2022-05-09", 106.0, 12.0,  268,   89, 81, 22,  5,  "scout",      "Repositioning toward Belva"],
    [50, 371, "2022-05-20", 146.7, 10.0,  346,   90, 79, 28,  5,  "scout",      "Flight 50 milestone"],
    [51, 382, "2022-06-02", 136.0, 10.0,  280,   91, 80, 24,  5,  "scout",      "Escaping Belva crater approach"],
    [52, 389, "2022-06-11", 162.4, 12.0,  404,   89, 77, 32,  6,  "science",    "Belva crater rim imaging"],
    [53, 399, "2022-06-24", 174.0, 14.0,  469,   90, 76, 38,  6,  "science",    "First 14m altitude flight"],
    [54, 409, "2022-07-09", 148.7, 14.0,  360,   91, 78, 30,  6,  "science",    "Northern delta scouting"],
    [55, 426, "2022-07-29", 142.0, 14.0,  311,   90, 79, 28,  5,  "scout",      "Reconnecting with Perseverance"],
    [56, 435, "2022-08-09", 147.0, 12.0,  359,   89, 79, 30,  5,  "scout",      "Upper fan survey"],
    [57, 451, "2022-08-31", 157.0, 12.0,  411,   90, 78, 32,  6,  "science",    "Berry hollow imaging"],
    [58, 460, "2022-09-12", 162.0, 14.0,  438,   91, 77, 34,  6,  "science",    "Detailed stratigraphy"],
    [59, 474, "2022-10-01", 142.0, 12.0,  304,   90, 79, 28,  5,  "scout",      "Reconnect with rover"],
    [60, 480, "2022-10-08", 148.5, 14.0,  332,   89, 78, 30,  6,  "science",    "Mt. Julian approach"],
    [61, 490, "2022-10-19", 110.0, 14.0,  284,   91, 81, 20,  4,  "ops",        "Unscheduled early landing — nav anomaly"],
    [62, 497, "2022-10-27", 160.0, 12.0,  202,   90, 79, 26,  5,  "ops",        "Resuming after anomaly investigation"],
    [63, 508, "2022-11-09", 126.9, 12.0,  279,   89, 80, 24,  5,  "scout",      "Mt. Julian survey"],
    [64, 522, "2022-11-28", 169.0, 14.0,  467,   90, 77, 36,  7,  "science",    "New altitude tied at 14m"],
    [65, 535, "2022-12-15", 128.7, 14.0,  302,   91, 79, 26,  6,  "science",    "Year-end science flight"],
    [66, 551, "2023-01-06", 110.0, 12.0,  212,   90, 81, 20,  4,  "ops",        "New Year repositioning"],
    [67, 569, "2023-01-29", 113.7, 14.0,  235,   89, 80, 22,  5,  "scout",      "Airspeed survey flight"],
    [68, 584, "2023-02-18", 148.0, 14.0,  349,   90, 78, 30,  6,  "science",    "Upper Jezero rim approach"],
    [69, 598, "2023-03-09", 136.0, 14.0,  312,   91, 79, 26,  6,  "science",    "Spring science run"],
    [70, 614, "2023-03-27", 100.0, 17.0,  179,   90, 82, 18,  4,  "ops",        "NEW altitude record: 17m"],
    [71, 643, "2023-04-27", 108.0, 17.0,  192,   89, 81, 20,  4,  "scout",      "Final scout before winter"],
    [72, 772, "2024-01-18", 130.3, 24.0,  0,     91, 83, 10,  2,  "ops",        "FINAL FLIGHT — rotor damaged on landing"],
]

COLUMNS = [
    "flight_num", "sol", "earth_date", "duration_s", "max_alt_m",
    "distance_m", "battery_start_pct", "battery_end_pct",
    "images_taken", "science_measurements", "flight_type", "notes",
]

PHASES = ["Tech Demo", "Early Ops", "Séítah", "Delta Approach", "Delta Science"]


def build_dataframe():
    df = pd.DataFrame(RAW_FLIGHTS, columns=COLUMNS)

    df["earth_date"] = pd.to_datetime(df["earth_date"])
    df["battery_used"] = df["battery_start_pct"] - df["battery_end_pct"]
    df["speed_ms"] = (df["distance_m"] / df["duration_s"]).round(2)
    df["speed_ms"] = df["speed_ms"].replace([np.inf, -np.inf], np.nan).fillna(0)
    df["days_since_f1"] = (df["earth_date"] - df["earth_date"].min()).dt.days
    # Plain strings (not Categorical) so lookups and CSV round-trips stay simple
    df["mission_phase"] = pd.cut(
        df["flight_num"], bins=[0, 5, 14, 35, 57, 72], labels=PHASES
    ).astype(str)
    df["age_bucket"] = pd.cut(
        df["flight_num"], bins=[0, 24, 48, 72],
        labels=["Early (1-24)", "Middle (25-48)", "Late (49-72)"],
    ).astype(str)
    df["anomaly_flag"] = df["flight_num"].isin([61, 72])
    df["record_flag"] = df["flight_num"].isin([4, 9, 15, 25, 53, 70, 72])

    # Cumulative stats
    df["cumulative_distance_m"] = df["distance_m"].cumsum()
    df["cumulative_duration_s"] = df["duration_s"].cumsum()
    df["cumulative_images"] = df["images_taken"].cumsum()
    df["cumulative_science"] = df["science_measurements"].cumsum()
    df["cumulative_battery_used"] = df["battery_used"].cumsum()

    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = build_dataframe()
    df.to_csv("data/ingenuity_flights.csv", index=False)

    top_alt = df.loc[df.max_alt_m.idxmax()]
    print(f"✅ {len(df)} flights exported → data/ingenuity_flights.csv")
    print(f"   Total flight time:  {df.duration_s.sum()/60:.1f} minutes")
    print(f"   Total distance:     {df.distance_m.sum()/1000:.2f} km")
    print(f"   Max altitude:       {top_alt.max_alt_m}m (Flight {top_alt.flight_num})")
    print(f"   Longest flight:     {df.duration_s.max()}s (Flight {df.loc[df.duration_s.idxmax(), 'flight_num']})")
    print(f"   Farthest flight:    {df.distance_m.max()}m (Flight {df.loc[df.distance_m.idxmax(), 'flight_num']})")
    print(f"   Total images:       {df.images_taken.sum():,}")
    print(f"   Science runs:       {df.science_measurements.sum():,}")
