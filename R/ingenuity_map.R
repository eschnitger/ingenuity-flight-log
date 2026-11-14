# R/ingenuity_map.R — ggplot2 maps of the real flight paths (+ optional GIF)
# Run from the project root:  Rscript R/ingenuity_map.R
source("R/theme_ingenuity.R")
suppressPackageStartupMessages({
  library(patchwork)
  library(ggrepel)
})

flights   <- load_flights()
locations <- load_locations()
paths     <- load_paths() |>
  left_join(select(flights, flight_num, duration_s, max_alt_m, distance_m,
                   max_speed_ms, mission_phase, final_flag),
            by = "flight_num")
dir.create("outputs", showWarnings = FALSE)

pad  <- 250
XLIM <- range(paths$east_m)  + c(-pad, pad)
YLIM <- range(paths$north_m) + c(-pad, pad)

theme_mars_map <- function(base_size = 11) {
  theme_ingenuity(base_size) +
    theme(panel.grid.major = element_line(color = GRD, linewidth = 0.3),
          panel.grid.minor = element_blank(),
          axis.text  = element_text(color = "#666666", size = 7),
          axis.title = element_text(color = "#888888", size = 8),
          legend.background = element_rect(fill = "#111111", color = "#333333"))
}

final_pt <- filter(paths, final_flag, is_landing)
origin   <- annotate("point", x = 0, y = 0, shape = 8, size = 5, color = "#FFD700",
                     stroke = 1.3)

# ── PLOT 1: master map ───────────────────────────────────────────────────────
p_map_main <- ggplot(paths, aes(east_m, north_m, group = flight_num)) +
  geom_path(aes(color = mission_phase), linewidth = 0.8, lineend = "round",
            linejoin = "round") +
  geom_point(data = locations, aes(east_m, north_m), inherit.aes = FALSE,
             shape = 17, size = 1.8, color = "#FFD700") +
  geom_text_repel(data = locations, aes(east_m, north_m, label = short_name),
                  inherit.aes = FALSE, color = "#FFD700", size = 2.4,
                  bg.color = BG, bg.r = 0.15, max.overlaps = 50, seed = 42,
                  segment.color = "#FFD700", segment.alpha = 0.4) +
  origin +
  annotate("label", x = -150, y = 250, label = "Wright Brothers Field\n(first flight)",
           color = "#FFD700", fill = "#1a1a0a", size = 2.8, hjust = 1) +
  annotate("point", x = final_pt$east_m, y = final_pt$north_m, shape = 4,
           size = 4, color = "#FF6B6B", stroke = 1.5) +
  annotate("label", x = final_pt$east_m, y = final_pt$north_m - 280,
           label = "Final flight (F72)", color = "#FF6B6B", fill = "#1a0a0a", size = 2.8) +
  annotate("segment", x = mean(XLIM) - 500, xend = mean(XLIM) + 500,
           y = YLIM[1] + 150, yend = YLIM[1] + 150, color = "white", linewidth = 1.2) +
  annotate("text", x = mean(XLIM), y = YLIM[1] + 260, label = "1 km",
           color = "white", size = 3) +
  scale_color_manual(values = PHASE_COLORS, name = "Phase") +
  coord_equal(xlim = XLIM, ylim = YLIM, expand = FALSE) +
  labs(title = "Ingenuity Helicopter — All 72 Flight Paths",
       subtitle = "Jezero Crater, Mars | April 2021 – January 2024",
       caption = SOURCE_NOTE,
       x = "East of Wright Brothers Field (m)", y = "North (m)") +
  theme_mars_map() +
  theme(legend.position = "inside", legend.position.inside = c(0.01, 0.02),
        legend.justification = c(0, 0))

ggsave("outputs/ingenuity_main_map.png", p_map_main,
       width = 16, height = 11, dpi = 160, bg = BG)
message("✅ outputs/ingenuity_main_map.png")

# ── PLOT 2: same paths, colored by four different metrics ────────────────────
build_metric_map <- function(metric_col, metric_label, option) {
  ggplot(paths, aes(east_m, north_m, group = flight_num)) +
    geom_path(aes(color = .data[[metric_col]]), linewidth = 1, lineend = "round") +
    origin +
    scale_color_viridis_c(option = option, name = NULL) +
    coord_equal(xlim = XLIM, ylim = YLIM, expand = FALSE) +
    labs(title = metric_label, x = NULL, y = NULL) +
    theme_mars_map() +
    theme(plot.title = element_text(size = 11), legend.position = "bottom",
          legend.key.width = unit(1.6, "cm"), legend.key.height = unit(0.3, "cm"))
}

p_metric_maps <- (
  (build_metric_map("duration_s",   "Duration (s)",          "viridis") |
   build_metric_map("max_alt_m",    "Max altitude (m)",      "plasma")) /
  (build_metric_map("distance_m",   "Distance (m)",          "inferno") |
   build_metric_map("max_speed_ms", "Top groundspeed (m/s)", "cividis"))
) +
  plot_annotation(
    title = "Flight Paths Colored by Flight Metric", caption = SOURCE_NOTE,
    theme = theme(plot.background = element_rect(fill = BG, color = NA),
                  plot.title = element_text(color = "white", size = 14, face = "bold",
                                            hjust = 0.5),
                  plot.caption = element_text(color = "#666666", size = 8))
  )

ggsave("outputs/ingenuity_metric_maps.png", p_metric_maps,
       width = 18, height = 13, dpi = 140, bg = BG)
message("✅ outputs/ingenuity_metric_maps.png")

# ── OPTIONAL: animated reveal, one flight per frame ──────────────────────────
if (requireNamespace("gganimate", quietly = TRUE) &&
    requireNamespace("gifski", quietly = TRUE)) {
  library(gganimate)
  p_anim <- ggplot(paths, aes(east_m, north_m, group = flight_num)) +
    geom_path(data = select(paths, -flight_num) |> mutate(g = paste(east_m)),
              aes(group = NULL), color = "#333344", linewidth = 0.4) +
    geom_path(aes(color = mission_phase), linewidth = 1.1) +
    origin +
    scale_color_manual(values = PHASE_COLORS, guide = "none") +
    coord_equal(xlim = XLIM, ylim = YLIM, expand = FALSE) +
    labs(title = "Ingenuity — flight {current_frame} of 72", x = NULL, y = NULL) +
    theme_mars_map() +
    transition_manual(frames = flight_num, cumulative = TRUE)
  anim_save("outputs/ingenuity_map_animation.gif",
            animate(p_anim, nframes = 72, fps = 6, width = 1000, height = 700,
                    bg = BG, renderer = gifski_renderer(loop = TRUE)))
  message("✅ outputs/ingenuity_map_animation.gif")
} else {
  message("(skipping GIF — install.packages(c('gganimate', 'gifski')) to enable)")
}
