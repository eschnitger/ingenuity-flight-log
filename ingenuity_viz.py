# ingenuity_viz.py
# Interactive Plotly charts for the Ingenuity flight log (NASA data).
# Run:  python ingenuity_viz.py   → outputs/*.html (+ PNG if kaleido is installed)
import os

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ingenuity_data import build_dataframe

PHASE_COLORS = {
    "Tech Demo": "#FF6B6B",
    "Ops 2021":  "#FFA07A",
    "Ops 2022":  "#4ECDC4",
    "Ops 2023":  "#A78BFA",
    "Ops 2024":  "#F472B6",
}

# column → (panel title, unit suffix)
METRICS = {
    "duration_s":     ("Flight duration", "s"),
    "max_alt_m":      ("Maximum altitude", "m"),
    "distance_m":     ("Distance flown", "m"),
    "max_speed_ms":   ("Top groundspeed", "m/s"),
    "avg_speed_ms":   ("Average speed (distance ÷ duration)", "m/s"),
    "landing_elev_m": ("Landing-site elevation", "m"),
}

TEMPLATE = "plotly_dark"
BG_COLOR = "#0a0a0f"
GRID_COLOR = "#2a2a3a"
SOURCE_NOTE = "Data: NASA/JPL-Caltech Mars 2020 map layers"


def phase_ranges(df):
    """Phase → (first flight, last flight), in mission order."""
    g = df.groupby("mission_phase", sort=False)["flight_num"].agg(["min", "max"])
    return {p: (int(r["min"]), int(r["max"])) for p, r in g.iterrows()}


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def flight_hover(df):
    return df.apply(lambda r: (
        f"<b>Flight {r.flight_num}</b><br>"
        f"{r.earth_date:%b %d, %Y} | Sol {r.sol}<br>"
        f"Duration: {r.duration_s:g} s<br>"
        f"Max altitude: {r.max_alt_m:g} m<br>"
        f"Distance: {r.distance_m:g} m<br>"
        f"Top speed: {r.max_speed_ms:g} m/s<br>"
        f"{r.route}"
        + (f"<br>🏆 New {r.records} record" if r.records else "")
        + ("<br>Final flight" if r.final_flag else "")
    ), axis=1)


def _title(text, sub):
    return dict(text=f"<b>{text}</b><br><sup>{sub}</sup>",
                font=dict(size=17, color="white"), x=0.5)


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — FLIGHT TIMELINE (x = flight, y = altitude, size = distance, color = duration)
# ─────────────────────────────────────────────────────────────────────────────
def chart_flight_timeline(df):
    fig = go.Figure()

    for phase, (x0, x1) in phase_ranges(df).items():
        color = PHASE_COLORS[phase]
        fig.add_vrect(
            x0=x0 - 0.5, x1=x1 + 0.5, fillcolor=color, opacity=0.06,
            layer="below", line_width=0,
            annotation_text=phase, annotation_position="top left",
            annotation_font=dict(size=9, color=color),
        )

    fig.add_trace(go.Scatter(
        x=df["flight_num"], y=df["max_alt_m"], mode="markers+lines",
        marker=dict(
            size=np.sqrt(df["distance_m"].clip(lower=1)) * 1.6 + 4,
            color=df["duration_s"], colorscale="Viridis", showscale=True,
            colorbar=dict(title="Duration (s)", x=1.02, thickness=12),
            line=dict(width=0.5, color="white"), opacity=0.85,
        ),
        line=dict(color="rgba(255,255,255,0.15)", width=1),
        text=flight_hover(df), hovertemplate="%{text}<extra></extra>",
    ))

    # Label each new altitude record and the final flight
    alt_records = df[df["records"].str.contains("altitude")]
    for _, row in alt_records.iterrows():
        fig.add_annotation(
            x=row.flight_num, y=row.max_alt_m, yshift=24,
            text=f"F{row.flight_num}: {row.max_alt_m:g} m", showarrow=False,
            font=dict(color="#FFD700", size=9),
        )
    final = df[df["final_flag"]].iloc[0]
    fig.add_annotation(
        x=final.flight_num, y=final.max_alt_m, text="Final flight",
        showarrow=True, arrowhead=2, arrowcolor="#FF6B6B", ax=-10, ay=40,
        font=dict(color="#FF6B6B", size=9),
        bgcolor="rgba(255,107,107,0.15)", bordercolor="#FF6B6B",
    )

    fig.update_layout(
        title=_title("Ingenuity Flight Log — All 72 Flights",
                     "Bubble size = distance flown | Color = duration | "
                     "Gold labels = new altitude records"),
        xaxis=dict(title="Flight number", gridcolor=GRID_COLOR, dtick=5),
        yaxis=dict(title="Maximum altitude (m)", gridcolor=GRID_COLOR,
                   range=[0, df["max_alt_m"].max() * 1.2]),
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
        subplot_titles=[f"{t} ({u})" for t, u in METRICS.values()],
        vertical_spacing=0.14, horizontal_spacing=0.07,
    )
    by_phase = [PHASE_COLORS[p] for p in df["mission_phase"]]

    for i, (col, (title, unit)) in enumerate(METRICS.items()):
        r, c = divmod(i, 3)
        if col == "landing_elev_m":
            # Elevation is a position, not an amount: a line, not bars from zero
            fig.add_trace(go.Scatter(
                x=df["flight_num"], y=df[col], mode="lines+markers",
                line=dict(color="#D4A96A", width=2),
                marker=dict(color=by_phase, size=5),
                hovertemplate="Flight %{x}<br>%{y:,.1f} m<extra></extra>",
            ), row=r + 1, col=c + 1)
            continue
        fig.add_trace(go.Bar(
            x=df["flight_num"], y=df[col], marker_color=by_phase,
            marker_line_width=0, opacity=0.9,
            hovertemplate=f"Flight %{{x}}<br>{title}: %{{y:g}} {unit}<extra></extra>",
        ), row=r + 1, col=c + 1)
        if col in ("duration_s", "distance_m"):
            fig.add_trace(go.Scatter(
                x=df["flight_num"], y=df[col].rolling(5, min_periods=1).mean(),
                line=dict(color="white", width=1.5, dash="dot"),
                hovertemplate="5-flight avg: %{y:.1f}<extra></extra>",
            ), row=r + 1, col=c + 1)
        if col in ("max_alt_m", "max_speed_ms"):
            fig.add_trace(go.Scatter(
                x=df["flight_num"], y=df[col].cummax(),
                line=dict(color="#FFD700", width=1.5, shape="hv"),
                hovertemplate="Record so far: %{y:g}<extra></extra>",
            ), row=r + 1, col=c + 1)

    fig.update_layout(
        title=_title("Ingenuity Performance Metrics — All 72 Flights",
                     "Bars colored by phase | dotted white = 5-flight average | "
                     "gold = running record"),
        template=TEMPLATE, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=720, showlegend=False, bargap=0.15,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, title_text="Flight number", dtick=10)
    fig.update_yaxes(gridcolor=GRID_COLOR)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — CUMULATIVE DISTANCE AND AIRTIME
# ─────────────────────────────────────────────────────────────────────────────
def chart_cumulative(df):
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Cumulative distance flown (km)", "Cumulative airtime (minutes)"),
    )
    series = [
        (df["cumulative_distance_m"] / 1000, 1, "#4ECDC4", "km"),
        (df["cumulative_duration_s"] / 60,   2, "#45B7D1", "min"),
    ]
    milestones = df[(df["flight_num"] % 10 == 0) | df["final_flag"]]

    for values, col, color, unit in series:
        fig.add_trace(go.Scatter(
            x=df["flight_num"], y=values, fill="tozeroy",
            fillcolor=_rgba(color, 0.2), line=dict(color=color, width=2),
            mode="lines",
            hovertemplate=f"After flight %{{x}}<br>%{{y:.2f}} {unit}<extra></extra>",
        ), row=1, col=col)
        fig.add_trace(go.Scatter(
            x=milestones["flight_num"], y=values[milestones.index],
            mode="markers+text", marker=dict(color=color, size=8),
            text=[f"{v:.1f}" for v in values[milestones.index]],
            textposition="top left", textfont=dict(size=9, color=color),
            hoverinfo="skip",
        ), row=1, col=col)

    fig.update_layout(
        title=_title("Ingenuity: Cumulative Mission Totals",
                     f"{df['distance_m'].sum()/1000:.2f} km and "
                     f"{df['duration_s'].sum()/60:.1f} minutes over {len(df)} flights"),
        template=TEMPLATE, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=480, showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, title_text="Flight number")
    fig.update_yaxes(gridcolor=GRID_COLOR)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 — SCATTER MATRIX
# ─────────────────────────────────────────────────────────────────────────────
def chart_scatter_matrix(df):
    fig = px.scatter_matrix(
        df,
        dimensions=["duration_s", "max_alt_m", "distance_m", "max_speed_ms"],
        color="mission_phase",
        color_discrete_map=PHASE_COLORS,
        category_orders={"mission_phase": list(PHASE_COLORS)},
        labels={
            "duration_s":    "Duration (s)",
            "max_alt_m":     "Altitude (m)",
            "distance_m":    "Distance (m)",
            "max_speed_ms":  "Top speed (m/s)",
            "mission_phase": "Phase",
        },
        hover_data=["flight_num", "earth_date", "route"],
        title="<b>Ingenuity Flight Metric Relationships</b>",
        template=TEMPLATE,
    )
    fig.update_traces(diagonal_visible=False, marker=dict(size=5, opacity=0.75))
    fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR, height=720,
                      title=dict(x=0.5, font=dict(size=16, color="white")))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 5 — MISSION SUMMARY (KPI cards, all computed from the data)
# ─────────────────────────────────────────────────────────────────────────────
def chart_kpi_summary(df):
    def at_max(col):
        return int(df.loc[df[col].idxmax(), "flight_num"])

    kpis = [
        (f"{len(df)}",                                 "Flights"),
        (f"{df.duration_s.sum()/60:.1f} min",          "Total airtime"),
        (f"{df.distance_m.sum()/1000:.2f} km",         "Total distance"),
        (f"{df.to_airfield.nunique()}",                "Airfields used"),
        (f"{df.max_alt_m.max():g} m",                  f"Highest (F{at_max('max_alt_m')})"),
        (f"{df.duration_s.max():g} s",                 f"Longest (F{at_max('duration_s')})"),
        (f"{df.distance_m.max():g} m",                 f"Farthest (F{at_max('distance_m')})"),
        (f"{df.max_speed_ms.max():g} m/s",             f"Fastest (F{at_max('max_speed_ms')})"),
        (f"{df.earth_date.min():%b %d, %Y}",           "First flight"),
        (f"{df.earth_date.max():%b %d, %Y}",           "Final flight"),
        (f"{df.sol.max() - df.sol.min():,} sols",      "First to last flight"),
        (f"{df.landing_elev_m.iloc[-1] - df.landing_elev_m.iloc[0]:+.0f} m",
                                                       "Net elevation change"),
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
        title=_title("Ingenuity Mars Helicopter — Mission Summary", SOURCE_NOTE),
        paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR, height=440,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        template=TEMPLATE, margin=dict(t=90, b=20, l=20, r=20),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 6 — FLIGHT ENVELOPE (altitude vs top groundspeed, with convex hull)
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

    hull = _convex_hull(list(zip(df["max_alt_m"], df["max_speed_ms"])))
    hull.append(hull[0])
    fig.add_trace(go.Scatter(
        x=[p[0] for p in hull], y=[p[1] for p in hull],
        fill="toself", fillcolor="rgba(255,255,255,0.04)",
        line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
        hoverinfo="skip",
    ))

    # Many flights share the same altitude/speed pair; jitter slightly so they separate
    rng = np.random.default_rng(7)
    jx = rng.uniform(-0.3, 0.3, len(df))
    jy = rng.uniform(-0.12, 0.12, len(df))
    fig.add_trace(go.Scatter(
        x=df["max_alt_m"] + jx, y=df["max_speed_ms"] + jy,
        mode="markers+text",
        marker=dict(size=15, color=df["flight_num"], colorscale="Plasma",
                    showscale=True, colorbar=dict(title="Flight #", thickness=12),
                    opacity=0.8, line=dict(width=0.5, color="white")),
        text=df["flight_num"].astype(str),
        textfont=dict(size=7, color="white"), textposition="middle center",
        customdata=np.column_stack([df["max_alt_m"], df["max_speed_ms"]]),
        hovertemplate="<b>Flight %{text}</b><br>Max altitude: %{customdata[0]:g} m<br>"
                      "Top speed: %{customdata[1]:g} m/s<extra></extra>",
    ))

    fig.update_layout(
        title=_title("Flight Envelope: Altitude vs Top Groundspeed",
                     "Dotted outline = convex hull of all flights | "
                     "points jittered slightly to separate overlaps"),
        xaxis=dict(title="Max altitude (m)", gridcolor=GRID_COLOR),
        yaxis=dict(title="Top groundspeed (m/s)", gridcolor=GRID_COLOR),
        template=TEMPLATE, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=520, showlegend=False,
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
