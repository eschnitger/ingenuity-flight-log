# ingenuity_map.py
# Flight-path maps (Plotly interactive + Matplotlib static).
# Run:  python ingenuity_map.py              → synthetic terrain basemap
#       python ingenuity_map.py --download   → try the USGS WMS basemap first
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

from ingenuity_data import build_dataframe
from ingenuity_positions import (
    FLIGHT_PATHS,
    build_endpoint_dataframe,
    build_location_dataframe,
    build_path_dataframe,
)

BG_COLOR = "#0a0a0f"
GRID_COLOR = "#1e1e2e"

PHASE_COLORS = {
    "Tech Demo":      "#FF6B6B",
    "Early Ops":      "#FFA07A",
    "Séítah":         "#4ECDC4",
    "Delta Approach": "#45B7D1",
    "Delta Science":  "#96CEB4",
}
PHASE_ORDER = list(PHASE_COLORS)

# Shared map window (ENU meters) — also used for the Tableau background image
X_MIN, X_MAX, Y_MIN, Y_MAX = -400, 2800, -3600, 500


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: TERRAIN BASEMAP
# ─────────────────────────────────────────────────────────────────────────────
def synthetic_terrain(width, height, seed=42):
    """Mars-coloured multi-octave value noise as an RGB uint8 array."""
    rng = np.random.default_rng(seed)
    terrain = np.zeros((height, width))
    for scale in (4, 8, 16, 32, 64, 128):
        small = rng.random((height // scale + 2, width // scale + 2))
        img = Image.fromarray((small * 255).astype(np.uint8))
        up = np.asarray(img.resize((width, height), Image.BICUBIC), dtype=float) / 255
        terrain += up * scale          # big features dominate, fine grain on top
    terrain = (terrain - terrain.min()) / (terrain.max() - terrain.min())

    rgb = np.stack([
        0.45 + 0.35 * terrain,
        0.22 + 0.18 * terrain,
        0.08 + 0.10 * terrain,
    ], axis=2)
    return (rgb * 255).clip(0, 255).astype(np.uint8)


def get_mars_basemap(save_path="data/mars_basemap.png", download=False,
                     width=1600, height=2050):
    """Returns a basemap path. Downloads from USGS only when asked; otherwise
    (or on any failure) writes a synthetic terrain texture."""
    if os.path.exists(save_path):
        print(f"✓ Using cached basemap: {save_path}")
        return save_path
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    if download:
        import requests
        url = (
            "https://planetarymaps.usgs.gov/cgi-bin/mapserv"
            "?map=/maps/mars/mars_simp_cyl.map"
            "&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
            "&LAYERS=MDIM21_color"
            "&BBOX=77.42,18.38,77.50,18.46"
            f"&WIDTH={width}&HEIGHT={height}"
            "&SRS=EPSG:4326&FORMAT=image/png&STYLES="
        )
        try:
            r = requests.get(url, timeout=30)
            if r.ok and r.headers.get("content-type", "").startswith("image/"):
                with open(save_path, "wb") as f:
                    f.write(r.content)
                print(f"✓ Downloaded basemap → {save_path}")
                return save_path
            print(f"⚠ WMS returned {r.status_code} ({r.headers.get('content-type')})")
        except Exception as e:  # network errors, timeouts
            print(f"⚠ WMS download failed: {e}")

    Image.fromarray(synthetic_terrain(width, height)).save(save_path)
    print(f"✓ Synthetic basemap → {save_path}")
    return save_path


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1: PLOTLY INTERACTIVE FLIGHT PATH MAP
# ─────────────────────────────────────────────────────────────────────────────
def chart_interactive_map(flight_df, loc_df, endpoint_df):
    fig = go.Figure()

    airfields = loc_df[loc_df["is_airfield"]]
    features = loc_df[~loc_df["is_airfield"]]

    fig.add_trace(go.Scatter(
        x=airfields["east_m"], y=airfields["north_m"],
        mode="markers+text",
        marker=dict(symbol="triangle-up", size=10, color="#FFD700",
                    line=dict(width=1, color="white"), opacity=0.9),
        text=airfields["location"].str.replace("Airfield ", "AF-")
                                  .str.replace("Wright Brothers Field", ""),
        textposition="top right", textfont=dict(size=8, color="#FFD700"),
        name="Airfields",
        customdata=airfields["location"],
        hovertemplate="<b>%{customdata}</b><br>East: %{x:.0f}m | North: %{y:.0f}m"
                      "<extra>Airfield</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=features["east_m"], y=features["north_m"],
        mode="markers+text",
        marker=dict(symbol="diamond", size=8, color="#D4A96A",
                    line=dict(width=1, color="white"), opacity=0.7),
        text=features["location"],
        textposition="top right", textfont=dict(size=9, color="#D4A96A"),
        name="Features",
        hovertemplate="<b>%{text}</b><br>East: %{x:.0f}m | North: %{y:.0f}m"
                      "<extra>Geographic Feature</extra>",
    ))

    # One hoverable trace per flight; clicking a phase in the legend toggles its flights
    for _, flight in flight_df.iterrows():
        fn = int(flight["flight_num"])
        phase = flight["mission_phase"]
        color = PHASE_COLORS[phase]
        waypoints = FLIGHT_PATHS[fn]
        xs = [p[0] for p in waypoints]
        ys = [p[1] for p in waypoints]

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line=dict(color=color, width=2), opacity=0.7,
            name=f"F{fn}", legendgroup=phase, showlegend=False,
            hovertemplate=(
                f"<b>Flight {fn}</b><br>"
                f"{flight['earth_date']:%b %d, %Y} | Sol {flight['sol']}<br>"
                f"Phase: {phase}<br>"
                f"Duration: {flight['duration_s']}s<br>"
                f"Distance: {flight['distance_m']}m<br>"
                f"Altitude: {flight['max_alt_m']}m<br>"
                f"Battery used: {flight['battery_used']}%<br>"
                f"Images: {flight['images_taken']}"
                "<extra></extra>"
            ),
        ))

        # Arrowhead at the landing point (skip pure hovers)
        dx, dy = xs[-1] - xs[-2], ys[-1] - ys[-2]
        mag = np.hypot(dx, dy)
        if mag > 0:
            fig.add_annotation(
                x=xs[-1], y=ys[-1],
                ax=xs[-1] - dx / mag * 15, ay=ys[-1] - dy / mag * 15,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=0.8,
                arrowwidth=1.5, arrowcolor=color,
            )

    fig.add_trace(go.Scatter(
        x=endpoint_df["takeoff_east"], y=endpoint_df["takeoff_north"],
        mode="markers",
        marker=dict(symbol="circle", size=5, color="lime",
                    line=dict(width=0.5, color="white"), opacity=0.7),
        name="Takeoff", customdata=endpoint_df["flight_num"],
        hovertemplate="Takeoff F%{customdata}<br>East: %{x:.0f}m | North: %{y:.0f}m"
                      "<extra>Takeoff</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=endpoint_df["landing_east"], y=endpoint_df["landing_north"],
        mode="markers",
        marker=dict(symbol="x", size=5, color="#FF6B6B", opacity=0.7),
        name="Landing", customdata=endpoint_df["flight_num"],
        hovertemplate="Landing F%{customdata}<br>East: %{x:.0f}m | North: %{y:.0f}m"
                      "<extra>Landing</extra>",
    ))

    fig.add_annotation(
        x=0, y=0, text="★ Wright Brothers Field<br>(Launch Site)",
        showarrow=True, arrowhead=2, ax=110, ay=-40,
        font=dict(color="#FFD700", size=9),
        bgcolor="rgba(255,215,0,0.1)", bordercolor="#FFD700", arrowcolor="#FFD700",
    )
    last = FLIGHT_PATHS[72][-1]
    final_date = flight_df.loc[flight_df.flight_num == 72, "earth_date"].iloc[0]
    fig.add_annotation(
        x=last[0], y=last[1],
        text=f"⚠ Final Landing<br>Flight 72 ({final_date:%b %d, %Y})",
        showarrow=True, arrowhead=2, ax=60, ay=40,
        font=dict(color="#FF6B6B", size=9),
        bgcolor="rgba(255,107,107,0.1)", bordercolor="#FF6B6B", arrowcolor="#FF6B6B",
    )

    # Phase legend entries
    for phase, color in PHASE_COLORS.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines",
            line=dict(color=color, width=3),
            name=phase, legendgroup=phase, showlegend=True,
        ))

    fig.add_annotation(x=2650, y=300, text="N ↑", showarrow=False,
                       font=dict(color="white", size=13),
                       bgcolor="rgba(255,255,255,0.1)")
    fig.add_shape(type="line", x0=2200, y0=-3450, x1=2700, y1=-3450,
                  line=dict(color="white", width=2))
    fig.add_annotation(x=2450, y=-3390, text="500 m", showarrow=False,
                       font=dict(color="white", size=9))

    fig.update_layout(
        title=dict(
            text="<b>Ingenuity Flight Paths — Jezero Crater, Mars</b><br>"
                 "<sup>72 flights | April 2021 – January 2024 | "
                 "18.44°N 77.45°E | Coordinate origin: Wright Brothers Field</sup>",
            font=dict(size=16, color="white"), x=0.5,
        ),
        xaxis=dict(title="East (meters from landing site)", gridcolor=GRID_COLOR,
                   zerolinecolor="rgba(255,255,255,0.2)", range=[X_MIN, X_MAX]),
        yaxis=dict(title="North (meters from landing site)", gridcolor=GRID_COLOR,
                   zerolinecolor="rgba(255,255,255,0.2)",
                   scaleanchor="x", scaleratio=1, range=[Y_MIN, Y_MAX]),
        template="plotly_dark", plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=900, hovermode="closest",
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="rgba(255,255,255,0.2)",
                    borderwidth=1, font=dict(color="white"),
                    title=dict(text="Mission Phase", font=dict(color="#aaaaaa"))),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2: MATPLOTLIB STATIC MAP (high-resolution export)
# ─────────────────────────────────────────────────────────────────────────────
def chart_static_map(flight_df, loc_df, endpoint_df, basemap_path=None,
                     out="outputs/ingenuity_flight_map.png"):
    fig, (ax_map, ax_info) = plt.subplots(
        1, 2, figsize=(18, 15), facecolor=BG_COLOR,
        gridspec_kw={"width_ratios": [2.5, 1]},
    )
    for ax in (ax_map, ax_info):
        ax.set_facecolor(BG_COLOR)

    if basemap_path and os.path.exists(basemap_path):
        ax_map.imshow(plt.imread(basemap_path),
                      extent=[X_MIN, X_MAX, Y_MIN, Y_MAX],
                      aspect="equal", alpha=0.35, origin="upper", zorder=0)

    flights = flight_df.set_index("flight_num")
    for fn, waypoints in FLIGHT_PATHS.items():
        row = flights.loc[fn]
        color = PHASE_COLORS[row["mission_phase"]]
        xs = [p[0] for p in waypoints]
        ys = [p[1] for p in waypoints]

        # Later flights drawn slightly bolder
        ax_map.plot(xs, ys, color=color,
                    linewidth=0.8 + (fn / 72) * 0.8,
                    alpha=0.4 + (fn / 72) * 0.5, zorder=2,
                    solid_capstyle="round", solid_joinstyle="round")

        if (xs[-1], ys[-1]) != (xs[-2], ys[-2]):
            ax_map.annotate(
                "", xy=(xs[-1], ys[-1]), xytext=(xs[-2], ys[-2]),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=0.8,
                                mutation_scale=6),
                zorder=3,
            )
        if row["anomaly_flag"]:
            ax_map.scatter(xs[-1], ys[-1], s=90, c="#FF6B6B", marker="X",
                           zorder=7, edgecolors="white", linewidths=0.5)

    ax_map.scatter(endpoint_df["takeoff_east"], endpoint_df["takeoff_north"],
                   s=12, c="lime", zorder=4, alpha=0.6, linewidths=0)

    stroke = [pe.withStroke(linewidth=2, foreground=BG_COLOR)]
    for _, loc in loc_df.iterrows():
        if loc["location"] == "Wright Brothers Field":
            continue
        if loc["is_airfield"]:
            ax_map.scatter(loc["east_m"], loc["north_m"], s=25, marker="^",
                           c="#FFD700", zorder=5, edgecolors="white",
                           linewidths=0.3, alpha=0.8)
            ax_map.annotate(loc["location"].replace("Airfield ", "AF-"),
                            (loc["east_m"], loc["north_m"]),
                            textcoords="offset points", xytext=(-16, -3),
                            fontsize=6, color="#FFD700", zorder=6,
                            path_effects=stroke)
        else:
            ax_map.annotate(loc["location"], (loc["east_m"], loc["north_m"]),
                            textcoords="offset points", xytext=(6, 6),
                            fontsize=7.5, color="#D4A96A", fontweight="bold",
                            zorder=6, path_effects=stroke)

    ax_map.scatter(0, 0, s=220, c="#FFD700", marker="*", zorder=8,
                   edgecolors="white", linewidths=0.5)
    ax_map.annotate("Wright Brothers\nField (Origin)", (0, 0),
                    textcoords="offset points", xytext=(10, 10), fontsize=8,
                    color="#FFD700", fontweight="bold", path_effects=stroke, zorder=9)

    final = FLIGHT_PATHS[72][-1]
    ax_map.annotate("Final Landing\nFlight 72", final,
                    textcoords="offset points", xytext=(14, -34), fontsize=8,
                    color="#FF6B6B",
                    arrowprops=dict(arrowstyle="->", color="#FF6B6B", lw=0.8),
                    path_effects=stroke, zorder=9)

    handles = [mpatches.Patch(facecolor=PHASE_COLORS[p], label=p, alpha=0.8)
               for p in PHASE_ORDER]
    handles += [
        plt.Line2D([0], [0], marker="*", color="none", markerfacecolor="#FFD700",
                   markersize=11, label="Launch Site"),
        plt.Line2D([0], [0], marker="^", color="none", markerfacecolor="#FFD700",
                   markersize=7, label="Airfield"),
        plt.Line2D([0], [0], marker="X", color="none", markerfacecolor="#FF6B6B",
                   markersize=8, label="Anomaly Landing"),
    ]
    ax_map.legend(handles=handles, loc="lower left", facecolor="#111111",
                  edgecolor=(1, 1, 1, 0.2), fontsize=8, labelcolor="white")

    # North arrow + scale bar
    ax_map.annotate("", xy=(2600, 380), xytext=(2600, 80),
                    arrowprops=dict(arrowstyle="-|>", color="white", lw=1.5))
    ax_map.text(2600, 400, "N", color="white", ha="center", fontsize=10)
    ax_map.plot([2200, 2700], [-3500, -3500], "w-", lw=2)
    ax_map.plot([2200, 2200], [-3500, -3470], "w-", lw=1.5)
    ax_map.plot([2700, 2700], [-3500, -3470], "w-", lw=1.5)
    ax_map.text(2450, -3450, "500 m", color="white", ha="center", fontsize=8)

    ax_map.set_xlim(X_MIN, X_MAX)
    ax_map.set_ylim(Y_MIN, Y_MAX)
    ax_map.set_aspect("equal")
    ax_map.set_xlabel("East from Wright Brothers Field (m)", color="white", fontsize=9)
    ax_map.set_ylabel("North from Wright Brothers Field (m)", color="white", fontsize=9)
    ax_map.tick_params(colors="white")
    ax_map.set_title("All 72 Flight Paths  |  Jezero Crater, Mars  |  18.44°N 77.45°E",
                     color="white", fontsize=12, pad=10)
    for spine in ax_map.spines.values():
        spine.set_edgecolor("#333333")

    # ── Right panel: duration bar per flight ──
    max_dur = flight_df["duration_s"].max()
    ax_info.set_xlim(0, 10)
    ax_info.set_ylim(-2, 73)
    ax_info.axis("off")
    ax_info.set_title("Flight Duration", color="white", fontsize=11, pad=8)
    for _, row in flight_df.iterrows():
        fn = int(row["flight_num"])
        color = PHASE_COLORS[row["mission_phase"]]
        y = 72 - fn
        width = row["duration_s"] / max_dur * 6
        ax_info.barh(y, width, height=0.65, left=1.5, color=color, alpha=0.75)
        ax_info.text(0.2, y, f"F{fn:02d}", va="center", ha="left",
                     color=color, fontsize=6)
        ax_info.text(1.6 + width, y, f"{row['duration_s']:g}s", va="center",
                     ha="left", color="#aaaaaa", fontsize=5.5)
        if row["anomaly_flag"]:
            ax_info.text(9.6, y, "X", va="center", ha="right",
                         color="#FF6B6B", fontsize=7, fontweight="bold")
    ax_info.text(5, -1.5, "bar length = duration  |  X = anomaly",
                 ha="center", color="#aaaaaa", fontsize=7)

    fig.suptitle("INGENUITY HELICOPTER — JEZERO CRATER FLIGHT MAP",
                 color="white", fontsize=16, fontweight="bold", y=0.985)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  ✓ {out}")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3: SMALL MULTIPLES — ONE MAP PER MISSION PHASE
# ─────────────────────────────────────────────────────────────────────────────
def chart_phase_maps(flight_df, out="outputs/ingenuity_phase_maps.png"):
    fig, axes = plt.subplots(1, 5, figsize=(25, 8), facecolor=BG_COLOR)

    for ax, phase in zip(axes, PHASE_ORDER):
        ax.set_facecolor(BG_COLOR)
        ax.set_aspect("equal")
        phase_flights = flight_df[flight_df["mission_phase"] == phase]
        color = PHASE_COLORS[phase]

        for waypoints in FLIGHT_PATHS.values():       # grey context
            ax.plot([p[0] for p in waypoints], [p[1] for p in waypoints],
                    color="#444455", linewidth=0.5, alpha=0.5, zorder=1)

        for fn in phase_flights["flight_num"]:
            waypoints = FLIGHT_PATHS[int(fn)]
            xs = [p[0] for p in waypoints]
            ys = [p[1] for p in waypoints]
            ax.plot(xs, ys, color=color, linewidth=2, alpha=0.9, zorder=3,
                    solid_capstyle="round")
            ax.scatter(xs[0], ys[0], s=20, c="lime", zorder=4, linewidths=0)
            ax.scatter(xs[-1], ys[-1], s=20, c="#FF6B6B", zorder=5, linewidths=0)

        ax.scatter(0, 0, s=90, c="#FFD700", marker="*", zorder=6)
        ax.set_xlim(X_MIN, X_MAX)
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.set_title(
            f"{phase}\n"
            f"F{phase_flights.flight_num.min()}–F{phase_flights.flight_num.max()}  "
            f"({len(phase_flights)} flights)\n"
            f"{phase_flights['distance_m'].sum():,.0f} m total",
            color=color, fontsize=10, pad=6,
        )
        ax.tick_params(colors="#666666", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#222222")

    fig.suptitle("Ingenuity Flight Paths by Mission Phase",
                 color="white", fontsize=15, fontweight="bold")
    plt.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  ✓ {out}")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4: ANIMATED FLIGHT PATH (Plotly) — flights appear one by one
# Trace layout is fixed (72 path traces + head marker + origin) so every frame
# can address every trace; future flights are simply empty.
# ─────────────────────────────────────────────────────────────────────────────
def chart_animated_map(flight_df):
    flights = flight_df.set_index("flight_num")
    n = len(FLIGHT_PATHS)

    def path_trace(fn, current_fn):
        color = PHASE_COLORS[flights.loc[fn, "mission_phase"]]
        visible = fn <= current_fn
        is_current = fn == current_fn
        pts = FLIGHT_PATHS[fn] if visible else []
        return go.Scatter(
            x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines",
            line=dict(color=color, width=3.5 if is_current else 1),
            opacity=1.0 if is_current else 0.4,
            hoverinfo="skip", showlegend=False,
        )

    def head_trace(current_fn):
        row = flights.loc[current_fn]
        x, y = FLIGHT_PATHS[current_fn][-1]
        return go.Scatter(
            x=[x], y=[y], mode="markers",
            marker=dict(symbol="circle", size=12, color="white",
                        line=dict(width=2, color="yellow")),
            showlegend=False,
            hovertemplate=(
                f"<b>Flight {current_fn}</b><br>"
                f"{row['earth_date']:%b %d, %Y}<br>"
                f"Duration: {row['duration_s']}s<br>"
                f"Distance: {row['distance_m']}m"
                "<extra>Current Flight</extra>"
            ),
        )

    def frame_data(current_fn):
        return [path_trace(fn, current_fn) for fn in range(1, n + 1)] + [head_trace(current_fn)]

    origin = go.Scatter(
        x=[0], y=[0], mode="markers+text",
        marker=dict(symbol="star", size=15, color="#FFD700",
                    line=dict(width=1, color="white")),
        text=["WBF"], textposition="top right",
        textfont=dict(color="#FFD700", size=9),
        hoverinfo="skip", showlegend=False,
    )

    fig = go.Figure(
        data=frame_data(1) + [origin],
        frames=[
            go.Frame(
                data=frame_data(k), traces=list(range(n + 1)), name=str(k),
                layout=dict(title_text=(
                    f"<b>Ingenuity Flight Path Animation — Flight {k} of {n}</b><br>"
                    f"<sup>{flights.loc[k, 'earth_date']:%B %d, %Y} | "
                    f"Sol {flights.loc[k, 'sol']} | {flights.loc[k, 'mission_phase']} | "
                    f"{flights.loc[k, 'notes']}</sup>"
                )),
            )
            for k in range(1, n + 1)
        ],
    )

    fig.update_layout(
        title=dict(
            text="<b>Ingenuity Flight Path Animation</b><br>"
                 "<sup>Press play or scrub the timeline</sup>",
            font=dict(size=15, color="white"), x=0.5,
        ),
        updatemenus=[dict(
            type="buttons", direction="left", showactive=False,
            x=0.05, y=-0.06, xanchor="right", yanchor="top",
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=400, redraw=True),
                                      fromcurrent=True,
                                      transition=dict(duration=0))]),
                dict(label="⏸ Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0, x=0.08, y=-0.04, len=0.9,
            steps=[dict(method="animate", label=f"F{i}",
                        args=[[str(i)], dict(mode="immediate",
                                             frame=dict(duration=0, redraw=True),
                                             transition=dict(duration=0))])
                   for i in range(1, n + 1)],
            currentvalue=dict(prefix="Flight: ", font=dict(color="white", size=12)),
            font=dict(color="white", size=8),
            bgcolor="#1a1a2e", bordercolor="#333344",
        )],
        xaxis=dict(title="East (m)", gridcolor=GRID_COLOR, range=[X_MIN, X_MAX]),
        yaxis=dict(title="North (m)", gridcolor=GRID_COLOR,
                   scaleanchor="x", scaleratio=1, range=[Y_MIN, Y_MAX]),
        template="plotly_dark", plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=900, margin=dict(b=110),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 5: HEATMAP — where Ingenuity spent the most airtime
# Each flight's duration is spread evenly along its path length.
# ─────────────────────────────────────────────────────────────────────────────
def chart_heatmap(flight_df, loc_df):
    durations = flight_df.set_index("flight_num")["duration_s"]
    points = []
    for fn, waypoints in FLIGHT_PATHS.items():
        pts = np.array(waypoints, dtype=float)
        seg_len = np.hypot(*np.diff(pts, axis=0).T)
        total = seg_len.sum()
        if total == 0:                       # pure hover: all time at one spot
            points.append((pts[0, 0], pts[0, 1], durations[fn]))
            continue
        for (a, b), length in zip(zip(pts[:-1], pts[1:]), seg_len):
            n_interp = max(int(length // 20), 1)      # one sample per ~20 m
            w = durations[fn] * (length / total) / n_interp
            for t in (np.arange(n_interp) + 0.5) / n_interp:
                points.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), w))

    wp = pd.DataFrame(points, columns=["x", "y", "weight"])

    fig = go.Figure(go.Histogram2dContour(
        x=wp["x"], y=wp["y"], z=wp["weight"], histfunc="sum",
        colorscale=[
            [0.0, "rgba(0,0,0,0)"],
            [0.1, "#0d0d3d"],
            [0.3, "#1a237e"],
            [0.5, "#FF6B6B"],
            [0.7, "#FFD700"],
            [1.0, "#FFFFFF"],
        ],
        colorbar=dict(title=dict(text="Airtime (s)", font=dict(color="white")),
                      tickfont=dict(color="white")),
        contours=dict(showlabels=False, coloring="fill"),
        line=dict(width=0),
        nbinsx=64, nbinsy=82,
        hovertemplate="East %{x:.0f}m, North %{y:.0f}m<br>%{z:.0f}s airtime<extra></extra>",
    ))

    features = loc_df[~loc_df["is_airfield"]]
    fig.add_trace(go.Scatter(
        x=features["east_m"], y=features["north_m"], mode="markers+text",
        marker=dict(size=5, color="white", opacity=0.6),
        text=features["location"], textfont=dict(size=9, color="white"),
        textposition="top right", showlegend=False,
        hovertemplate="%{text}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text="<b>Ingenuity Airtime Heatmap</b><br>"
                 "<sup>Brighter = more cumulative airtime over that location</sup>",
            font=dict(size=15, color="white"), x=0.5,
        ),
        xaxis=dict(title="East (m)", gridcolor=GRID_COLOR, range=[X_MIN, X_MAX]),
        yaxis=dict(title="North (m)", gridcolor=GRID_COLOR,
                   scaleanchor="x", scaleratio=1, range=[Y_MIN, Y_MAX]),
        template="plotly_dark", plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=900,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT ALL
# ─────────────────────────────────────────────────────────────────────────────
def export_map_charts(download=False):
    os.makedirs("outputs", exist_ok=True)

    flight_df = build_dataframe()
    loc_df = build_location_dataframe()
    endpoint_df = build_endpoint_dataframe(flight_df)
    basemap = get_mars_basemap(download=download)

    charts = {
        "map_01_interactive": chart_interactive_map(flight_df, loc_df, endpoint_df),
        "map_03_animated":    chart_animated_map(flight_df),
        "map_04_heatmap":     chart_heatmap(flight_df, loc_df),
    }
    for name, fig in charts.items():
        fig.write_html(f"outputs/{name}.html", include_plotlyjs="cdn",
                       auto_play=False)
        print(f"  ✓ outputs/{name}.html")

    chart_static_map(flight_df, loc_df, endpoint_df, basemap)
    chart_phase_maps(flight_df)
    print("\n✅ All map charts exported")


if __name__ == "__main__":
    export_map_charts(download="--download" in sys.argv)
