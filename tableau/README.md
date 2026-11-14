# Tableau build notes

Run `python tableau_export.py` from the project root first. It writes the CSVs
and a background image into this folder:

| File | Grain | Use for |
|---|---|---|
| `tableau_ingenuity_paths.csv` | one row per path vertex (970) | the path map |
| `tableau_ingenuity_flights.csv` | one row per flight (72) | metric sheets, KPIs, detail card |
| `tableau_ingenuity_locations.csv` | one row per airfield (44) | airfield labels |
| `mars_terrain_tableau.png` | — | decorative backdrop (not real terrain) |

Coordinates are meters east/north of Wright Brothers Field, from NASA's
flight paths. The window is East `-7500 … 300`, North `-1300 … 3600`.

## Sheet 1 — path map

1. Source `tableau_ingenuity_paths.csv`
2. `x_meters_east` → Columns, `y_meters_north` → Rows (continuous **dimensions**)
3. Mark type → **Line**; `flight_num` → Detail; `path_order` → Path
4. `mission_phase` → Color
5. Fix the axes to the window above and make them equal-scaled
6. Optional: Map → Background Images → `mars_terrain_tableau.png` with
   Left `-7500`, Right `300`, Bottom `-1300`, Top `3600`

## Sheet 2 — airfields (dual axis or floating overlay)

Source `tableau_ingenuity_locations.csv`; x = `east_m`, y = `north_m`;
triangle shape; label = `short_name`. Same fixed axes.

## Metric sheets

Source `tableau_ingenuity_flights.csv` so each flight counts once.
`flight_num` on Columns, `[Dynamic Metric]` on Rows, color by `mission_phase`.

## Parameters

| Parameter | Type | Values |
|---|---|---|
| `Selected Metric` | String list | Duration, Altitude, Distance, Top Speed, Avg Speed |
| `Selected Flight` | Integer | 0–72 (0 = none) |

## Calculated fields

```
// Dynamic Metric
CASE [Selected Metric]
WHEN "Duration"  THEN [duration_s]
WHEN "Altitude"  THEN [max_alt_m]
WHEN "Distance"  THEN [distance_m]
WHEN "Top Speed" THEN [max_speed_ms]
WHEN "Avg Speed" THEN [avg_speed_ms]
END

// Path Line Width — put on Size
IF [flight_num] = [Selected Flight] THEN 3.0 ELSE 1.0 END

// Running Altitude Record (table calc along flight_num)
RUNNING_MAX(MAX([max_alt_m]))

// Running Distance Total (table calc along flight_num)
RUNNING_SUM(SUM([distance_m]))

// Distance from Wright Brothers Field
SQRT([x_meters_east]^2 + [y_meters_north]^2)

// Tooltip
"Flight " + STR([flight_num]) + CHAR(10) +
STR([earth_date]) + " | Sol " + STR([sol]) + CHAR(10) +
[route] + CHAR(10) +
"Duration: " + STR([duration_s]) + " s  ·  Altitude: " + STR([max_alt_m]) + " m" + CHAR(10) +
"Distance: " + STR([distance_m]) + " m  ·  Top speed: " + STR([max_speed_ms]) + " m/s" +
IIF([record_flag], CHAR(10) + "New " + [records] + " record", "")
```

Actions: path click → filter action on `flight_num` into a detail sheet;
highlight action on `mission_phase` across sheets.

Data: NASA/JPL-Caltech Mars 2020 map layers.
