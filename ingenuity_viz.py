# ingenuity_viz.py
# Interactive Plotly charts for the Ingenuity flight log.
# Run:  python ingenuity_viz.py   → outputs/*.html (+ PNG if kaleido is installed)
import os

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ingenuity_data import build_dataframe

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {
    "phase_colors": {
        "Tech Demo":      "#FF6B6B",
        "Early Ops":      "#FFA07A",
        "Séítah":         "#4ECDC4",
        "Delta Approach": "#45B7D1",
        "Delta Science":  "#96CEB4",
    },
    "type_colors": {
        "tech_demo": "#FF6B6B",
        "ops":       "#FFA07A",
        "scout":     "#4ECDC4",
        "science":   "#96CEB4",
    },
}

PHASE_RANGES = {
    "Tech Demo":      (1, 5),
    "Early Ops":      (6, 14),
    "Séítah":         (15, 35),
    "Delta Approach": (36, 57),
    "Delta Science":  (58, 72),
}

TEMPLATE = "plotly_dark"
BG_COLOR = "#0a0a0f"
GRID_COLOR = "#2a2a3a"


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — MASTER FLIGHT TIMELINE
# Bubble chart: x=flight#, y=altitude, size=distance, color=duration
# ─────────────────────────────────────────────────────────────────────────────
def chart_flight_timeline(df):
    fig = go.Figure()

    for phase, (x0, x1) in PHASE_RANGES.items():
        color = COLORS["phase_colors"][phase]
        fig.add_vrect(
            x0=x0 - 0.5, x1=x1 + 0.5,
            fillcolor=color, opacity=0.06,
            layer="below", line_width=0,
            annotation_text=phase,
            annotation_position="top left",
            annotation_font=dict(size=9, color=color),
        )

    hover = df.apply(lambda r: (
        f"<b>Flight {r.flight_num}</b><br>"
        f"Date: {r.earth_date.strftime('%b %d, %Y')}<br>"
        f"Sol {r.sol}<br>"
        f"Duration: {r.duration_s}s<br>"
        f"Altitude: {r.max_alt_m}m<br>"
        f"Distance: {r.distance_m}m<br>"
        f"Phase: {r.mission_phase}"
        f"{'<br>⚠ ANOMALY' if r.anomaly_flag else ''}"
        f"{'<br>🏆 RECORD' if r.record_flag else ''}"
    ), axis=1)

    fig.add_trace(go.Scatter(
        x=df["flight_num"],
        y=df["max_alt_m"],
        mode="markers+lines",
        marker=dict(
            size=np.sqrt(df["distance_m"].clip(lower=1)) * 1.8 + 4,
            color=df["duration_s"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Duration (s)", x=1.02, thickness=12),
            line=dict(width=0.5, color="white"),
            opacity=0.85,
        ),
        line=dict(color="rgba(255,255,255,0.15)", width=1),
        text=hover,
        hovertemplate="%{text}<extra></extra>",
        name="Flights",
    ))

    for _, row in df[df["anomaly_flag"]].iterrows():
        fig.add_annotation(
            x=row.flight_num, y=row.max_alt_m,
            text=f"⚠ F{row.flight_num}<br>{'Final' if row.flight_num == 72 else 'Anomaly'}",
            showarrow=True, arrowhead=2, arrowcolor="#FF6B6B",
            font=dict(color="#FF6B6B", size=9),
            bgcolor="rgba(255,107,107,0.15)", bordercolor="#FF6B6B",
            ax=-40, ay=-30,
        )

    records = {
        4: "Speed record",
        9: "Distance record",
        15: "689m record",
        53: "14m altitude",
        70: "17m record",
    }
    for fnum, label in records.items():
        row = df[df.flight_num == fnum].iloc[0]
        fig.add_annotation(
            x=row.flight_num, y=row.max_alt_m, yshift=28,
            text=f"🏆 {label}", showarrow=False,
            font=dict(color="#FFD700", size=8),
        )

    fig.update_layout(
        title=dict(
            text="<b>Ingenuity Flight Log — All 72 Flights</b><br>"
                 "<sup>Bubble size = distance traveled | Color = duration | Height = max altitude</sup>",
            font=dict(size=18, color="white"), x=0.5,
        ),
        xaxis=dict(title="Flight Number", gridcolor=GRID_COLOR, dtick=5),
        yaxis=dict(title="Maximum Altitude (m)", gridcolor=GRID_COLOR),
        template=TEMPLATE, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=520, hovermode="closest", showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — SIX-PANEL METRIC DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def chart_six_panel(df):
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=(
            "Flight Duration (seconds)",
            "Maximum Altitude (meters)",
            "Distance Traveled (meters)",
            "Battery Usage (%)",
            "Images Captured per Flight",
            "Science Measurements per Flight",
        ),
        vertical_spacing=0.14, horizontal_spacing=0.08,
    )

    bar_kwargs = dict(x=df["flight_num"], marker_line_width=0, opacity=0.85)
    by_phase = [COLORS["phase_colors"][p] for p in df["mission_phase"]]
    by_type = [COLORS["type_colors"][t] for t in df["flight_type"]]

    fig.add_trace(go.Bar(
        **bar_kwargs, y=df["duration_s"], marker_color=by_phase, name="Duration",
        hovertemplate="Flight %{x}<br>Duration: %{y}s<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["flight_num"], y=df["duration_s"].rolling(5, min_periods=1).mean(),
        line=dict(color="white", width=1.5, dash="dot"), name="5-flight avg",
        hovertemplate="5-flight avg: %{y:.1f}s<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        **bar_kwargs, y=df["max_alt_m"], marker_color=by_phase, name="Altitude",
        hovertemplate="Flight %{x}<br>Altitude: %{y}m<extra></extra>",
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=df["flight_num"], y=df["max_alt_m"].cummax(),
        line=dict(color="#FFD700", width=2, shape="hv"), name="Altitude record",
        hovertemplate="Record at F%{x}: %{y}m<extra></extra>",
    ), row=1, col=2)

    fig.add_trace(go.Bar(
        **bar_kwargs, y=df["distance_m"], marker_color=by_phase, name="Distance",
        hovertemplate="Flight %{x}<br>Distance: %{y}m<extra></extra>",
    ), row=1, col=3)

    fig.add_trace(go.Bar(
        **bar_kwargs, y=df["battery_used"],
        marker_color=["#FF6B6B" if b > 13 else "#FFA07A" if b > 10 else "#4ECDC4"
                      for b in df["battery_used"]],
        name="Battery Used",
        hovertemplate="Flight %{x}<br>Battery used: %{y}%<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Bar(
        **bar_kwargs, y=df["images_taken"], marker_color=by_type, name="Images",
        hovertemplate="Flight %{x}<br>Images: %{y}<extra></extra>",
    ), row=2, col=2)

    fig.add_trace(go.Bar(
        **bar_kwargs, y=df["science_measurements"], marker_color=by_type, name="Science",
        hovertemplate="Flight %{x}<br>Measurements: %{y}<extra></extra>",
    ), row=2, col=3)

    # Anomaly markers on every panel
    for fnum in df.loc[df["anomaly_flag"], "flight_num"]:
        fig.add_vline(x=fnum, line_width=1, line_dash="dash",
                      line_color="#FF6B6B", opacity=0.5)

    fig.update_layout(
        title=dict(text="<b>Ingenuity Performance Metrics — All 72 Flights</b>",
                   font=dict(size=16, color="white"), x=0.5),
        template=TEMPLATE, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=700, showlegend=False, bargap=0.15,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, title_text="Flight Number", dtick=10)
    fig.update_yaxes(gridcolor=GRID_COLOR)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — CUMULATIVE PROGRESS AREA CHART
# ─────────────────────────────────────────────────────────────────────────────
def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def chart_cumulative(df):
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Cumulative Distance Flown (meters)",
            "Cumulative Flight Time (minutes)",
            "Cumulative Images Captured",
            "Cumulative Science Measurements",
        ),
    )

    cumulative_data = [
        (df["cumulative_distance_m"],      1, 1, "#4ECDC4", "meters"),
        (df["cumulative_duration_s"] / 60, 1, 2, "#45B7D1", "minutes"),
        (df["cumulative_images"],          2, 1, "#96CEB4", "images"),
        (df["cumulative_science"],         2, 2, "#FFD700", "measurements"),
    ]
    milestones = df[df["flight_num"] % 10 == 0]

    for series, row, col, color, unit in cumulative_data:
        fig.add_trace(go.Scatter(
            x=df["flight_num"], y=series,
            fill="tozeroy", fillcolor=_rgba(color, 0.2),
            line=dict(color=color, width=2), mode="lines",
            hovertemplate=f"After Flight %{{x}}<br>Total: %{{y:,.1f}} {unit}<extra></extra>",
        ), row=row, col=col)
        fig.add_trace(go.Scatter(
            x=milestones["flight_num"], y=series[milestones.index],
            mode="markers+text",
            marker=dict(color=color, size=8),
            text=[f"F{n}" for n in milestones["flight_num"]],
            textposition="top center", textfont=dict(size=8),
            hoverinfo="skip",
        ), row=row, col=col)

    fig.update_layout(
        title=dict(
            text="<b>Ingenuity: Cumulative Mission Totals</b><br>"
                 f"<sup>{df['distance_m'].sum()/1000:.2f} km | "
                 f"{df['duration_s'].sum()/60:.1f} min | "
                 f"{df['images_taken'].sum():,} images | "
                 f"{df['science_measurements'].sum():,} science measurements</sup>",
            font=dict(size=16, color="white"), x=0.5,
        ),
        template=TEMPLATE, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=620, showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, title_text="Flight Number")
    fig.update_yaxes(gridcolor=GRID_COLOR)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 — SCATTER MATRIX
# ─────────────────────────────────────────────────────────────────────────────
def chart_scatter_matrix(df):
    fig = px.scatter_matrix(
        df,
        dimensions=["duration_s", "max_alt_m", "distance_m",
                    "battery_used", "images_taken", "science_measurements"],
        color="mission_phase",
        color_discrete_map=COLORS["phase_colors"],
        category_orders={"mission_phase": list(PHASE_RANGES)},
        labels={
            "duration_s":           "Duration (s)",
            "max_alt_m":            "Altitude (m)",
            "distance_m":           "Distance (m)",
            "battery_used":         "Battery (%)",
            "images_taken":         "Images",
            "science_measurements": "Science Runs",
            "mission_phase":        "Mission Phase",
        },
        hover_data=["flight_num", "earth_date", "notes"],
        title="<b>Ingenuity Flight Metric Correlations</b>",
        template=TEMPLATE,
    )
    fig.update_traces(diagonal_visible=False, marker=dict(size=4, opacity=0.7))
    fig.update_layout(
        paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR, height=750,
        title=dict(x=0.5, font=dict(size=16, color="white")),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 5 — MISSION STATS SUMMARY (KPI cards, all computed from the data)
# ─────────────────────────────────────────────────────────────────────────────
def chart_kpi_summary(df):
    def at_max(col):
        return int(df.loc[df[col].idxmax(), "flight_num"])

    span_days = (df.earth_date.max() - df.earth_date.min()).days
    anomalies = ", ".join(f"F{n}" for n in df.loc[df.anomaly_flag, "flight_num"])

    kpis = [
        (f"{len(df)}",                              "Total Flights"),
        (f"{df.duration_s.sum()/60:.0f} min",       "Total Airtime"),
        (f"{df.distance_m.sum()/1000:.2f} km",      "Total Distance"),
        (f"{df.max_alt_m.max():g}m",                f"Max Altitude (F{at_max('max_alt_m')})"),
        (f"{df.duration_s.max():g}s",               f"Longest Flight (F{at_max('duration_s')})"),
        (f"{df.distance_m.max():g}m",               f"Farthest Flight (F{at_max('distance_m')})"),
        (f"{df.images_taken.sum():,}",              "Total Images"),
        (f"{df.science_measurements.sum():,}",      "Science Measurements"),
        (f"{df.battery_used.max()}%",               f"Peak Battery Use (F{at_max('battery_used')})"),
        (f"{span_days:,} days",                     "First to Last Flight"),
        (df.earth_date.max().strftime("%b %d, %Y"), "Final Flight Date"),
        (anomalies,                                 "Anomaly Flights"),
    ]

    fig = go.Figure()
    cols, rows = 4, 3
    for i, (value, label) in enumerate(kpis):
        r, c = divmod(i, cols)
        x_pos = c / cols + 1 / (2 * cols)
        y_pos = 1 - r / rows - 1 / (2 * rows)
        fig.add_shape(
            type="rect", xref="paper", yref="paper",
            x0=c / cols + 0.01, y0=1 - (r + 1) / rows + 0.02,
            x1=(c + 1) / cols - 0.01, y1=1 - r / rows - 0.02,
            fillcolor="rgba(255,255,255,0.05)",
            line=dict(color="rgba(255,255,255,0.2)", width=1),
        )
        fig.add_annotation(x=x_pos, y=y_pos + 0.05, text=f"<b>{value}</b>",
                           font=dict(size=22, color="#4ECDC4"),
                           showarrow=False, xref="paper", yref="paper")
        fig.add_annotation(x=x_pos, y=y_pos - 0.08, text=label,
                           font=dict(size=10, color="#aaaaaa"),
                           showarrow=False, xref="paper", yref="paper")

    fig.update_layout(
        title=dict(
            text="<b>🚁 Ingenuity Helicopter — Mission Summary</b><br>"
                 "<sup>First powered aircraft to fly on another planet | Mars 2020 Mission</sup>",
            font=dict(size=18, color="white"), x=0.5,
        ),
        paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR, height=440,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        template=TEMPLATE, margin=dict(t=90, b=20, l=20, r=20),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 6 — FLIGHT ENVELOPE (altitude vs average speed, with convex hull)
# ─────────────────────────────────────────────────────────────────────────────
def _convex_hull(points):
    """Andrew's monotone chain; returns hull vertices in order."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and cross(out[-2], out[-1], p) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]

    return half(pts) + half(reversed(pts))


def chart_flight_envelope(df):
    fig = go.Figure()

    hull = _convex_hull(list(zip(df["max_alt_m"], df["speed_ms"])))
    hull.append(hull[0])
    fig.add_trace(go.Scatter(
        x=[p[0] for p in hull], y=[p[1] for p in hull],
        fill="toself", fillcolor="rgba(255,255,255,0.04)",
        line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
        name="Flight envelope", hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=df["max_alt_m"], y=df["speed_ms"],
        mode="markers+text",
        marker=dict(
            size=14, color=df["flight_num"], colorscale="Plasma",
            showscale=True, colorbar=dict(title="Flight #", thickness=12),
            opacity=0.85, line=dict(width=0.5, color="white"),
        ),
        text=df["flight_num"].astype(str),
        textfont=dict(size=7, color="white"),
        textposition="middle center",
        hovertemplate="<b>Flight %{text}</b><br>Max altitude: %{x}m<br>"
                      "Avg speed: %{y:.2f} m/s<extra></extra>",
        name="Flight",
    ))

    fig.update_layout(
        title=dict(
            text="<b>Flight Envelope: Altitude vs Speed</b><br>"
                 "<sup>Dotted outline = convex hull of all 72 flights</sup>",
            font=dict(size=15, color="white"), x=0.5,
        ),
        xaxis=dict(title="Max Altitude (m)", gridcolor=GRID_COLOR),
        yaxis=dict(title="Avg Speed (m/s)", gridcolor=GRID_COLOR),
        template=TEMPLATE, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=480, showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT ALL CHARTS
# ─────────────────────────────────────────────────────────────────────────────
def export_all(df, png=True):
    os.makedirs("outputs", exist_ok=True)

    charts = {
        "01_flight_timeline":   chart_flight_timeline(df),
        "02_six_panel_metrics": chart_six_panel(df),
        "03_cumulative_totals": chart_cumulative(df),
        "04_scatter_matrix":    chart_scatter_matrix(df),
        "05_kpi_summary":       chart_kpi_summary(df),
        "06_flight_envelope":   chart_flight_envelope(df),
    }

    for name, fig in charts.items():
        fig.write_html(f"outputs/{name}.html", include_plotlyjs="cdn")
        print(f"  ✓ {name}.html")

    if png:
        try:
            import kaleido  # noqa: F401
        except ImportError:
            print("  (skipping PNG export — `pip install kaleido` to enable)")
        else:
            for name, fig in charts.items():
                fig.write_image(f"outputs/{name}.png", width=1400, height=700, scale=2)
                print(f"  ✓ {name}.png")

    print(f"\n✅ {len(charts)} charts exported to outputs/")
    return charts


if __name__ == "__main__":
    export_all(build_dataframe())
