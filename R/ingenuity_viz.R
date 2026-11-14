# R/ingenuity_viz.R — six-panel ggplot2 dashboard (+ optional gganimate GIF)
# Run from the project root:  Rscript R/ingenuity_viz.R
source("R/theme_ingenuity.R")
suppressPackageStartupMessages({
  library(patchwork)
  library(scales)
  library(ggrepel)
})

df <- load_flights()
bands <- phase_bands(df)
dir.create("outputs", showWarnings = FALSE)

x_flights <- scale_x_continuous(breaks = seq(0, 72, 10), expand = expansion(add = 0.5))
band_layer <- geom_rect(data = bands, inherit.aes = FALSE,
                        aes(xmin = xmin, xmax = xmax, ymin = -Inf, ymax = Inf,
                            fill = mission_phase),
                        alpha = 0.07, show.legend = FALSE)

# ── PLOT 1: duration lollipop ────────────────────────────────────────────────
p1_duration <- ggplot(df, aes(flight_num, duration_s)) +
  band_layer +
  geom_segment(aes(xend = flight_num, yend = 0, color = mission_phase),
               linewidth = 0.6, alpha = 0.6) +
  geom_point(aes(color = mission_phase, size = distance_m), alpha = 0.9) +
  geom_line(aes(y = roll_mean(duration_s)), color = "white",
            linewidth = 0.8, linetype = "dashed", alpha = 0.5) +
  geom_label_repel(
    data = slice_max(df, duration_s, n = 3),
    aes(label = glue("F{flight_num}: {duration_s} s")),
    color = "#FFD700", fill = "#1a1a0a", size = 2.8, nudge_y = 20,
    segment.color = "#FFD700", seed = 1
  ) +
  scale_fill_manual(values = PHASE_COLORS, guide = "none") +
  scale_color_manual(values = PHASE_COLORS, name = "Phase") +
  scale_size_continuous(range = c(1.5, 7), guide = "none") +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = " s"), limits = c(0, 200)) +
  labs(title = "Flight Duration",
       subtitle = "Dot size = distance flown | Dashed line = 5-flight rolling average",
       x = "Flight number", y = "Duration (s)") +
  theme_ingenuity()

# ── PLOT 2: altitude with running record ─────────────────────────────────────
alt <- mutate(df, alt_record = cummax(max_alt_m))
p2_altitude <- ggplot(alt, aes(flight_num)) +
  geom_col(aes(y = max_alt_m, fill = mission_phase), width = 0.7, alpha = 0.9) +
  geom_step(aes(y = alt_record), direction = "mid", color = "#FFD700",
            linewidth = 0.7, linetype = "dashed") +
  geom_label_repel(
    data = filter(alt, grepl("altitude", records)),
    aes(y = max_alt_m, label = glue("F{flight_num}: {max_alt_m} m")),
    color = "#FFD700", fill = "#1a1a0a", size = 3, nudge_y = 3, nudge_x = -4,
    segment.color = "#FFD700", seed = 1
  ) +
  scale_fill_manual(values = PHASE_COLORS, name = "Phase") +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = " m")) +
  labs(title = "Maximum Altitude per Flight",
       subtitle = "Dashed gold line = running altitude record",
       x = "Flight number", y = "Max altitude (m)") +
  theme_ingenuity()

# ── PLOT 3: distance per flight ──────────────────────────────────────────────
p3_distance <- ggplot(df, aes(flight_num, distance_m)) +
  geom_col(aes(fill = mission_phase), width = 0.7, alpha = 0.9, show.legend = FALSE) +
  geom_line(aes(y = roll_mean(distance_m)), color = "white",
            linewidth = 0.8, linetype = "dashed", alpha = 0.5) +
  geom_label_repel(
    data = filter(df, grepl("distance", records), distance_m > 600),
    aes(label = glue("F{flight_num}: {round(distance_m)} m")),
    color = "#FFD700", fill = "#1a1a0a", size = 2.8, nudge_y = 80,
    segment.color = "#FFD700", seed = 1
  ) +
  scale_fill_manual(values = PHASE_COLORS) +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = " m")) +
  labs(title = "Distance Flown per Flight",
       subtitle = "Gold labels = distance records above 600 m",
       x = "Flight number", y = "Distance (m)") +
  theme_ingenuity()

# ── PLOT 4: top groundspeed with record line ─────────────────────────────────
p4_speed <- ggplot(df, aes(flight_num)) +
  geom_col(aes(y = max_speed_ms, fill = mission_phase), width = 0.7, alpha = 0.9,
           show.legend = FALSE) +
  geom_step(aes(y = cummax(max_speed_ms)), direction = "mid", color = "#FFD700",
            linewidth = 0.7, linetype = "dashed") +
  scale_fill_manual(values = PHASE_COLORS) +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = " m/s")) +
  labs(title = "Top Groundspeed per Flight",
       subtitle = "Dashed gold line = running speed record",
       x = "Flight number", y = "Top groundspeed (m/s)") +
  theme_ingenuity()

# ── PLOT 5: cumulative distance ──────────────────────────────────────────────
p5_cumulative <- ggplot(df, aes(flight_num, cumulative_distance_m / 1000)) +
  geom_area(fill = "#4ECDC4", alpha = 0.3) +
  geom_line(color = "#4ECDC4", linewidth = 1.2) +
  geom_point(data = filter(df, flight_num %% 10 == 0 | final_flag),
             color = "white", size = 2.5) +
  geom_label_repel(
    data = filter(df, flight_num %in% c(20, 40, 60) | final_flag),
    aes(label = glue("F{flight_num}: {round(cumulative_distance_m / 1000, 1)} km")),
    color = "#4ECDC4", fill = BG, size = 3, nudge_x = -8, nudge_y = 1.5,
    segment.color = "#4ECDC4", seed = 1
  ) +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = " km")) +
  labs(title = "Cumulative Distance Flown",
       subtitle = glue("Total: {round(sum(df$distance_m) / 1000, 2)} km over {nrow(df)} flights"),
       x = "Flight number", y = "Cumulative distance (km)") +
  theme_ingenuity()

# ── PLOT 6: duration vs distance ─────────────────────────────────────────────
moved <- filter(df, distance_m > 20)
r_val <- round(cor(moved$duration_s, moved$distance_m), 2)

p6_scatter <- ggplot(moved, aes(duration_s, distance_m)) +
  geom_smooth(method = "lm", formula = y ~ x, se = TRUE, color = "white",
              fill = "white", alpha = 0.06, linetype = "dashed", linewidth = 0.7) +
  geom_point(aes(color = mission_phase, size = max_alt_m), alpha = 0.85) +
  geom_label_repel(
    data = slice_max(moved, distance_m, n = 5),
    aes(label = glue("F{flight_num}")),
    color = "white", fill = "#00000080", size = 3, segment.color = "white", seed = 1
  ) +
  annotate("text", x = min(moved$duration_s), y = max(moved$distance_m),
           label = glue("r = {r_val}"), color = "#aaaaaa", size = 3.8, hjust = 0) +
  scale_color_manual(values = PHASE_COLORS, name = "Phase") +
  scale_size_continuous(range = c(1.5, 7), name = "Altitude (m)") +
  scale_x_continuous(labels = label_number(suffix = " s")) +
  scale_y_continuous(labels = label_number(suffix = " m")) +
  labs(title = "Duration vs Distance",
       subtitle = "Dot size = max altitude | flights under 20 m excluded",
       x = "Duration (s)", y = "Distance (m)") +
  theme_ingenuity()

# ── COMBINE ──────────────────────────────────────────────────────────────────
dashboard <- (p1_duration | p2_altitude) /
  (p3_distance | p4_speed) /
  (p5_cumulative | p6_scatter) +
  plot_annotation(
    title    = "INGENUITY MARS HELICOPTER — COMPLETE FLIGHT LOG",
    subtitle = glue("{nrow(df)} flights | {format(min(df$earth_date), '%B %d, %Y')} – ",
                    "{format(max(df$earth_date), '%B %d, %Y')} | Jezero Crater, Mars"),
    caption  = SOURCE_NOTE,
    theme    = theme(
      plot.background = element_rect(fill = BG, color = NA),
      plot.title      = element_text(color = "white", size = 20, face = "bold", hjust = 0.5),
      plot.subtitle   = element_text(color = "#aaaaaa", size = 11, hjust = 0.5),
      plot.caption    = element_text(color = "#666666", size = 8, hjust = 1)
    )
  )

ggsave("outputs/ingenuity_dashboard.png", dashboard,
       width = 20, height = 20, dpi = 150, bg = BG)
message("✅ Dashboard → outputs/ingenuity_dashboard.png")

# ── OPTIONAL: animated cumulative distance ───────────────────────────────────
if (requireNamespace("gganimate", quietly = TRUE) &&
    requireNamespace("gifski", quietly = TRUE)) {
  library(gganimate)
  anim <- ggplot(df, aes(flight_num, cumulative_distance_m / 1000)) +
    geom_area(fill = "#4ECDC4", alpha = 0.3) +
    geom_line(color = "#4ECDC4", linewidth = 1.5) +
    geom_point(color = "white", size = 3) +
    scale_x_continuous(limits = c(1, 72), breaks = seq(0, 72, 10)) +
    scale_y_continuous(labels = label_number(suffix = " km")) +
    labs(title = "Ingenuity: cumulative distance, flight {round(frame_along)}",
         x = "Flight number", y = "Cumulative distance (km)") +
    theme_ingenuity() +
    transition_reveal(flight_num)
  anim_save("outputs/ingenuity_cumulative_distance.gif",
            animate(anim, nframes = 144, fps = 10, width = 900, height = 500,
                    bg = BG, renderer = gifski_renderer()))
  message("✅ Animation → outputs/ingenuity_cumulative_distance.gif")
} else {
  message("(skipping GIF — install.packages(c('gganimate', 'gifski')) to enable)")
}
