# ingenuity_map.py
# Flight-path maps from NASA's real Ingenuity paths (Plotly + Matplotlib).
# Run:  python ingenuity_map.py
import os

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
    FLIGHT_PATHS, X_MAX, X_MIN, Y_MAX, Y_MIN,
    build_endpoint_dataframe, build_location_dataframe,
)
from ingenuity_viz import PHASE_COLORS, SOURCE_NOTE

BG_COLOR = "#0a0a0f"
GRID_COLOR = "#1e1e2e"
PHASE_ORDER = list(PHASE_COLORS)


def synthetic_terrain(width, height, seed=42):
    """Mars-coloured value noise (decorative backdrop only — not real terrain)."""
    rng = np.random.default_rng(seed)
    terrain = np.zeros((height, width))
    for scale in (4, 8, 16, 32, 64, 128):
        small = rng.random((height // scale + 2, width // scale + 2))
        img = Image.fromarray((small * 255).astype(np.uint8))
        up = np.asarray(img.resize((width, height), Image.BICUBIC), dtype=float) / 255
        terrain += up * scale
    terrain = (terrain - terrain.min()) / (terrain.max() - terrain.min())
    rgb = np.stack([0.45 + 0.35 * terrain, 0.22 + 0.18 * terrain,
                    0.08 + 0.10 * terrain], axis=2)
    return (rgb * 255).clip(0, 255).astype(np.uint8)


def _xy(fn):
    pts = FLIGHT_PATHS[fn]
    return [p[0] for p in pts], [p[1] for p in pts]


def _map_axes():
    return dict(
        xaxis=dict(title="East of Wright Brothers Field (m)", gridcolor=GRID_COLOR,
                   zerolinecolor="rgba(255,255,255,0.15)", range=[X_MIN, X_MAX],
                   constrain="domain"),
        yaxis=dict(title="North (m)", gridcolor=GRID_COLOR,
                   zerolinecolor="rgba(255,255,255,0.15)", range=[Y_MIN, Y_MAX],
                   scaleanchor="x", scaleratio=1, constrain="domain"),
    )


def _flight_hover(f):
    return (f"<b>Flight {f.flight_num}</b><br>{f.earth_date:%b %d, %Y} | Sol {f.sol}<br>"
            f"{f.route}<br>Duration: {f.duration_s:g} s | Alt: {f.max_alt_m:g} m<br>"
            f"Distance: {f.distance_m:g} m | Top speed: {f.max_speed_ms:g} m/s"
            "<extra></extra>")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1: PLOTLY INTERACTIVE FLIGHT PATH MAP
# ─────────────────────────────────────────────────────────────────────────────
def chart_interactive_map(flight_df, loc_df, endpoint_df):
    fig = go.Figure()

    for f in flight_df.itertuples():
        xs, ys = _xy(f.flight_num)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", line=dict(color=PHASE_COLORS[f.mission_phase], width=2),
            opacity=0.8, legendgroup=f.mission_phase, showlegend=False,
            hovertemplate=_flight_hover(f),
        ))

    for phase in PHASE_ORDER:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=phase,
                                 legendgroup=phase,
                                 line=dict(color=PHASE_COLORS[phase], width=3)))

    fig.add_trace(go.Scatter(
        x=loc_df["east_m"], y=loc_df["north_m"], mode="markers+text", name="Airfields",
        marker=dict(symbol="triangle-up", size=8, color="#FFD700",
                    line=dict(width=0.5, color="white")),
        text=loc_df["short_name"], textposition="top center",
        textfont=dict(size=8, color="#FFD700"),
        customdata=np.column_stack([loc_df["location"], loc_df["first_flight"]]),
        hovertemplate="<b>%{customdata[0]}</b><br>First landing: flight %{customdata[1]}"
                      "<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=endpoint_df["landing_east"], y=endpoint_df["landing_north"], mode="markers",
        name="Landings", visible="legendonly",
        marker=dict(symbol="x", size=6, color="#FF6B6B"),
        customdata=endpoint_df["flight_num"],
        hovertemplate="Landing F%{customdata}<extra></extra>",
    ))

    final = flight_df[flight_df["final_flag"]].iloc[0]
    fx, fy = _xy(int(final.flight_num))
    fig.add_annotation(x=fx[-1], y=fy[-1], text=f"Final flight F{final.flight_num}<br>"
                       f"{final.earth_date:%b %d, %Y}", showarrow=True, arrowhead=2,
                       ax=-50, ay=-50, font=dict(color="#FF6B6B", size=10),
                       bgcolor="rgba(255,107,107,0.12)", bordercolor="#FF6B6B",
                       arrowcolor="#FF6B6B")
    fig.add_annotation(x=0, y=0, text="Wright Brothers Field<br>(first flight)",
                       showarrow=True, arrowhead=2, ax=-60, ay=-45,
                       font=dict(color="#FFD700", size=10),
                       bgcolor="rgba(255,215,0,0.1)", bordercolor="#FFD700",
                       arrowcolor="#FFD700")

    fig.update_layout(
        title=dict(text="<b>Ingenuity Flight Paths — Jezero Crater, Mars</b><br>"
                        f"<sup>All 72 flights, April 2021 – January 2024 | {SOURCE_NOTE}</sup>",
                   font=dict(size=16, color="white"), x=0.5),
        template="plotly_dark", plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=760, hovermode="closest",
        legend=dict(bgcolor="rgba(0,0,0,0.5)", x=0.01, y=0.99,
                    font=dict(color="white")),
        **_map_axes(),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2: MATPLOTLIB STATIC MAP
# ─────────────────────────────────────────────────────────────────────────────
def chart_static_map(flight_df, loc_df, out="outputs/ingenuity_flight_map.png"):
    width_m, height_m = X_MAX - X_MIN, Y_MAX - Y_MIN
    fig, ax = plt.subplots(figsize=(18, 18 * height_m / width_m + 1.6), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    stroke = [pe.withStroke(linewidth=2.2, foreground=BG_COLOR)]

    for f in flight_df.itertuples():
        xs, ys = _xy(f.flight_num)
        color = PHASE_COLORS[f.mission_phase]
        ax.plot(xs, ys, color=color, lw=1.4, alpha=0.85, zorder=2,
                solid_capstyle="round", solid_joinstyle="round")

    ax.scatter(loc_df["east_m"], loc_df["north_m"], s=22, marker="^", c="#FFD700",
               edgecolors="white", linewidths=0.3, zorder=4)
    for loc in loc_df.itertuples():
        ax.annotate(loc.short_name, (loc.east_m, loc.north_m), textcoords="offset points",
                    xytext=(4, 4), fontsize=6.5, color="#FFD700", zorder=5,
                    path_effects=stroke)

    ax.scatter(0, 0, s=240, c="#FFD700", marker="*", zorder=6,
               edgecolors="white", linewidths=0.5)
    ax.annotate("Wright Brothers Field\n(first flight, Apr 19 2021)", (0, 0),
                textcoords="offset points", xytext=(-14, 14), ha="right", fontsize=9,
                color="#FFD700", fontweight="bold", path_effects=stroke, zorder=7)

    final = flight_df[flight_df["final_flag"]].iloc[0]
    fx, fy = _xy(int(final.flight_num))
    ax.scatter(fx[-1], fy[-1], s=110, c="#FF6B6B", marker="X", zorder=6,
               edgecolors="white", linewidths=0.6)
    ax.annotate(f"Final flight F{final.flight_num}\n{final.earth_date:%b %d, %Y}",
                (fx[-1], fy[-1]), textcoords="offset points", xytext=(0, -38), ha="center",
                fontsize=9, color="#FF6B6B", path_effects=stroke, zorder=7)

    handles = [mpatches.Patch(color=PHASE_COLORS[p], label=p) for p in PHASE_ORDER]
    handles += [plt.Line2D([0], [0], marker="^", color="none", markerfacecolor="#FFD700",
                           markersize=7, label="Airfield")]
    ax.legend(handles=handles, loc="lower left", facecolor="#111111",
              edgecolor=(1, 1, 1, 0.2), fontsize=9, labelcolor="white")

    # North arrow and 1 km scale bar
    nx, ny = X_MAX - 250, Y_MAX - 700
    ax.annotate("", xy=(nx, ny + 450), xytext=(nx, ny),
                arrowprops=dict(arrowstyle="-|>", color="white", lw=1.5))
    ax.text(nx, ny + 520, "N", color="white", ha="center", fontsize=11)
    sx, sy = (X_MIN + X_MAX) / 2 - 500, Y_MIN + 250
    ax.plot([sx, sx + 1000], [sy, sy], "w-", lw=2)
    ax.text(sx + 500, sy + 90, "1 km", color="white", ha="center", fontsize=9)

    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")
    ax.tick_params(colors="#888888", labelsize=8)
    ax.set_xlabel("East of Wright Brothers Field (m)", color="white", fontsize=9)
    ax.set_ylabel("North (m)", color="white", fontsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
    ax.set_title(f"INGENUITY — ALL 72 FLIGHT PATHS, JEZERO CRATER\n{SOURCE_NOTE}",
                 color="white", fontsize=14, fontweight="bold", pad=12)

    fig.savefig(out, dpi=170, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  ✓ {out}")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3: SMALL MULTIPLES — ONE MAP PER PHASE
# ─────────────────────────────────────────────────────────────────────────────
def chart_phase_maps(flight_df, out="outputs/ingenuity_phase_maps.png"):
    fig, axes = plt.subplots(len(PHASE_ORDER), 1, figsize=(14, 4.4 * len(PHASE_ORDER)),
                             facecolor=BG_COLOR)
    for ax, phase in zip(axes, PHASE_ORDER):
        ax.set_facecolor(BG_COLOR)
        sub = flight_df[flight_df["mission_phase"] == phase]
        color = PHASE_COLORS[phase]
        for fn in FLIGHT_PATHS:
            xs, ys = _xy(fn)
            ax.plot(xs, ys, color="#3a3a4a", lw=0.7, zorder=1)
        for fn in sub["flight_num"]:
            xs, ys = _xy(int(fn))
            ax.plot(xs, ys, color=color, lw=2, zorder=3, solid_capstyle="round")
            ax.scatter(xs[-1], ys[-1], s=14, c="white", zorder=4, linewidths=0)
        ax.scatter(0, 0, s=90, c="#FFD700", marker="*", zorder=5)
        ax.set_xlim(X_MIN, X_MAX)
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.set_aspect("equal")
        ax.set_title(f"{phase}: flights {sub.flight_num.min()}–{sub.flight_num.max()} "
                     f"({len(sub)} flights, {sub.distance_m.sum()/1000:.2f} km)",
                     color=color, fontsize=11, loc="left")
        ax.tick_params(colors="#555555", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#222222")
    fig.suptitle("Ingenuity Flight Paths by Phase", color="white", fontsize=15,
                 fontweight="bold")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  ✓ {out}")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4: ANIMATED MAP — flights appear one by one
# Fixed trace layout (one per flight + a head marker) so every frame addresses
# every trace; flights not yet flown are empty.
# ─────────────────────────────────────────────────────────────────────────────
def chart_animated_map(flight_df):
    flights = flight_df.set_index("flight_num")
    nums = list(flights.index)

    def frame_data(cur):
        traces = []
        for fn in nums:
            xs, ys = _xy(fn) if fn <= cur else ([], [])
            is_cur = fn == cur
            traces.append(go.Scatter(
                x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
                line=dict(color=PHASE_COLORS[flights.loc[fn, "mission_phase"]],
                          width=4 if is_cur else 1.2),
                opacity=1.0 if is_cur else 0.45,
            ))
        hx, hy = _xy(cur)
        traces.append(go.Scatter(x=[hx[-1]], y=[hy[-1]], mode="markers", showlegend=False,
                                 hoverinfo="skip",
                                 marker=dict(size=12, color="white",
                                             line=dict(width=2, color="yellow"))))
        return traces

    def frame_title(k):
        r = flights.loc[k]
        return (f"<b>Flight {k} of {len(nums)}</b> · {r.earth_date:%B %d, %Y} · Sol {r.sol}"
                f"<br><sup>{r.notes}</sup>")

    origin = go.Scatter(x=[0], y=[0], mode="markers", hoverinfo="skip", showlegend=False,
                        marker=dict(symbol="star", size=14, color="#FFD700"))
    fig = go.Figure(
        data=frame_data(nums[0]) + [origin],
        frames=[go.Frame(data=frame_data(k), traces=list(range(len(nums) + 1)), name=str(k),
                         layout=dict(title_text=frame_title(k))) for k in nums],
    )
    fig.update_layout(
        title=dict(text=frame_title(nums[0]), font=dict(size=15, color="white"), x=0.5),
        updatemenus=[dict(
            type="buttons", direction="left", showactive=False,
            x=0.05, y=-0.08, xanchor="right", yanchor="top",
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=350, redraw=True),
                                      fromcurrent=True, transition=dict(duration=0))]),
                dict(label="⏸ Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0, x=0.08, y=-0.05, len=0.9,
            steps=[dict(method="animate", label=str(k),
                        args=[[str(k)], dict(mode="immediate",
                                             frame=dict(duration=0, redraw=True),
                                             transition=dict(duration=0))]) for k in nums],
            currentvalue=dict(prefix="Flight ", font=dict(color="white", size=12)),
            font=dict(color="white", size=7), bgcolor="#1a1a2e", bordercolor="#333344",
        )],
        template="plotly_dark", plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=720, margin=dict(b=120),
        **_map_axes(),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 5: AIRTIME HEATMAP — each flight's duration spread along its path
# ─────────────────────────────────────────────────────────────────────────────
def chart_heatmap(flight_df, loc_df):
    durations = flight_df.set_index("flight_num")["duration_s"]
    points = []
    for fn, waypoints in FLIGHT_PATHS.items():
        pts = np.array(waypoints, dtype=float)
        seg_len = np.hypot(*np.diff(pts, axis=0).T) if len(pts) > 1 else np.array([0.0])
        total = seg_len.sum()
        if total < 1:
            points.append((pts[0, 0], pts[0, 1], durations[fn]))
            continue
        for a, b, length in zip(pts[:-1], pts[1:], seg_len):
            n = max(int(length // 25), 1)
            w = durations[fn] * (length / total) / n
            for t in (np.arange(n) + 0.5) / n:
                points.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), w))
    wp = pd.DataFrame(points, columns=["x", "y", "w"])

    fig = go.Figure(go.Histogram2d(
        x=wp["x"], y=wp["y"], z=wp["w"], histfunc="sum",
        xbins=dict(start=X_MIN, end=X_MAX, size=150),
        ybins=dict(start=Y_MIN, end=Y_MAX, size=150),
        colorscale=[[0, "rgba(0,0,0,0)"], [0.001, "#1a237e"], [0.3, "#FF6B6B"],
                    [0.65, "#FFD700"], [1, "#FFFFFF"]],
        colorbar=dict(title="Airtime (s)<br>per 150 m cell"),
        hovertemplate="East %{x}, North %{y}<br>%{z:.0f} s airtime<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=loc_df["east_m"], y=loc_df["north_m"], mode="markers", showlegend=False,
        marker=dict(symbol="triangle-up", size=6, color="white", opacity=0.6),
        text=loc_df["location"], hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Where Ingenuity Spent Its Airtime</b><br>"
                        "<sup>Each flight's duration spread evenly along its path, "
                        "summed in 150 m cells</sup>",
                   font=dict(size=15, color="white"), x=0.5),
        template="plotly_dark", plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        height=720, **_map_axes(),
    )
    return fig


def export_map_charts():
    os.makedirs("outputs", exist_ok=True)
    flight_df = build_dataframe()
    loc_df = build_location_dataframe()
    endpoint_df = build_endpoint_dataframe(flight_df)

    charts = {
        "map_01_interactive": chart_interactive_map(flight_df, loc_df, endpoint_df),
        "map_03_animated":    chart_animated_map(flight_df),
        "map_04_heatmap":     chart_heatmap(flight_df, loc_df),
    }
    for name, fig in charts.items():
        fig.write_html(f"outputs/{name}.html", include_plotlyjs="cdn", auto_play=False)
        print(f"  ✓ outputs/{name}.html")

    chart_static_map(flight_df, loc_df)
    chart_phase_maps(flight_df)
    print("\n✅ All map charts exported")


if __name__ == "__main__":
    export_map_charts()
