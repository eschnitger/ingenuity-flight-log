# Ingenuity Flight Log

Visualizations of the Ingenuity Mars Helicopter's 72 flights, built four ways
from one dataset: Python (Plotly + Matplotlib), R (ggplot2), Tableau, and an
interactive Shiny app that can be published to GitHub Pages with shinylive.

> **About the data.** The per-flight metrics in `ingenuity_data.py` and the
> waypoints in `ingenuity_positions.py` are an *illustrative* dataset written
> for this visualization exercise. They are not the official JPL flight log:
> battery, image and science counts are invented, paths are schematic, and
> several headline values differ from the real mission (for example, the real
> altitude record of 24 m was set on Flight 61, and Flight 72 reached 12 m).
> Replace `RAW_FLIGHTS` / `FLIGHT_PATHS` with sourced values before presenting
> any of this as fact. Every chart and KPI is computed from the data, so
> nothing else needs to change.

## Layout

```
ingenuity_data.py         72 flights → data/ingenuity_flights.csv
ingenuity_positions.py    waypoints + named locations → data/*.csv
ingenuity_viz.py          6 Plotly charts → outputs/0*.html
ingenuity_map.py          Plotly + Matplotlib maps → outputs/map_*.html, *.png
tableau_export.py         Tableau CSVs + background image → tableau/
tableau/README.md         Tableau build steps and calculated fields
R/ingenuity_viz.R         ggplot2 six-panel dashboard
R/ingenuity_map.R         ggplot2 maps
ingenuity-shiny/          Shiny app (app.R, R/helpers.R, www/, data/)
.github/workflows/        shinylive → GitHub Pages deploy
```

## Run it

```bash
python ingenuity_data.py && python ingenuity_positions.py   # data first
python ingenuity_viz.py
python ingenuity_map.py            # add --download to try the USGS basemap
python tableau_export.py
Rscript R/ingenuity_viz.R
Rscript R/ingenuity_map.R
```

Python needs `pandas numpy plotly matplotlib pillow` (`kaleido` optional, for
PNG export of the Plotly charts). The R scripts need `dplyr tidyr readr ggplot2
glue patchwork ggrepel scales`; `gganimate` + `gifski` are optional and enable
the GIFs.

### Shiny app

```r
install.packages(c("shiny", "bslib", "plotly", "dplyr", "glue", "reactable"))
shiny::runApp("ingenuity-shiny")
```

The app reads its own copy of the CSVs. After changing the data, refresh it:

```bash
cp data/ingenuity_flights.csv data/ingenuity_paths.csv data/ingenuity_locations.csv ingenuity-shiny/data/
```

### GitHub Pages (shinylive)

shinylive compiles the app to WebAssembly so it runs in the browser with no R
server. To preview a build locally:

```r
install.packages("shinylive")
shinylive::export("ingenuity-shiny", "site")
httpuv::runStaticServer("site")
```

To publish: make this folder its own GitHub repository, set
**Settings → Pages → Source** to **GitHub Actions**, and push to `main`. The
workflow in `.github/workflows/deploy_shinylive.yml` builds and deploys. Expect
a 10–30 second first load while the browser downloads the R runtime.
