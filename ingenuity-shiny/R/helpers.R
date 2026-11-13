# R/helpers.R — constants, data loading and plot helpers.
# Shiny sources every file in R/ automatically before app.R runs.

BG_COLOR     <- "#0a0a0f"
PANEL_COLOR  <- "#111122"
BORDER_COLOR <- "#2a2a3a"
GRID_COLOR   <- "#1e1e2e"
TEXT_COLOR   <- "#e0e0e0"
ACCENT       <- "#4ECDC4"

PHASE_LEVELS <- c("Tech Demo", "Early Ops", "Séítah", "Delta Approach", "Delta Science")
PHASE_COLORS <- c(
  "Tech Demo"      = "#FF6B6B",
  "Early Ops"      = "#FFA07A",
  "Séítah"         = "#4ECDC4",
  "Delta Approach" = "#45B7D1",
  "Delta Science"  = "#96CEB4"
)
TYPE_LABELS <- c(tech_demo = "Tech Demo", ops = "Operations",
                 scout = "Scout", science = "Science")

METRICS <- c(
  "Duration (s)"         = "duration_s",
  "Max altitude (m)"     = "max_alt_m",
  "Distance (m)"         = "distance_m",
  "Battery used (%)"     = "battery_used",
  "Images captured"      = "images_taken",
  "Science measurements" = "science_measurements"
)
metric_label <- function(col) names(METRICS)[match(col, METRICS)]

MAP_X <- c(-400, 2800)
MAP_Y <- c(-3600, 500)

# ── Data ─────────────────────────────────────────────────────────────────────
as_flag <- function(x) tolower(as.character(x)) == "true"

load_flights <- function(path = "data/ingenuity_flights.csv") {
  df <- read.csv(path, fileEncoding = "UTF-8", stringsAsFactors = FALSE)
  df$earth_date    <- as.Date(df$earth_date)
  df$mission_phase <- factor(df$mission_phase, levels = PHASE_LEVELS)
  df$flight_type   <- factor(unname(TYPE_LABELS[df$flight_type]), levels = unname(TYPE_LABELS))
  df$anomaly_flag  <- as_flag(df$anomaly_flag)
  df$record_flag   <- as_flag(df$record_flag)
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
  df <- read.csv(path, fileEncoding = "UTF-8", stringsAsFactors = FALSE)
  df$is_airfield <- as_flag(df$is_airfield)
  df
}

flight_hover <- function(f) {
  paste0(
    "<b>Flight ", f$flight_num, "</b><br>",
    format(f$earth_date, "%b %d, %Y"), " | Sol ", f$sol, "<br>",
    "Phase: ", f$mission_phase, "<br>",
    "Duration: ", f$duration_s, " s<br>",
    "Altitude: ", f$max_alt_m, " m<br>",
    "Distance: ", f$distance_m, " m<br>",
    "Battery used: ", f$battery_used, "%<br>",
    "Images: ", f$images_taken,
    ifelse(f$anomaly_flag, "<br><b>⚠ ANOMALY FLIGHT</b>", "")
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

map_axes <- function(p) {
  plotly::layout(
    p,
    xaxis = axis("East (m from Wright Brothers Field)", range = MAP_X,
                 constrain = "domain"),
    yaxis = axis("North (m)", range = MAP_Y, scaleanchor = "x", scaleratio = 1,
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
