# ingenuity_positions.py
# ─────────────────────────────────────────────────────────────────────────────
# Ingenuity flight waypoint data
# Coordinates: Areocentric lat/lon + local ENU meters from landing site
#
# Landing site: 18.4447°N, 77.4508°E  (Perseverance / Wright Brothers Field)
# Local ENU: East = +X, North = +Y, origin = Wright Brothers Field
#
# NOTE: waypoints are schematic (hand-placed path nodes), not JPL telemetry.
# ─────────────────────────────────────────────────────────────────────────────

import os

import numpy as np
import pandas as pd

# ── Landing site (origin for local ENU system) ──
LANDING_LAT = 18.4447      # degrees N
LANDING_LON = 77.4508      # degrees E
MARS_RADIUS_M = 3_389_500  # meters


def enu_to_latlon(east_m, north_m):
    """Convert local ENU meters to Mars areocentric lat/lon."""
    d_lat = np.degrees(north_m / MARS_RADIUS_M)
    d_lon = np.degrees(east_m / (MARS_RADIUS_M * np.cos(np.radians(LANDING_LAT))))
    return LANDING_LAT + d_lat, LANDING_LON + d_lon


def latlon_to_enu(lat, lon):
    """Convert Mars lat/lon to local ENU meters from landing site."""
    north_m = np.radians(lat - LANDING_LAT) * MARS_RADIUS_M
    east_m = np.radians(lon - LANDING_LON) * MARS_RADIUS_M * np.cos(np.radians(LANDING_LAT))
    return east_m, north_m


# ─────────────────────────────────────────────────────────────────────────────
# NAMED LOCATIONS IN JEZERO CRATER (ENU meters from Wright Brothers Field)
# ─────────────────────────────────────────────────────────────────────────────
LOCATIONS = {
    # Airfields
    "Wright Brothers Field":    (0,      0),
    "Airfield B":               (50,   -105),
    "Airfield C":               (160,  -320),
    "Airfield D":               (-92,  -457),
    "Airfield E":               (22,   -622),
    "Airfield F":               (290,  -875),
    "Airfield G":               (528, -1053),
    "Airfield H":               (640, -1280),
    "Airfield I":               (810, -1490),
    "Airfield J":               (950, -1720),
    "Airfield K":               (1100, -2010),
    "Airfield L":               (1250, -2280),
    "Airfield M":               (1420, -2490),
    "Airfield N":               (1580, -2680),
    "Airfield O":               (1730, -2890),

    # Geographic features
    "Séítah Region":            (350,  -900),
    "Raised Ridges":            (750, -1350),
    "Kodiak Butte":             (1300, -1950),
    "Hawksbill Gap":            (1450, -2200),
    "Jezero Delta Front":       (1600, -2500),
    "Belva Crater":             (1850, -2750),
    "Mt. Julian":               (2050, -3000),
    "Upper Delta":              (2200, -3200),
}

# ─────────────────────────────────────────────────────────────────────────────
# FLIGHT PATH DATA
# Each flight: list of (east_m, north_m) waypoints
# First point = takeoff, last point = landing
# ─────────────────────────────────────────────────────────────────────────────
FLIGHT_PATHS = {
    # ── TECH DEMO PHASE (Flights 1–5) ──
    1:  [(0, 0), (0, 0)],                                          # Vertical hover only
    2:  [(0, 0), (0, 0)],                                          # Hover + lateral drift
    3:  [(0, 0), (25, 0), (50, 0), (50, 0)],                       # 50m out and back
    4:  [(0, 0), (67, 0), (133, 0), (133, 0)],                     # 133m downrange
    5:  [(0, 0), (65, 5), (129, 10), (65, 5), (0, 0)],             # Round trip

    # ── EARLY OPS PHASE (Flights 6–14) ──
    6:  [(0, 0), (50, -40), (108, -80), (50, -105)],               # To Airfield B
    7:  [(50, -105), (100, -130), (155, -155), (50, -105)],        # Scout from B
    8:  [(50, -105), (130, -180), (160, -320)],                    # To Airfield C
    9:  [(160, -320), (400, -360), (700, -350), (785, -340)],      # Long scout east
    10: [(160, -320), (55, -430), (-92, -457)],                    # To Airfield D
    11: [(-92, -457), (-200, -520), (-250, -580), (-92, -457)],    # South Séítah scout
    12: [(-92, -457), (-130, -580), (-160, -700), (-92, -457)],    # Southernmost
    13: [(-92, -457), (-50, -500), (22, -622)],                    # To Airfield E
    14: [(22, -622), (200, -600), (400, -590), (22, -622)],        # Scout from E

    # ── SÉÍTAH PHASE (Flights 15–35) ──
    15: [(22, -622), (200, -680), (400, -730), (600, -755),
         (689, -760)],                                             # Distance record 689m
    16: [(689, -760), (500, -740), (290, -875)],                   # To Airfield F
    17: [(290, -875), (380, -910), (430, -950), (290, -875)],      # Survey from F
    18: [(290, -875), (300, -890), (290, -875)],                   # Short hop
    19: [(290, -875), (420, -920), (478, -930), (290, -875)],      # Hardware search
    20: [(290, -875), (430, -940), (528, -1053)],                  # To Airfield G
    21: [(528, -1053), (600, -1080), (660, -1100), (528, -1053)],  # Artuby ridge
    22: [(528, -1053), (680, -1120), (730, -1150), (528, -1053)],  # Crater rim
    23: [(528, -1053), (700, -1140), (750, -1200), (528, -1053)],  # Raised Ridges approach
    24: [(528, -1053), (750, -1250), (780, -1350), (528, -1053)],  # Raised Ridges scout
    25: [(528, -1053), (800, -1350), (900, -1500),
         (1000, -1600), (1050, -1650)],                            # 704m record
    26: [(1050, -1650), (900, -1550), (750, -1450), (640, -1280)], # To Airfield H
    27: [(640, -1280), (660, -1290), (640, -1280)],                # Short hop
    28: [(640, -1280), (700, -1350), (810, -1490)],                # To Airfield I
    29: [(810, -1490), (860, -1540), (950, -1600), (810, -1490)],  # Transition
    30: [(810, -1490), (830, -1510), (810, -1490)],                # Reposition
    31: [(810, -1490), (880, -1560), (950, -1720)],                # Airfield J approach
    32: [(950, -1720), (1020, -1780), (1050, -1840),
         (950, -1720)],                                            # Delta front survey
    33: [(950, -1720), (960, -1730), (950, -1720)],                # Minor reposition
    34: [(950, -1720), (1000, -1780), (950, -1720)],               # Year-end survey
    35: [(950, -1720), (1020, -1800), (1100, -2010)],              # To Airfield K

    # ── DELTA APPROACH PHASE (Flights 36–57) ──
    36: [(1100, -2010), (1180, -2080), (1250, -2280)],             # To Airfield L
    37: [(1250, -2280), (1280, -2330), (1300, -1950),
         (1250, -2280)],                                           # Kodiak approach
    38: [(1250, -2280), (1320, -2360), (1380, -2400),
         (1250, -2280)],                                           # Kodiak survey
    39: [(1250, -2280), (1330, -2370), (1420, -2490)],             # To Airfield M
    40: [(1420, -2490), (1480, -2550), (1450, -2200),
         (1420, -2490)],                                           # Hawksbill approach
    41: [(1420, -2490), (1500, -2560), (1580, -2680)],             # Through gap to N
    42: [(1580, -2680), (1620, -2720), (1660, -2760),
         (1580, -2680)],                                           # Through the gap
    43: [(1580, -2680), (1680, -2760), (1730, -2890)],             # Upper delta approach
    44: [(1730, -2890), (1750, -2920), (1800, -2950),
         (1730, -2890)],                                           # Delta stratigraphy
    45: [(1730, -2890), (1780, -2950), (1820, -2980),
         (1730, -2890)],                                           # First science flight
    46: [(1730, -2890), (1850, -2990), (2000, -3040),
         (2100, -3060), (1730, -2890)],                            # Long science run
    47: [(1730, -2890), (1800, -2930), (1900, -2960),
         (1730, -2890)],                                           # Castaic area
    48: [(1730, -2890), (1900, -3000), (2050, -3050),
         (2100, -3080), (1730, -2890)],                            # Extended science
    49: [(1730, -2890), (1780, -2920), (1850, -2750)],             # Toward Belva
    50: [(1850, -2750), (1900, -2800), (1950, -2850),
         (1850, -2750)],                                           # Flight 50 milestone
    51: [(1850, -2750), (1900, -2790), (1920, -2830),
         (1850, -2750)],                                           # Belva approach
    52: [(1850, -2750), (1900, -2800), (1950, -2850),
         (2000, -2900), (1850, -2750)],                            # Belva rim imaging
    53: [(1850, -2750), (1950, -2830), (2020, -2880),
         (2100, -2920), (1850, -2750)],                            # 14m altitude
    54: [(1850, -2750), (1920, -2810), (2000, -2850),
         (2100, -2870), (1850, -2750)],                            # Northern delta
    55: [(1850, -2750), (1900, -2780), (1950, -2800),
         (1850, -2750)],                                           # Reconnect with rover
    56: [(1850, -2750), (1920, -2800), (2000, -2840),
         (1850, -2750)],                                           # Upper fan survey
    57: [(1850, -2750), (1950, -2830), (2050, -2880),
         (1850, -2750)],                                           # Berry hollow

    # ── DELTA SCIENCE PHASE (Flights 58–72) ──
    58: [(1850, -2750), (2000, -2870), (2150, -2930),
         (2200, -2960), (1850, -2750)],                            # Stratigraphy
    59: [(1850, -2750), (1900, -2790), (1950, -2820),
         (1850, -2750)],                                           # Reconnect
    60: [(1850, -2750), (1950, -2840), (2050, -2960),
         (1850, -2750)],                                           # Mt. Julian approach
    61: [(1850, -2750), (1920, -2800), (2050, -2870),
         (2134, -2910)],                                           # ⚠ Anomaly — landed off target
    62: [(2134, -2910), (2100, -2880), (2050, -3000)],             # Resume after anomaly
    63: [(2050, -3000), (2080, -3020), (2100, -3050),
         (2050, -3000)],                                           # Mt. Julian survey
    64: [(2050, -3000), (2150, -3080), (2200, -3140),
         (2300, -3180), (2050, -3000)],                            # New altitude 14m
    65: [(2050, -3000), (2120, -3060), (2180, -3100),
         (2050, -3000)],                                           # Year-end science
    66: [(2050, -3000), (2080, -3020), (2100, -3040),
         (2050, -3000)],                                           # Reposition
    67: [(2050, -3000), (2120, -3050), (2200, -3080),
         (2050, -3000)],                                           # Airspeed survey
    68: [(2050, -3000), (2200, -3100), (2300, -3160),
         (2050, -3000)],                                           # Jezero rim approach
    69: [(2050, -3000), (2150, -3080), (2250, -3120),
         (2050, -3000)],                                           # Spring science
    70: [(2050, -3000), (2100, -3040), (2200, -3100),
         (2229, -3120)],                                           # 17m record
    71: [(2229, -3120), (2250, -3130), (2300, -3150),
         (2229, -3120)],                                           # Final scout
    72: [(2229, -3120), (2300, -3170), (2350, -3200),
         (2400, -3220)],                                           # FINAL FLIGHT
}


# ─────────────────────────────────────────────────────────────────────────────
# BUILD TIDY DATAFRAMES
# ─────────────────────────────────────────────────────────────────────────────
def build_path_dataframe():
    """Long-format dataframe of all waypoints: one row per waypoint."""
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
                "lat":         lat,
                "lon":         lon,
                "n_waypoints": len(waypoints),
            })
    return pd.DataFrame(rows)


def build_endpoint_dataframe(flight_df):
    """Takeoff/landing positions merged onto flight metrics: one row per flight."""
    paths = pd.DataFrame([
        {
            "flight_num":     fn,
            "takeoff_east":   pts[0][0],
            "takeoff_north":  pts[0][1],
            "landing_east":   pts[-1][0],
            "landing_north":  pts[-1][1],
            "takeoff_lat":    enu_to_latlon(*pts[0])[0],
            "takeoff_lon":    enu_to_latlon(*pts[0])[1],
            "landing_lat":    enu_to_latlon(*pts[-1])[0],
            "landing_lon":    enu_to_latlon(*pts[-1])[1],
        }
        for fn, pts in FLIGHT_PATHS.items()
    ])
    return flight_df.merge(paths, on="flight_num", how="left")


def build_location_dataframe():
    """Named locations for map annotation."""
    rows = []
    for name, (east_m, north_m) in LOCATIONS.items():
        lat, lon = enu_to_latlon(east_m, north_m)
        rows.append({
            "location":    name,
            "east_m":      east_m,
            "north_m":     north_m,
            "lat":         lat,
            "lon":         lon,
            "is_airfield": "Airfield" in name or name == "Wright Brothers Field",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    path_df = build_path_dataframe()
    loc_df = build_location_dataframe()

    path_df.to_csv("data/ingenuity_paths.csv", index=False)
    loc_df.to_csv("data/ingenuity_locations.csv", index=False)

    print(f"✅ Path data: {len(path_df):,} waypoints across {path_df.flight_num.nunique()} flights")
    print(f"✅ Locations: {len(loc_df)} named features")
    print("\n   Bounding box (ENU meters):")
    print(f"   East:  {path_df.east_m.min():.0f} → {path_df.east_m.max():.0f}")
    print(f"   North: {path_df.north_m.min():.0f} → {path_df.north_m.max():.0f}")
    print(f"\n   Total area covered: ~{(path_df.east_m.max()-path_df.east_m.min())/1000:.1f} × "
          f"{abs(path_df.north_m.min()-path_df.north_m.max())/1000:.1f} km")
