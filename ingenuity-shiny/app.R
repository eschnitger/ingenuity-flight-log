# app.R — Ingenuity Flight Log (Shiny)
# Runs as a normal Shiny app (shiny::runApp("ingenuity-shiny")) and as a
# shinylive/WebAssembly export for GitHub Pages. Dependencies are kept small
# on purpose: every package is one more download in the browser.

library(shiny)
library(bslib)
library(plotly)
library(dplyr)
library(glue)
library(reactable)

FLIGHTS   <- load_flights()
PATHS     <- load_paths()
LOCATIONS <- load_locations()

N_FLIGHTS <- nrow(FLIGHTS)
SOL_RANGE <- range(FLIGHTS$sol)
MAP_X     <- range(PATHS$east_m)  + c(-250, 250)
MAP_Y     <- range(PATHS$north_m) + c(-250, 250)

# Path vertices with flight metrics attached
PATHS_FULL <- PATHS |>
  left_join(FLIGHTS, by = "flight_num") |>
  mutate(hover = flight_hover(pick(everything())))

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
kpi_card <- function(id, label) {
  div(class = "kpi-card",
      div(class = "kpi-value", textOutput(id, inline = TRUE)),
      div(class = "kpi-label", label))
}

ui <- page_sidebar(
  title = "Ingenuity Flight Log",
  theme = bs_theme(version = 5, bg = BG_COLOR, fg = TEXT_COLOR, primary = ACCENT),
  fillable = FALSE,
  tags$head(tags$link(rel = "stylesheet", href = "styles.css")),

  sidebar = sidebar(
    width = 250, bg = "#0d0d1a", fg = TEXT_COLOR,  # explicit fg skips a Sass contrast check
    p("FILTER FLIGHTS", class = "sidebar-section-title"),
    checkboxGroupInput("sel_phase", "Phase", PHASE_LEVELS, PHASE_LEVELS),
    checkboxInput("only_moves", "Only flights that moved to a new airfield", FALSE),
    sliderInput("sel_flight_range", "Flight number", 1, N_FLIGHTS,
                c(1, N_FLIGHTS), step = 1),
    sliderInput("sel_sol_range", "Sol", SOL_RANGE[1], SOL_RANGE[2], SOL_RANGE, step = 1),
    actionButton("reset_filters", "Reset filters", class = "btn-sm btn-outline-light"),
    hr(),
    p("SELECTED FLIGHT", class = "sidebar-section-title"),
    uiOutput("sidebar_selected")
  ),

  div(class = "kpi-strip",
      kpi_card("kpi_flights",  "Flights"),
      kpi_card("kpi_airtime",  "Airtime"),
      kpi_card("kpi_distance", "Distance"),
      kpi_card("kpi_alt",      "Max altitude"),
      kpi_card("kpi_speed",    "Top speed"),
      kpi_card("kpi_fields",   "Airfields reached")),

  # Keep this static UI shallow. In the browser, R renders the page on a small
  # call stack, and Safari runs out of stack on deeply nested tags (the app
  # then fails with a 404). So the tabs aren't wrapped in a card, and the two
  # tabs with nested controls are rendered by the server (map_tab, anim_tab).
  navset_tab(
    id = "main_tabs",

    nav_panel("Flight Map",  uiOutput("map_tab")),
    nav_panel("Performance", plotlyOutput("metrics_plot", height = "680px")),
    nav_panel("Cumulative",  plotlyOutput("cumulative_plot", height = "460px")),
    nav_panel("Timeline",    plotlyOutput("timeline_plot", height = "540px")),
    nav_panel("Animation",   uiOutput("anim_tab")),

    nav_panel(
      "Data",
      downloadButton("download_csv", "Download filtered CSV",
                     class = "btn-sm btn-outline-light mb-2"),
      reactableOutput("flight_table")
    ),

    nav_panel(
      "About",
      div(class = "about-content",
          h4("Ingenuity Mars Helicopter"),
          p("The first powered, controlled flights on another planet: 72 flights in",
            "Jezero Crater between April 19, 2021 and January 18, 2024, ending when",
            "rotor damage was found after flight 72."),
          p(strong("Data: "), "flight dates, durations, altitudes, distances, top",
            "groundspeeds, airfields and flown paths come from the Ingenuity layers",
            "behind NASA's", tags$a("Where is Perseverance? map", target = "_blank",
            href = "https://science.nasa.gov/mission/mars-2020-perseverance/location-map/"),
            "(", tags$code("m20_heli_waypoints.json"), "and",
            tags$code("m20_heli_flight_path.json"), "), courtesy NASA/JPL-Caltech."),
          p(strong("Derived here: "), "phases (tech demo = flights 1–5, then",
            "operations by Earth year), average speed (distance ÷ duration), records",
            "(a flight beating every earlier one) and route labels. Distances are",
            "NASA's per-flight figures; the drawn paths are simplified to 0.5 m."),
          p(class = "text-muted", "Built with R, Shiny, bslib and plotly."))
    )
  )
)

# ─────────────────────────────────────────────────────────────────────────────
# SERVER
# ─────────────────────────────────────────────────────────────────────────────
server <- function(input, output, session) {

  # Tab bodies with nested controls (kept out of the static UI; see the note
  # above navset_tab). Their inputs are NULL until rendered, so the plots that
  # read them wait with req().
  output$map_tab <- renderUI({
    div(class = "map-layout",
        div(
          div(class = "controls-row",
              selectInput("color_by", "Color paths by",
                          c("Phase" = "phase", METRICS[1:4]), width = "200px"),
              checkboxGroupInput("show_layers", "Layers",
                                 c("Airfields" = "airfields", "Landings" = "landings"),
                                 selected = "airfields", inline = TRUE)),
          plotlyOutput("flight_map", height = "640px")),
        uiOutput("detail_card"))
  })

  output$anim_tab <- renderUI({
    tagList(
      div(class = "controls-row",
          sliderInput("anim_flight", "Flight", 1, N_FLIGHTS, 1, step = 1, width = "60%",
                      animate = animationOptions(interval = 700, loop = FALSE)),
          checkboxInput("anim_cumulative", "Keep earlier flights visible", TRUE)),
      plotlyOutput("anim_map", height = "640px"))
  })

  selected_flight <- reactiveVal(NULL)

  flight_range <- debounce(reactive(input$sel_flight_range), 250)
  sol_range    <- debounce(reactive(input$sel_sol_range), 250)

  filtered <- reactive({
    FLIGHTS |>
      filter(
        mission_phase %in% input$sel_phase,
        !input$only_moves | relocated,
        between(flight_num, flight_range()[1], flight_range()[2]),
        between(sol, sol_range()[1], sol_range()[2])
      )
  })

  observeEvent(input$reset_filters, {
    updateCheckboxGroupInput(session, "sel_phase", selected = PHASE_LEVELS)
    updateCheckboxInput(session, "only_moves", value = FALSE)
    updateSliderInput(session, "sel_flight_range", value = c(1, N_FLIGHTS))
    updateSliderInput(session, "sel_sol_range", value = SOL_RANGE)
    selected_flight(NULL)
  })

  observe({
    fn <- selected_flight()
    if (!is.null(fn) && !fn %in% filtered()$flight_num) selected_flight(NULL)
  })

  selected_row <- reactive({
    fn <- selected_flight()
    if (is.null(fn)) NULL else FLIGHTS[FLIGHTS$flight_num == fn, ]
  })

  for (src in c("map", "metrics", "timeline", "cumulative")) local({
    s <- src
    observeEvent(event_data("plotly_click", source = s, priority = "event"), {
      fn <- event_data("plotly_click", source = s)$customdata
      if (!is.null(fn) && !is.na(fn[[1]])) selected_flight(as.integer(fn[[1]]))
    }, ignoreInit = TRUE)
  })

  # ── KPIs ───────────────────────────────────────────────────────────────────
  kpi <- function(f) renderText({
    df <- filtered()
    if (nrow(df) == 0) "–" else f(df)
  })
  output$kpi_flights  <- renderText(nrow(filtered()))
  output$kpi_airtime  <- kpi(\(d) glue("{round(sum(d$duration_s) / 60, 1)} min"))
  output$kpi_distance <- kpi(\(d) glue("{round(sum(d$distance_m) / 1000, 2)} km"))
  output$kpi_alt      <- kpi(\(d) glue("{max(d$max_alt_m)} m"))
  output$kpi_speed    <- kpi(\(d) glue("{max(d$max_speed_ms)} m/s"))
  output$kpi_fields   <- kpi(\(d) length(unique(d$to_airfield)))

  output$sidebar_selected <- renderUI({
    row <- selected_row()
    if (is.null(row)) return(div(class = "sidebar-no-selection", "No flight selected"))
    div(class = "sidebar-flight-info",
        p(style = glue("color:{row$phase_color}; font-weight:bold; margin:0;"),
          glue("Flight {row$flight_num}")),
        p(class = "small-muted", format(row$earth_date, "%b %d, %Y")),
        actionLink("clear_selection", "✕ Clear selection", class = "small-muted"))
  })
  observeEvent(input$clear_selection, selected_flight(NULL))

  # ── Flight map ─────────────────────────────────────────────────────────────
  output$flight_map <- renderPlotly({
    df <- filtered()
    if (nrow(df) == 0) return(empty_plot())
    pts <- PATHS_FULL |> filter(flight_num %in% df$flight_num)
    sel <- selected_flight()
    by  <- req(input$color_by)

    pts$line_color <- if (by == "phase") pts$phase_color else
      metric_colors(pts[[by]], range(FLIGHTS[[by]]))

    p <- plot_ly(source = "map") |>
      add_paths(data = pts, x = ~east_m, y = ~north_m, split = ~flight_num,
                color = ~I(line_color), line = list(width = 2.2),
                opacity = if (is.null(sel)) 0.9 else 0.35,
                text = ~hover, hoverinfo = "text", customdata = ~flight_num,
                showlegend = FALSE)

    if (by == "phase") {
      for (ph in intersect(PHASE_LEVELS, as.character(df$mission_phase))) {
        p <- p |> add_paths(x = NA_real_, y = NA_real_, name = ph,
                            line = list(color = PHASE_COLORS[[ph]], width = 3))
      }
    } else {
      p <- p |> add_markers(
        data = filter(pts, is_takeoff), x = ~east_m, y = ~north_m,
        hoverinfo = "skip", showlegend = FALSE,
        marker = list(size = 0.1, color = as.formula(paste0("~", by)),
                      colorscale = "Viridis", showscale = TRUE,
                      cmin = min(FLIGHTS[[by]]), cmax = max(FLIGHTS[[by]]),
                      colorbar = list(title = metric_label(by), thickness = 12)))
    }

    if ("airfields" %in% input$show_layers) {
      p <- p |> add_trace(
        data = LOCATIONS, x = ~east_m, y = ~north_m, type = "scatter",
        mode = "markers+text", text = ~short_name, textposition = "top center",
        textfont = list(size = 9, color = "#FFD700"),
        hovertext = ~paste0(location, "<br>first landing: flight ", first_flight),
        hoverinfo = "text",
        marker = list(symbol = "triangle-up", size = 8, color = "#FFD700"),
        showlegend = FALSE)
    }
    if ("landings" %in% input$show_layers) {
      p <- p |> add_markers(
        data = filter(pts, is_landing), x = ~east_m, y = ~north_m, name = "Landing",
        marker = list(symbol = "x", size = 6, color = "#FF6B6B"),
        text = ~paste0("Landing F", flight_num), hoverinfo = "text",
        customdata = ~flight_num)
    }

    if (!is.null(sel)) {
      sp <- filter(pts, flight_num == sel)
      p <- p |>
        add_paths(data = sp, x = ~east_m, y = ~north_m,
                  line = list(color = "white", width = 6), hoverinfo = "skip",
                  showlegend = FALSE) |>
        add_paths(data = sp, x = ~east_m, y = ~north_m,
                  line = list(color = sp$line_color[1], width = 3.5),
                  text = ~hover, hoverinfo = "text", customdata = ~flight_num,
                  showlegend = FALSE) |>
        add_markers(data = sp[nrow(sp), ], x = ~east_m, y = ~north_m,
                    marker = list(size = 11, color = "white",
                                  line = list(color = "yellow", width = 2)),
                    hoverinfo = "skip", showlegend = FALSE)
    }

    p |>
      dark_layout(uirevision = "map", margin = list(t = 20, r = 10, b = 40, l = 50),
                  legend = list(bgcolor = "rgba(0,0,0,0.5)", x = 0.01, y = 0.01,
                                xanchor = "left", yanchor = "bottom")) |>
      map_axes(MAP_X, MAP_Y) |>
      event_register("plotly_click")
  })

  # ── Detail card ────────────────────────────────────────────────────────────
  output$detail_card <- renderUI({
    row <- selected_row()
    if (is.null(row)) {
      return(div(class = "detail-card detail-placeholder",
                 "Click a flight path, bar or table row to see its details."))
    }
    stat <- function(label, value, sub = NULL) {
      div(class = "metric-card",
          div(class = "metric-value", value),
          div(class = "metric-label", label),
          if (!is.null(sub)) div(class = "metric-sub", sub))
    }
    fns <- filtered()$flight_num
    pos <- match(row$flight_num, fns)

    div(class = "detail-card",
        div(class = "detail-header",
            span(class = "detail-flight-num", style = glue("color:{row$phase_color};"),
                 glue("Flight {row$flight_num}")),
            if (row$final_flag) span(class = "badge-anomaly", "FINAL FLIGHT")
            else if (row$record_flag) span(class = "badge-record", "RECORD"),
            div(class = "small-muted",
                glue("{format(row$earth_date, '%B %d, %Y')} · Sol {row$sol}")),
            div(class = "small-muted", as.character(row$mission_phase))),
        div(class = "metric-grid",
            stat("Duration", glue("{row$duration_s} s"),
                 glue("{round(row$duration_s / 60, 1)} min")),
            stat("Max altitude", glue("{row$max_alt_m} m")),
            stat("Distance", glue("{row$distance_m} m")),
            stat("Top speed", glue("{row$max_speed_ms} m/s"),
                 glue("{row$avg_speed_ms} m/s average")),
            stat("Landing elevation", glue("{round(row$landing_elev_m)} m"),
                 "relative to Mars datum"),
            stat("Day of mission", glue("{row$days_since_f1}"), "days after flight 1")),
        div(class = "detail-notes",
            row$route,
            if (row$records != "") tagList(br(), glue("New {row$records} record"))),
        div(class = "detail-nav",
            actionButton("prev_flight", "← Prev", class = "btn-sm btn-outline-light"),
            span(class = "small-muted", glue("{pos} of {length(fns)}")),
            actionButton("next_flight", "Next →", class = "btn-sm btn-outline-light")))
  })

  step_selection <- function(by) {
    fns <- filtered()$flight_num
    pos <- match(selected_flight(), fns) + by
    if (!is.na(pos) && pos >= 1 && pos <= length(fns)) selected_flight(fns[pos])
  }
  observeEvent(input$prev_flight, step_selection(-1))
  observeEvent(input$next_flight, step_selection(1))

  # ── Performance: six panels ────────────────────────────────────────────────
  output$metrics_plot <- renderPlotly({
    df <- filtered()
    if (nrow(df) == 0) return(empty_plot())
    is_sel <- df$flight_num %in% selected_flight()

    panels <- lapply(seq_along(METRICS), function(i) {
      col <- METRICS[[i]]
      hov <- paste0("Flight %{x}<br>", names(METRICS)[i], ": %{y}<extra></extra>")
      p <- plot_ly(df, x = ~flight_num, y = as.formula(paste0("~", col)),
                   source = "metrics", customdata = ~flight_num)
      p <- if (col == "landing_elev_m") {
        add_trace(p, type = "scatter", mode = "lines+markers",
                  line = list(color = "#D4A96A"),
                  marker = list(color = df$phase_color, size = ifelse(is_sel, 12, 5)),
                  hovertemplate = hov)
      } else {
        add_bars(p, marker = list(color = df$phase_color,
                                  line = list(color = "white", width = ifelse(is_sel, 2.5, 0))),
                 hovertemplate = hov)
      }
      layout(p, xaxis = axis("Flight number"), yaxis = axis(names(METRICS)[i]))
    })

    subplot(panels, nrows = 2, shareX = TRUE, titleY = TRUE, margin = 0.06) |>
      dark_layout(showlegend = FALSE, bargap = 0.2, margin = list(t = 30, l = 60, r = 10)) |>
      event_register("plotly_click")
  })

  # ── Cumulative totals (over the filtered flights) ──────────────────────────
  output$cumulative_plot <- renderPlotly({
    df <- filtered()
    if (nrow(df) == 0) return(empty_plot())
    series <- list(
      list("Distance (km)",     cumsum(df$distance_m) / 1000, "#4ECDC4"),
      list("Airtime (minutes)", cumsum(df$duration_s) / 60,   "#A78BFA")
    )
    panels <- lapply(series, function(s) {
      plot_ly(x = df$flight_num, y = s[[2]], type = "scatter", mode = "lines",
              fill = "tozeroy", source = "cumulative", customdata = df$flight_num,
              line = list(color = s[[3]], width = 2), fillcolor = paste0(s[[3]], "33"),
              hovertemplate = paste0("After flight %{x}<br>", s[[1]],
                                     ": %{y:,.2f}<extra></extra>")) |>
        layout(xaxis = axis("Flight number"), yaxis = axis(paste("Cumulative", s[[1]])))
    })
    subplot(panels, nrows = 1, titleX = TRUE, titleY = TRUE, margin = 0.07) |>
      dark_layout(showlegend = FALSE, margin = list(t = 30, l = 60, r = 10)) |>
      event_register("plotly_click")
  })

  # ── Timeline bubble chart ──────────────────────────────────────────────────
  output$timeline_plot <- renderPlotly({
    df <- filtered()
    if (nrow(df) == 0) return(empty_plot())
    sel <- selected_row()
    top <- max(FLIGHTS$max_alt_m) * 1.15

    spans <- FLIGHTS |> group_by(mission_phase) |>
      summarise(lo = min(flight_num), hi = max(flight_num), .groups = "drop")
    bands <- lapply(seq_len(nrow(spans)), function(i) {
      list(type = "rect", x0 = spans$lo[i] - 0.5, x1 = spans$hi[i] + 0.5, y0 = 0, y1 = top,
           fillcolor = PHASE_COLORS[[as.character(spans$mission_phase[i])]],
           opacity = 0.08, layer = "below", line = list(width = 0))
    })
    labels <- lapply(seq_len(nrow(spans)), function(i) {
      ph <- as.character(spans$mission_phase[i])
      list(x = (spans$lo[i] + spans$hi[i]) / 2, y = top, text = ph, showarrow = FALSE,
           yanchor = "top", font = list(color = PHASE_COLORS[[ph]], size = 10))
    })

    p <- plot_ly(df, x = ~flight_num, y = ~max_alt_m, source = "timeline") |>
      add_lines(line = list(color = "rgba(255,255,255,0.15)", width = 1), hoverinfo = "skip") |>
      add_markers(
        customdata = ~flight_num, text = flight_hover(df), hoverinfo = "text",
        marker = list(size = sqrt(pmax(df$distance_m, 1)) * 1.3 + 5,
                      color = ~duration_s, colorscale = "Viridis", showscale = TRUE,
                      colorbar = list(title = "Duration (s)", thickness = 12),
                      opacity = 0.85, line = list(width = 0.5, color = "white")))
    if (!is.null(sel)) {
      p <- p |> add_markers(data = sel, x = ~flight_num, y = ~max_alt_m, hoverinfo = "skip",
                            marker = list(size = 28, color = "rgba(0,0,0,0)",
                                          line = list(color = "yellow", width = 2.5)))
    }
    p |>
      dark_layout(
        title = "Max altitude by flight<br><sup>Bubble size = distance · color = duration</sup>",
        showlegend = FALSE, shapes = bands, annotations = labels,
        xaxis = axis("Flight number", dtick = 5),
        yaxis = axis("Max altitude (m)", range = c(0, top)),
        margin = list(t = 70)) |>
      event_register("plotly_click")
  })

  # ── Animation ──────────────────────────────────────────────────────────────
  output$anim_map <- renderPlotly({
    cur  <- req(input$anim_flight)
    row  <- FLIGHTS[FLIGHTS$flight_num == cur, ]
    now  <- filter(PATHS_FULL, flight_num == cur)
    past <- filter(PATHS_FULL, flight_num < cur)

    p <- plot_ly()
    if (isTRUE(input$anim_cumulative) && nrow(past) > 0) {
      p <- p |> add_paths(data = past, x = ~east_m, y = ~north_m, split = ~flight_num,
                          color = ~I(phase_color), opacity = 0.35,
                          line = list(width = 1.4), hoverinfo = "skip")
    }
    p |>
      add_paths(data = now, x = ~east_m, y = ~north_m,
                line = list(color = row$phase_color, width = 4),
                text = ~hover, hoverinfo = "text") |>
      add_markers(data = now[nrow(now), ], x = ~east_m, y = ~north_m, hoverinfo = "skip",
                  marker = list(size = 12, color = "white",
                                line = list(width = 2, color = "yellow"))) |>
      add_markers(x = 0, y = 0, hoverinfo = "skip",
                  marker = list(symbol = "star", size = 14, color = "#FFD700")) |>
      dark_layout(
        title = glue("<b>Flight {cur} of {N_FLIGHTS}</b> · ",
                     "{format(row$earth_date, '%B %d, %Y')} · Sol {row$sol}",
                     "<br><sup>{row$notes}</sup>"),
        showlegend = FALSE, uirevision = "anim", margin = list(t = 70)) |>
      map_axes(MAP_X, MAP_Y)
  })

  # ── Data table ─────────────────────────────────────────────────────────────
  table_data <- reactive({
    filtered() |>
      select(Flight = flight_num, Date = earth_date, Sol = sol, Phase = mission_phase,
             `Duration (s)` = duration_s, `Alt (m)` = max_alt_m, `Dist (m)` = distance_m,
             `Top speed (m/s)` = max_speed_ms, From = from_airfield, To = to_airfield,
             Records = records)
  })

  output$flight_table <- renderReactable({
    reactable(
      table_data(), selection = "single", onClick = "select",
      searchable = TRUE, compact = TRUE, highlight = TRUE, defaultPageSize = 18,
      columns = list(
        From = colDef(minWidth = 150), To = colDef(minWidth = 150),
        Records = colDef(minWidth = 140),
        Phase = colDef(minWidth = 100, style = function(value) {
          list(color = PHASE_COLORS[[as.character(value)]], fontWeight = 600)
        })
      ),
      theme = reactableTheme(
        color = TEXT_COLOR, backgroundColor = PANEL_COLOR, borderColor = BORDER_COLOR,
        highlightColor = "rgba(78,205,196,0.08)",
        rowSelectedStyle = list(backgroundColor = "rgba(78,205,196,0.18)"),
        inputStyle = list(backgroundColor = BG_COLOR, color = TEXT_COLOR),
        pageButtonStyle = list(color = TEXT_COLOR)
      )
    )
  })

  observeEvent(getReactableState("flight_table", "selected"), {
    idx <- getReactableState("flight_table", "selected")
    if (length(idx) == 1) selected_flight(table_data()$Flight[idx])
  })

  output$download_csv <- downloadHandler(
    filename = function() glue("ingenuity_flights_{Sys.Date()}.csv"),
    content  = function(file) write.csv(select(filtered(), -phase_color), file,
                                        row.names = FALSE)
  )
}

shinyApp(ui, server)
