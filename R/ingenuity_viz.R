# R/ingenuity_viz.R — six-panel ggplot2 dashboard (+ optional gganimate GIF)
# Run from the project root:  Rscript R/ingenuity_viz.R
source("R/theme_ingenuity.R")
suppressPackageStartupMessages({
  library(patchwork)
  library(scales)
  library(ggrepel)
})

df <- load_flights()
dir.create("outputs", showWarnings = FALSE)

x_flights <- scale_x_continuous(breaks = seq(0, 72, 10), expand = expansion(add = 0.5))

# ── PLOT 1: duration lollipop ────────────────────────────────────────────────
p1_duration <- ggplot(df, aes(flight_num, duration_s)) +
  phase_band_layer() +
  scale_fill_manual(values = PHASE_COLORS, guide = "none") +
  geom_segment(aes(xend = flight_num, yend = 0, color = mission_phase),
               linewidth = 0.6, alpha = 0.6) +
  geom_point(aes(color = mission_phase, size = distance_m), alpha = 0.9) +
  geom_line(aes(y = roll_mean(duration_s, 5)),
            color = "white", linewidth = 0.8, linetype = "dashed", alpha = 0.5) +
  geom_label_repel(
    data = filter(df, anomaly_flag),
    aes(label = glue("F{flight_num} anomaly")),
    color = "#FF6B6B", fill = "#1a0a0a", size = 3, nudge_y = 45,
    segment.color = "#FF6B6B"
  ) +
  geom_label_repel(
    data = slice_max(df, duration_s, n = 3),
    aes(label = glue("F{flight_num}: {duration_s}s")),
    color = "#FFD700", fill = "#1a1a0a", size = 2.8, nudge_y = 22,
    segment.color = "#FFD700"
  ) +
  scale_color_manual(values = PHASE_COLORS, name = "Mission Phase") +
  scale_size_continuous(range = c(1.5, 7), guide = "none") +
  x_flights +
  scale_y_continuous(
    labels = label_number(suffix = "s"), limits = c(0, 240),
    sec.axis = sec_axis(~ . / 60, name = "Duration (minutes)")
  ) +
  labs(title = "Flight Duration",
       subtitle = "Dot size = distance traveled | Dashed line = 5-flight rolling average",
       x = "Flight Number", y = "Duration (seconds)") +
  theme_ingenuity()

# ── PLOT 2: altitude with running record ─────────────────────────────────────
alt <- mutate(df, alt_record = cummax(max_alt_m))
p2_altitude <- ggplot(alt, aes(flight_num)) +
  geom_col(aes(y = max_alt_m, fill = mission_phase), width = 0.7, alpha = 0.85) +
  geom_step(aes(y = alt_record), direction = "mid",
            color = "#FFD700", linewidth = 0.7, linetype = "dashed") +
  geom_label_repel(
    data = filter(alt, max_alt_m == alt_record, max_alt_m >= 14) |>
      distinct(max_alt_m, .keep_all = TRUE),
    aes(y = max_alt_m, label = glue("F{flight_num}: {max_alt_m}m")),
    color = "#FFD700", fill = "#1a1a0a", size = 3, nudge_y = 2, nudge_x = -6,
    segment.color = "#FFD700"
  ) +
  scale_fill_manual(values = PHASE_COLORS, name = "Mission Phase") +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = "m")) +
  labs(title = "Maximum Altitude per Flight",
       subtitle = "Dashed gold line = running altitude record",
       x = "Flight Number", y = "Max Altitude (meters)") +
  theme_ingenuity()

# ── PLOT 3: battery used ─────────────────────────────────────────────────────
mean_batt <- mean(df$battery_used)
p3_battery <- ggplot(df, aes(flight_num, battery_used)) +
  geom_col(aes(fill = battery_used), width = 0.7, alpha = 0.9) +
  geom_hline(yintercept = mean_batt, color = "#FFD700", linewidth = 0.6,
             linetype = "dashed", alpha = 0.8) +
  annotate("label", x = 1, y = mean_batt + 1.1,
           label = glue("Mean: {round(mean_batt, 1)}%"),
           color = "#FFD700", fill = BG, size = 3, hjust = 0) +
  scale_fill_gradient2(low = "#4ECDC4", mid = "#FFA07A", high = "#FF6B6B",
                       midpoint = mean_batt, name = "Battery\nused (%)") +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = "%")) +
  labs(title = "Battery Usage per Flight",
       subtitle = "Start-of-flight minus end-of-flight state of charge",
       x = "Flight Number", y = "Battery Used (%)") +
  theme_ingenuity()

# ── PLOT 4: images + science measurements (separate scales) ──────────────────
science_long <- df |>
  select(flight_num, Images = images_taken,
         `Science measurements` = science_measurements) |>
  pivot_longer(-flight_num, names_to = "metric", values_to = "count")

p4_science <- ggplot(science_long, aes(flight_num, count, fill = metric)) +
  geom_col(width = 0.7, alpha = 0.85, show.legend = FALSE) +
  geom_vline(xintercept = PHASE_BANDS$xmin[-1], color = "white",
             linewidth = 0.3, linetype = "dotted", alpha = 0.4) +
  facet_wrap(~metric, ncol = 1, scales = "free_y") +
  scale_fill_manual(values = c("Images" = "#45B7D1",
                               "Science measurements" = "#96CEB4")) +
  x_flights +
  labs(title = "Images & Science Measurements per Flight",
       subtitle = "Dotted lines = mission phase boundaries",
       x = "Flight Number", y = "Count") +
  theme_ingenuity()

# ── PLOT 5: cumulative distance ──────────────────────────────────────────────
p5_cumulative <- ggplot(df, aes(flight_num, cumulative_distance_m / 1000)) +
  geom_area(fill = "#4ECDC4", alpha = 0.3) +
  geom_line(color = "#4ECDC4", linewidth = 1.2) +
  geom_point(data = filter(df, flight_num %% 10 == 0 | flight_num == 72),
             color = "white", size = 2.5) +
  geom_label_repel(
    data = filter(df, flight_num %in% c(20, 40, 60, 72)),
    aes(label = glue("F{flight_num}: {round(cumulative_distance_m / 1000, 1)} km")),
    color = "#4ECDC4", fill = BG, size = 3, nudge_x = -8, nudge_y = 1.5,
    segment.color = "#4ECDC4"
  ) +
  x_flights +
  scale_y_continuous(labels = label_number(suffix = " km")) +
  labs(title = "Cumulative Distance Flown",
       subtitle = glue("Total: {round(sum(df$distance_m) / 1000, 2)} km over {nrow(df)} flights"),
       x = "Flight Number", y = "Cumulative Distance (km)") +
  theme_ingenuity()

# ── PLOT 6: duration vs distance ─────────────────────────────────────────────
moved <- filter(df, distance_m > 0)
r_val <- round(cor(moved$duration_s, moved$distance_m), 2)

p6_scatter <- ggplot(moved, aes(duration_s, distance_m)) +
  geom_smooth(method = "lm", formula = y ~ x, se = TRUE, color = "white",
              fill = "white", alpha = 0.06, linetype = "dashed", linewidth = 0.7) +
  geom_point(aes(color = flight_type, size = max_alt_m), alpha = 0.85) +
  geom_label_repel(
    data = slice_max(moved, distance_m, n = 5),
    aes(label = glue("F{flight_num}")),
    color = "white", fill = "#00000080", size = 3, segment.color = "white"
  ) +
  annotate("text", x = min(moved$duration_s), y = max(moved$distance_m),
           label = glue("r = {r_val}"), color = "#aaaaaa", size = 3.8, hjust = 0) +
  scale_color_manual(values = TYPE_COLORS, name = "Flight Type") +
  scale_size_continuous(range = c(2, 7), name = "Altitude (m)") +
  scale_x_continuous(labels = label_number(suffix = "s")) +
  scale_y_continuous(labels = label_number(suffix = "m")) +
  labs(title = "Flight Duration vs Distance Traveled",
       subtitle = "Dot size = max altitude | Flights with zero distance excluded",
       x = "Flight Duration (seconds)", y = "Distance Traveled (meters)") +
  theme_ingenuity()

# ── COMBINE ──────────────────────────────────────────────────────────────────
dashboard <- (p1_duration | p2_altitude) /
  (p3_battery | p4_science) /
  (p5_cumulative | p6_scatter) +
  plot_annotation(
    title    = "INGENUITY HELICOPTER — COMPLETE FLIGHT LOG",
    subtitle = glue("{nrow(df)} flights | {format(min(df$earth_date), '%B %d, %Y')} – ",
                    "{format(max(df$earth_date), '%B %d, %Y')} | Mars 2020 Mission"),
    caption  = "Illustrative dataset (see README) | Visualization: R / ggplot2",
    theme    = theme(
      plot.background = element_rect(fill = BG, color = NA),
      plot.title      = element_text(color = "white", size = 20, face = "bold", hjust = 0.5),
      plot.subtitle   = element_text(color = "#aaaaaa", size = 11, hjust = 0.5),
      plot.caption    = element_text(color = "#666666", size = 8, hjust = 1)
    )
  )

ggsave("outputs/ingenuity_dashboard.png", dashboard,
       width = 20, height = 22, dpi = 150, bg = BG)
message("✅ Dashboard → outputs/ingenuity_dashboard.png")

# ── OPTIONAL: animated cumulative distance ───────────────────────────────────
if (requireNamespace("gganimate", quietly = TRUE) &&
    requireNamespace("gifski", quietly = TRUE)) {
  library(gganimate)
  anim <- ggplot(df, aes(flight_num, cumulative_distance_m / 1000)) +
    geom_area(fill = "#4ECDC4", alpha = 0.3) +
    geom_line(color = "#4ECDC4", linewidth = 1.5) +
    geom_point(color = "white", size = 3) +
    geom_text(
      aes(x = 4, y = max(cumulative_distance_m / 1000) * 0.9,
          label = glue("Flight {flight_num}  |  {format(earth_date, '%b %d, %Y')}\n",
                       "Sol {sol}  |  This flight: {distance_m} m\n",
                       "Total flown: {round(cumulative_distance_m / 1000, 2)} km")),
      hjust = 0, color = "white", size = 4
    ) +
    scale_x_continuous(limits = c(1, 72), breaks = seq(0, 72, 10)) +
    scale_y_continuous(labels = label_number(suffix = " km")) +
    labs(title = "Ingenuity: Cumulative Distance",
         x = "Flight Number", y = "Cumulative Distance (km)") +
    theme_ingenuity() +
    transition_reveal(flight_num)

  anim_save("outputs/ingenuity_cumulative_distance.gif",
            animate(anim, nframes = 144, fps = 10, width = 900, height = 500,
                    bg = BG, renderer = gifski_renderer()))
  message("✅ Animation → outputs/ingenuity_cumulative_distance.gif")
} else {
  message("(skipping GIF — install.packages(c('gganimate', 'gifski')) to enable)")
}
