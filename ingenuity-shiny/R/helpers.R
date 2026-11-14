# R/helpers.R — constants, data loading and plot helpers.
# Shiny sources every file in R/ automatically before app.R runs.

BG_COLOR     <- "#0a0a0f"
PANEL_COLOR  <- "#111122"
BORDER_COLOR <- "#2a2a3a"
GRID_COLOR   <- "#1e1e2e"
TEXT_COLOR   <- "#e0e0e0"
ACCENT       <- "#4ECDC4"
SOURCE_NOTE  <- "NASA/JPL-Caltech Mars 2020 map layers"

PHASE_COLORS <- c(
  "Tech Demo" = "#FF6B6B",
  "Ops 2021"  = "#FFA07A",
  "Ops 2022"  = "#4ECDC4",
  "Ops 2023"  = "#A78BFA",
  "Ops 2024"  = "#F472B6"
)
PHASE_LEVELS <- names(PHASE_COLORS)

METRICS <- c(
  "Duration (s)"           = "duration_s",
  "Max altitude (m)"       = "max_alt_m",
  "Distance (m)"           = "distance_m",
  "Top groundspeed (m/s)"  = "max_speed_ms",
  "Average speed (m/s)"    = "avg_speed_ms",
  "Landing elevation (m)"  = "landing_elev_m"
)
metric_label <- function(col) names(METRICS)[match(col, METRICS)]

# ── Data ─────────────────────────────────────────────────────────────────────
as_flag <- function(x) tolower(as.character(x)) == "true"

load_flights <- function(path = "data/ingenuity_flights.csv") {
  df <- read.csv(path, fileEncoding = "UTF-8", stringsAsFactors = FALSE)
  df$earth_date    <- as.Date(df$earth_date)
  df$mission_phase <- factor(df$mission_phase, levels = PHASE_LEVELS)
  df$records[is.na(df$records)] <- ""
  for (col in c("record_flag", "final_flag", "relocated")) df[[col]] <- as_flag(df[[col]])
  df$phase_color   <- unname(PHASE_COLORS[as.character(df$mission_phase)])
  df[order(df$flight_num), ]
}

load_paths <- function(path = "data/ingenuity_paths.csv") {
  df <- read.csv(path, stringsAsFactors = FALSE)
  df$is_takeoff <- as_flag(df$is_takeoff)
  df$is_landing <- as_flag(df$is_landing)
  df[order(df$flight_num, df$step), ]
}

load_locations <- function(path = "data/ingenuity_locations.csv") {
  read.csv(path, fileEncoding = "UTF-8", stringsAsFactors = FALSE)
}

flight_hover <- function(f) {
  paste0(
    "<b>Flight ", f$flight_num, "</b><br>",
    format(f$earth_date, "%b %d, %Y"), " | Sol ", f$sol, "<br>",
    f$route, "<br>",
    "Duration: ", f$duration_s, " s · Altitude: ", f$max_alt_m, " m<br>",
    "Distance: ", f$distance_m, " m · Top speed: ", f$max_speed_ms, " m/s",
    ifelse(f$records != "", paste0("<br><b>New ", f$records, " record</b>"), ""),
    ifelse(f$final_flag, "<br><b>Final flight</b>", "")
  )
}

# ── Plot helpers ─────────────────────────────────────────────────────────────
dark_layout <- function(p, title = NULL, ...) {
  plotly::layout(
    p,
    title         = if (!is.null(title)) list(text = title, x = 0.5,
                                              font = list(size = 15, color = "white")),
    plot_bgcolor  = BG_COLOR,
    paper_bgcolor = PANEL_COLOR,
    font          = list(color = TEXT_COLOR),
    hoverlabel    = list(bgcolor = "#1a1a2e", bordercolor = BORDER_COLOR,
                         font = list(color = "white")),
    ...
  )
}

axis <- function(title = "", ...) {
  list(title = title, gridcolor = GRID_COLOR, zerolinecolor = "#33334a", ...)
}

map_axes <- function(p, xr, yr) {
  plotly::layout(
    p,
    xaxis = axis("East of Wright Brothers Field (m)", range = xr, constrain = "domain"),
    yaxis = axis("North (m)", range = yr, scaleanchor = "x", scaleratio = 1,
                 constrain = "domain")
  )
}

metric_colors <- function(values, domain) {
  scales::col_numeric("viridis", domain = domain)(values)
}

empty_plot <- function(msg = "No flights match the current filters") {
  plotly::plot_ly(type = "scatter", mode = "markers") |>
    dark_layout(
      xaxis = list(visible = FALSE), yaxis = list(visible = FALSE),
      annotations = list(list(text = msg, showarrow = FALSE, xref = "paper",
                              yref = "paper", x = 0.5, y = 0.5,
                              font = list(color = "#888888", size = 14)))
    )
}
