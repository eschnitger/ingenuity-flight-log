# Ingenuity Flight Log

Visualizations of all 72 flights of NASA's Ingenuity Mars Helicopter, built
four ways from one dataset: Python (Plotly + Matplotlib), R (ggplot2), Tableau,
and an interactive Shiny app published to GitHub Pages with shinylive.

**Live app:** https://eschnitger.github.io/ingenuity-flight-log/

## Data

Everything comes from the two Ingenuity layers behind NASA's
[Where is Perseverance?](https://science.nasa.gov/mission/mars-2020-perseverance/location-map/)
map, committed in `data/raw/`:

| File | Contents |
|---|---|
| `m20_heli_waypoints.json` | one point per flight: date, sol, duration, max altitude, distance, top groundspeed, from/to airfield, landing position and elevation |
| `m20_heli_flight_path.json` | the flown path of every flight as a line |

Courtesy NASA/JPL-Caltech. Refresh with `python fetch_nasa_data.py`.

Derived in `ingenuity_data.py`, not from NASA:

- **Phase:** flights 1–5 are the tech demo, later flights are grouped by Earth year.
- **Average speed:** distance ÷ duration.
- **Records:** a flight that strictly beats every earlier flight on duration,
  altitude, distance or top speed.
- **Local coordinates:** meters east/north of Wright Brothers Field, from lat/lon
  with Mars radius 3,396,190 m; paths simplified to 0.5 m for plotting.

Headline numbers: 128.9 minutes of airtime, 18.14 km flown, 24 m maximum
altitude (flight 61), 10 m/s top groundspeed (flight 62), 44 airfields.

## Layout

```
fetch_nasa_data.py        download data/raw/*.json from NASA
ingenuity_data.py         raw JSON → data/ingenuity_flights.csv
ingenuity_positions.py    raw JSON → data/ingenuity_paths.csv, ingenuity_locations.csv
ingenuity_viz.py          6 Plotly charts → outputs/0*.html
ingenuity_map.py          Plotly + Matplotlib maps → outputs/map_*.html, *.png
tableau_export.py         Tableau CSVs + background → tableau/
R/                        ggplot2 dashboard and maps
ingenuity-shiny/          Shiny app (app.R, R/helpers.R, www/, data/)
.github/workflows/        shinylive → GitHub Pages deploy
```

## Run it

```bash
python ingenuity_data.py && python ingenuity_positions.py
python ingenuity_viz.py
python ingenuity_map.py
python tableau_export.py
Rscript R/ingenuity_viz.R
Rscript R/ingenuity_map.R
```

Python needs `pandas numpy plotly matplotlib pillow` (`kaleido` optional, for
PNG export of the Plotly charts). R needs `dplyr tidyr readr ggplot2 glue
patchwork ggrepel scales`; `gganimate` + `gifski` are optional and enable GIFs.

### Shiny app

```r
install.packages(c("shiny", "bslib", "plotly", "dplyr", "glue", "reactable"))
shiny::runApp("ingenuity-shiny")
```

The app reads its own copy of the CSVs. After regenerating the data:

```bash
cp data/ingenuity_flights.csv data/ingenuity_paths.csv data/ingenuity_locations.csv ingenuity-shiny/data/
```

### GitHub Pages

Pushing changes under `ingenuity-shiny/` to `main` rebuilds and deploys the
app through `.github/workflows/deploy_shinylive.yml`. To preview a build
locally:

```r
shinylive::export("ingenuity-shiny", "site")
httpuv::runStaticServer("site")
```
