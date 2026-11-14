# R/theme_ingenuity.R — shared palette, theme and data loaders for the R scripts
suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
  library(ggplot2)
  library(glue)
})

BG  <- "#0a0a0f"
GRD <- "#1e1e2e"
SOURCE_NOTE <- "Data: NASA/JPL-Caltech Mars 2020 map layers"

PHASE_COLORS <- c(
  "Tech Demo" = "#FF6B6B",
  "Ops 2021"  = "#FFA07A",
  "Ops 2022"  = "#4ECDC4",
  "Ops 2023"  = "#A78BFA",
  "Ops 2024"  = "#F472B6"
)
PHASE_LEVELS <- names(PHASE_COLORS)

load_flights <- function(path = "data/ingenuity_flights.csv") {
  if (!file.exists(path)) stop("Run `python ingenuity_data.py` first to create ", path)
  read_csv(path, show_col_types = FALSE) |>
    mutate(
      earth_date    = as.Date(earth_date),
      mission_phase = factor(mission_phase, levels = PHASE_LEVELS),
      records       = coalesce(records, ""),
      across(c(record_flag, final_flag, relocated), as.logical)
    )
}

load_paths <- function(path = "data/ingenuity_paths.csv") {
  if (!file.exists(path)) stop("Run `python ingenuity_positions.py` first to create ", path)
  read_csv(path, show_col_types = FALSE) |>
    mutate(across(c(is_takeoff, is_landing), as.logical))
}

load_locations <- function(path = "data/ingenuity_locations.csv") {
  read_csv(path, show_col_types = FALSE)
}

# Phase spans (between flights) for background bands
phase_bands <- function(df) {
  df |>
    group_by(mission_phase) |>
    summarise(xmin = min(flight_num) - 0.5, xmax = max(flight_num) + 0.5, .groups = "drop")
}

# Centered rolling mean without extra dependencies
roll_mean <- function(x, k = 5) {
  half <- k %/% 2
  vapply(seq_along(x), function(i) mean(x[max(1, i - half):min(length(x), i + half)]),
         numeric(1))
}

theme_ingenuity <- function(base_size = 11) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.background   = element_rect(fill = BG, color = NA),
      panel.background  = element_rect(fill = BG, color = NA),
      panel.grid.major  = element_line(color = GRD, linewidth = 0.4),
      panel.grid.minor  = element_line(color = "#141420", linewidth = 0.2),
      text              = element_text(color = "white"),
      axis.text         = element_text(color = "#aaaaaa", size = 9),
      axis.title        = element_text(color = "white", size = 10),
      plot.title        = element_text(color = "white", size = 13, face = "bold", hjust = 0.5),
      plot.subtitle     = element_text(color = "#aaaaaa", size = 9, hjust = 0.5),
      plot.caption      = element_text(color = "#666666", size = 7),
      legend.background = element_rect(fill = BG, color = NA),
      legend.key        = element_rect(fill = BG, color = NA),
      legend.text       = element_text(color = "white", size = 9),
      legend.title      = element_text(color = "#aaaaaa", size = 9),
      strip.text        = element_text(color = "white", size = 9, face = "bold"),
      plot.margin       = margin(12, 12, 12, 12)
    )
}
