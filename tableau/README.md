# Tableau build notes

Run `python tableau_export.py` from the project root first. It writes the three
CSVs and the background image into this folder.

## Data source setup

1. Connect to `tableau_ingenuity_paths.csv`
2. Field types:
   - `x_meters_east`, `y_meters_north` → Number (decimal)
   - `path_order` → Number (whole) — required for path drawing
   - `flight_num` → Number (whole)
   - `earth_date` → Date

## Sheet 1 — path map

1. `x_meters_east` → Columns, `y_meters_north` → Rows (both as continuous **dimensions**)
2. Mark type → **Line**
3. `flight_num` → Detail (one path per flight)
4. `path_order` → Path
5. `mission_phase` → Color
6. Fix both axes: X `-400 … 2800`, Y `-3600 … 500`
7. Map → Background Images → add `mars_terrain_tableau.png` with
   Left `-400`, Right `2800`, Bottom `-3600`, Top `500`

## Sheet 2 — endpoints (dual axis or floating overlay)

Source `tableau_ingenuity_endpoints.csv`; mark type Shape; triangle/green for
`is_takeoff_point`, X/red for `is_landing_point`. Same fixed axes.

## Sheet 3 — named locations

Source `tableau_ingenuity_locations.csv`; x = `east_m`, y = `north_m`;
shape + color by `is_airfield`; label = `location`. Same fixed axes.

## Sheets 4+ — metric panels

Flight # on Columns, `[Dynamic Metric]` on Rows, color by `mission_phase`.
Use `tableau_ingenuity_endpoints.csv` filtered to `is_takeoff_point` (one row
per flight) so sums are not multiplied by the number of waypoints.

## Parameters

| Parameter | Type | Values |
|---|---|---|
| `Selected Metric` | String list | Duration, Altitude, Distance, Battery, Images, Science |
| `Map Color By` | String list | Phase, Duration, Altitude, Battery, Images |
| `Selected Flight` | Integer | 0–72 (0 = none) |

## Calculated fields

```
// Dynamic Metric
CASE [Selected Metric]
WHEN "Duration" THEN FLOAT([duration_s])
WHEN "Altitude" THEN FLOAT([max_alt_m])
WHEN "Distance" THEN FLOAT([distance_m])
WHEN "Battery"  THEN FLOAT([battery_used])
WHEN "Images"   THEN FLOAT([images_taken])
WHEN "Science"  THEN FLOAT([science_measurements])
END

// Dynamic Metric Label
CASE [Selected Metric]
WHEN "Duration" THEN "Duration (seconds)"
WHEN "Altitude" THEN "Max Altitude (meters)"
WHEN "Distance" THEN "Distance Traveled (meters)"
WHEN "Battery"  THEN "Battery Used (%)"
WHEN "Images"   THEN "Images Captured"
WHEN "Science"  THEN "Science Measurements"
END

// Map Color Value (continuous; use [mission_phase] directly when Map Color By = "Phase")
CASE [Map Color By]
WHEN "Duration" THEN FLOAT([duration_s])
WHEN "Altitude" THEN FLOAT([max_alt_m])
WHEN "Battery"  THEN FLOAT([battery_used])
WHEN "Images"   THEN FLOAT([images_taken])
END

// Path Opacity (fades earlier flights) — put on Color opacity via a continuous field
0.3 + ([flight_num] / 72.0) * 0.65

// Path Line Width — put on Size
IF [flight_num] = [Selected Flight] THEN 3.0 ELSE 1.0 END

// Waypoint Label
IF [is_takeoff_point] THEN "▲ T/O F" + STR([flight_num])
ELSEIF [is_landing_point] THEN "✕ LDG F" + STR([flight_num])
ELSE "" END

// Running Altitude Record (table calc along flight_num)
RUNNING_MAX(MAX([max_alt_m]))

// Running Distance Total (table calc along flight_num, one row per flight)
RUNNING_SUM(SUM([distance_m]))

// Battery Efficiency (m per % battery)
IF [battery_used] > 0 THEN [distance_m] / [battery_used] ELSE 0 END

// Distance from Origin
SQRT([x_meters_east]^2 + [y_meters_north]^2)

// Net Flight Bearing (degrees clockwise from north, takeoff → landing)
// { FIXED } LODs pick the takeoff and landing rows of each flight.
(DEGREES(ATAN2(
  { FIXED [flight_num] : MAX(IIF([is_landing_point], [x_meters_east], NULL)) }
    - { FIXED [flight_num] : MAX(IIF([is_takeoff_point], [x_meters_east], NULL)) },
  { FIXED [flight_num] : MAX(IIF([is_landing_point], [y_meters_north], NULL)) }
    - { FIXED [flight_num] : MAX(IIF([is_takeoff_point], [y_meters_north], NULL)) }
)) + 360) % 360

// Tooltip
"Flight " + STR([flight_num]) + CHAR(10) +
"Date: " + STR([earth_date]) + " | Sol " + STR([sol]) + CHAR(10) +
"Phase: " + [mission_phase] + CHAR(10) +
"Duration: " + STR([duration_s]) + "s" + CHAR(10) +
"Altitude: " + STR([max_alt_m]) + "m" + CHAR(10) +
"Distance: " + STR([distance_m]) + "m" + CHAR(10) +
"Battery: " + STR([battery_start_pct]) + "% → " + STR([battery_end_pct]) +
  "% (" + STR([battery_used]) + "% used)" + CHAR(10) +
"Images: " + STR([images_taken]) +
IIF([anomaly_flag], CHAR(10) + "⚠ ANOMALY FLIGHT", "")
```

## Dashboard layout

```
┌───────────┬───────────────────────────────────────────┬───────────────┐
│ FILTERS   │ KPI strip (flights · airtime · km · imgs) │               │
│ Phase     ├───────────────────────────────────────────┤ FLIGHT DETAIL │
│ Type      │                                           │ (filter       │
│ Flight #  │ PATH MAP  (sheets 1–3 layered, floating,  │  action from  │
│ Sol range │            identical fixed axes)          │  map click)   │
│ Metric ▾  │                                           │               │
│ Color by ▾├───────────────────────────────────────────┴───────────────┤
│ [Reset]   │ Metric panels: timeline · altitude · battery · science    │
└───────────┴───────────────────────────────────────────────────────────┘
```

Actions: map/timeline click → filter action on `flight_num` into the detail
sheet; highlight action on `mission_phase` across all sheets.
