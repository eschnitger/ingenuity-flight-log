# R/ingenuity_map.R — ggplot2 flight-path maps (+ optional gganimate GIF)
# Run from the project root:  Rscript R/ingenuity_map.R
source("R/theme_ingenuity.R")
suppressPackageStartupMessages({
  library(patchwork)
  library(ggrepel)
})

flights   <- load_flights()
locations <- load_locations()
paths     <- load_paths() |>
  left_join(
    select(flights, flight_num, duration_s, max_alt_m, distance_m, battery_used,
           mission_phase, anomaly_flag, images_taken),
    by = "flight_num"
  )
dir.create("outputs", showWarnings = FALSE)

XLIM <- c(-400, 2800)
YLIM <- c(-3600, 500)

theme_mars_map <- function(base_size = 11) {
  theme_ingenuity(base_size) +
    theme(
      panel.grid.major = element_line(color = GRD, linewidth = 0.3),
      panel.grid.minor = element_blank(),
      axis.text        = element_text(color = "#666666", size = 7),
      axis.title       = element_text(color = "#888888", size = 8),
      legend.background = element_rect(fill = "#111111", color = "#333333")
    )
}

# One row per path segment
segments <- paths |>
  arrange(flight_num, step) |>
  group_by(flight_num) |>
  mutate(x_end = lead(east_m), y_end = lead(north_m)) |>
  filter(!is.na(x_end)) |>
  ungroup()

origin_layer <- function(size = 5) {
  annotate("point", x = 0, y = 0, shape = 8, size = size, color = "#FFD700", stroke = 1.3)
}

# ── PLOT 1: master map ───────────────────────────────────────────────────────
final_pt <- paths |> filter(flight_num == 72, is_landing)

p_map_main <- ggplot() +
  geom_segment(
    data = segments,
    aes(east_m, north_m, xend = x_end, yend = y_end,
        color = mission_phase, alpha = flight_num),
    linewidth = 0.9, lineend = "round"
  ) +
  geom_point(
    data = filter(paths, anomaly_flag, is_landing),
    aes(east_m, north_m), shape = 4, size = 4, color = "#FF6B6B", stroke = 1.5
  ) +
  geom_point(
    data = filter(locations, is_airfield, location != "Wright Brothers Field"),
    aes(east_m, north_m), shape = 17, size = 2.5, color = "#FFD700", alpha = 0.8
  ) +
  geom_point(
    data = filter(locations, !is_airfield),
    aes(east_m, north_m), shape = 18, size = 3, color = "#D4A96A", alpha = 0.8
  ) +
  geom_text_repel(
    data = filter(locations, !is_airfield),
    aes(east_m, north_m, label = location),
    color = "#D4A96A", size = 3, fontface = "bold",
    bg.color = BG, bg.r = 0.15, nudge_x = 250, direction = "y",
    segment.color = "#D4A96A", segment.alpha = 0.5, seed = 42
  ) +
  origin_layer(6) +
  annotate("label", x = 130, y = 150, label = "Wright Brothers Field\n(origin)",
           color = "#FFD700", fill = "#1a1a0a", size = 2.8, hjust = 0) +
  annotate("label", x = final_pt$east_m, y = final_pt$north_m - 170,
           label = "Final landing\nFlight 72",
           color = "#FF6B6B", fill = "#1a0a0a", size = 2.8) +
  # North arrow
  annotate("segment", x = 2650, xend = 2650, y = 50, yend = 350,
           color = "white", linewidth = 1,
           arrow = arrow(length = unit(8, "pt"), type = "closed")) +
  annotate("text", x = 2650, y = 420, label = "N", color = "white",
           size = 4, fontface = "bold") +
  # Scale bar
  annotate("segment", x = 2200, xend = 2700, y = -3500, yend = -3500,
           color = "white", linewidth = 1.5) +
  annotate("text", x = 2450, y = -3420, label = "500 m", color = "white", size = 3) +
  scale_color_manual(values = PHASE_COLORS, name = "Mission Phase") +
  scale_alpha_continuous(range = c(0.45, 0.95), guide = "none") +
  coord_equal(xlim = XLIM, ylim = YLIM, expand = FALSE) +
  labs(
    title    = "Ingenuity Helicopter — All 72 Flight Paths",
    subtitle = "Jezero Crater, Mars | 18.44°N 77.45°E | April 2021 – January 2024",
    caption  = "Schematic paths in local ENU meters from Wright Brothers Field (see README)",
    x = "East (meters)", y = "North (meters)"
  ) +
  theme_mars_map() +
  theme(legend.position = "inside",
        legend.position.inside = c(0.02, 0.02),
        legend.justification = c(0, 0))

ggsave("outputs/ingenuity_main_map.png", p_map_main,
       width = 11, height = 14.5, dpi = 170, bg = BG)
message("✅ outputs/ingenuity_main_map.png")

# ── PLOT 2: same paths, coloured by four different metrics ───────────────────
build_metric_map <- function(metric_col, metric_label, option) {
  ggplot(segments) +
    geom_segment(
      aes(east_m, north_m, xend = x_end, yend = y_end, color = .data[[metric_col]]),
      linewidth = 1.2, alpha = 0.85, lineend = "round"
    ) +
    origin_layer(4) +
    scale_color_viridis_c(option = option, name = NULL) +
    coord_equal(xlim = XLIM, ylim = YLIM, expand = FALSE) +
    labs(title = metric_label, x = NULL, y = NULL) +
    theme_mars_map() +
    theme(plot.title = element_text(size = 11),
          legend.position = "bottom",
          legend.key.width = unit(1.4, "cm"),
          legend.key.height = unit(0.3, "cm"))
}

p_metric_maps <- (
  build_metric_map("duration_s",   "Duration (s)",     "viridis") |
  build_metric_map("max_alt_m",    "Max altitude (m)", "plasma")  |
  build_metric_map("battery_used", "Battery used (%)", "inferno") |
  build_metric_map("images_taken", "Images captured",  "cividis")
) +
  plot_annotation(
    title    = "Flight Path Maps — Colored by Mission Metric",
    subtitle = "Same paths, one metric per panel",
    theme    = theme(
      plot.background = element_rect(fill = BG, color = NA),
      plot.title      = element_text(color = "white", size = 14, face = "bold", hjust = 0.5),
      plot.subtitle   = element_text(color = "#aaaaaa", size = 9, hjust = 0.5)
    )
  )

ggsave("outputs/ingenuity_metric_maps.png", p_metric_maps,
       width = 20, height = 8.5, dpi = 150, bg = BG)
message("✅ outputs/ingenuity_metric_maps.png")

# ── OPTIONAL: animated reveal, one flight per frame ──────────────────────────
if (requireNamespace("gganimate", quietly = TRUE) &&
    requireNamespace("gifski", quietly = TRUE)) {
  library(gganimate)

  p_anim <- ggplot() +
    geom_segment(
      data = select(segments, -flight_num),      # static grey context
      aes(east_m, north_m, xend = x_end, yend = y_end),
      color = "#333344", linewidth = 0.4, alpha = 0.5
    ) +
    geom_segment(
      data = segments,
      aes(east_m, north_m, xend = x_end, yend = y_end,
          color = mission_phase, group = flight_num),
      linewidth = 1.2, alpha = 0.85
    ) +
    origin_layer(5) +
    scale_color_manual(values = PHASE_COLORS, guide = "none") +
    coord_equal(xlim = XLIM, ylim = YLIM, expand = FALSE) +
    labs(title = "Ingenuity — Flight {current_frame} of 72",
         subtitle = "Jezero Crater, Mars", x = NULL, y = NULL) +
    theme_mars_map() +
    transition_manual(frames = flight_num, cumulative = TRUE)

  anim_save("outputs/ingenuity_map_animation.gif",
            animate(p_anim, nframes = 72, fps = 6, width = 700, height = 900,
                    bg = BG, renderer = gifski_renderer(loop = TRUE)))
  message("✅ outputs/ingenuity_map_animation.gif")
} else {
  message("(skipping GIF — install.packages(c('gganimate', 'gifski')) to enable)")
}
