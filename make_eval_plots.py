"""Evaluation figures and LaTeX tables for Harvest (Section 7).

Data: the `rq/` results directory (rq1_view, rq1, rq2, rq3, rq4, rq5, rq_cult_sweep) and
`new_experiments/` (E10 framework vs. scheduler, E14 cultivation sensitivity).
Style: follows plot_code/single_column_paper_plots.py and the combined
row scripts (1 x N panels, page width, pastel bars with hatches, shared
legend, bold "(a)" panel titles, blue "lower/higher is better" marker).

Usage:  python make_eval_plots.py /path/to/rq  figures/evaluation  [/path/to/new_experiments]

Writes every figure (.pdf + .png preview), its .tex wrapper, and the LaTeX tables.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns

# --------------------------------------------------------------------------
# Style (copied from plot_code/utils.py + single_column_paper_plots.py)
# --------------------------------------------------------------------------
code_palette = sns.color_palette("pastel", n_colors=10)
code_palette_muted = sns.color_palette("muted", n_colors=10)
code_palette_deep = sns.color_palette("deep", n_colors=10)
code_hatches = ["/", "\\", "//", "++", "xx", "**"]

FONTSIZE = 12              # every text element; values on top of bars use FONTSIZE - 2

plt.rcParams.update({
    "font.family": "serif",
    "font.size": FONTSIZE,
    "lines.linewidth": 1.4,
    "lines.markersize": 4,
    "lines.markeredgewidth": 0.6,
    "lines.markeredgecolor": "black",
    "errorbar.capsize": 2,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "hatch.linewidth": 0.5,
})

PAPER_WIDTH = 9.5          # wider row for a single-column (acmsmall) page; was 7.2
ROW_HEIGHT = 2.2           # same figure height as the Framed paper plots (HEIGHT_FIGSIZE)
LABEL_SIZE = TICK_SIZE = TITLE_SIZE = MARKER_SIZE = FONTSIZE
LEGEND_SIZE = FONTSIZE - 2
BAR_VALUE_SIZE = FONTSIZE - 2
LOWER = r"Lower is better $\downarrow$"
HIGHER = r"Higher is better $\uparrow$"


def tight_layout_engine(fig) -> None:
    """Constrained layout (no overlapping labels) with little space between panels."""
    fig.set_layout_engine("constrained")
    fig.get_layout_engine().set(w_pad=2 / 72, h_pad=2 / 72, wspace=0.0, hspace=0.0)


AXES_HEIGHT = 1.285   # plotting-area height of a 2.2in row whose x labels are not rotated


def match_axes_height(fig, target: float = AXES_HEIGHT) -> None:
    """Grow the figure until its panels are ``target`` inches tall.

    For rows with rotated x tick labels, which need more room below the panels:
    the plotting area then matches the other figures, only the figure is taller.
    """
    for _ in range(4):
        fig.canvas.draw()
        h = fig.axes[0].get_position().height * fig.get_figheight()
        if abs(h - target) < 0.003:
            break
        fig.set_figheight(fig.get_figheight() + target - h)


PANEL_WIDTH = 2.40    # width of one panel slot in every row figure (inches)


def fix_panel_width(fig, axes) -> None:
    """Give every panel of a row the same width in every figure.

    The constrained layout sizes panels per figure, so their width depends on
    each figure's labels.  Freeze its result, set each slot to PANEL_WIDTH (a
    first panel spanning two slots gets 2*PANEL_WIDTH plus the gap), keep the
    gaps it computed, and center the row.  The figure width stays the same, so
    the panels also have the same width on the page.
    """
    fig.canvas.draw()
    fw = fig.get_figwidth()
    pos = [ax.get_position() for ax in axes]
    gaps = [pos[i + 1].x0 - pos[i].x1 for i in range(len(pos) - 1)]
    w = PANEL_WIDTH / fw
    widths = [w] * len(axes) if len(axes) == 3 else [2 * w + gaps[0], w]
    total = sum(widths) + sum(gaps)
    if total > pos[-1].x1 - pos[0].x0 + 1e-6:
        raise ValueError(f"row does not fit with PANEL_WIDTH = {PANEL_WIDTH} in")
    x = pos[0].x0 + ((pos[-1].x1 - pos[0].x0) - total) / 2
    fig.set_layout_engine("none")   # keep the positions set below
    for ax, p_, t, g in zip(axes, pos, widths, gaps + [0]):
        ax.set_position([x, p_.y0, t, p_.height])
        x += t + g


def row_figure(n_panels: int, height: float = ROW_HEIGHT, sharey: bool = False):
    """A row of panels on a grid of three equal slots.

    Three panels take one slot each, so they all have the same width; with two
    panels the first one spans two slots.
    """
    fig = plt.figure(figsize=(PAPER_WIDTH, height))
    tight_layout_engine(fig)
    gs = fig.add_gridspec(1, 3)
    if n_panels == 3:
        axes = list(gs.subplots(sharey=sharey))
    elif n_panels == 2:
        a = fig.add_subplot(gs[0, :2])
        axes = [a, fig.add_subplot(gs[0, 2], sharey=a if sharey else None)]
    else:
        raise ValueError(f"row_figure supports 2 or 3 panels, not {n_panels}")
    fig._row_axes = axes   # save() fixes their width
    return fig, axes

# Order used in every plot and table: baselines first, Harvest last (rightmost).
COMPILERS = ["Litinski", "O3LS", "EAF", "PureMagic", "Harvest"]
BASELINES = COMPILERS[:-1]
SOTA_ORDER = COMPILERS
MODELS = ["instant", "cultivation"]
MODEL_LABELS = {"instant": "Free model", "cultivation": "Cultivation"}

# One hue per framework, used in all figures. Instant = darker shade, cultivation = lighter.
_HUE = {"Harvest": 0, "EAF": 1, "PureMagic": 2, "Litinski": 3, "O3LS": 4}


def _lighten(rgb, amount):
    return tuple(1 - (1 - x) * (1 - amount) for x in rgb)


COMPILER_COLORS = {c: code_palette_deep[i] for c, i in _HUE.items()}          # lines / points
BAR_COLOR = {c: {"instant": code_palette_muted[i], "cultivation": code_palette[i]}
             for c, i in _HUE.items()}                                         # bars
LINE_COLOR = {c: {"instant": code_palette_deep[i],
                  "cultivation": _lighten(code_palette_deep[i], 0.45)}
              for c, i in _HUE.items()}                                        # lines per model
# Neutral colors for things that are not frameworks
TEMPLATE_COLORS = {"ring": code_palette_deep[5], "blocks4": code_palette_deep[6],
                   "dense4": code_palette_deep[9]}
OBLIVIOUS_COLOR = code_palette_deep[7]
PHASE_COLORS = [code_palette[5], code_palette[6], code_palette[7], code_palette[8]]
# instant vs cultivation pairs: "/" vs "\\" look too alike, so use clearly different patterns
MODEL_HATCH = {"instant": "*", "cultivation": "//"}


def model_legend_handles(compiler: str | None = None):
    """Legend patches for the two magic-state models (gray, or in a framework's hue)."""
    from matplotlib.patches import Patch
    out = []
    for m, gray in [("instant", "0.55"), ("cultivation", "0.85")]:
        color = BAR_COLOR[compiler][m] if compiler else gray
        out.append(Patch(facecolor=color, edgecolor="black", linewidth=0.45,
                         hatch=MODEL_HATCH[m], label=MODEL_LABELS[m]))
    return out


def gmean(x) -> float:
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    x = x[x > 0]
    return float(np.exp(np.log(x).mean())) if len(x) else float("nan")


def panel_title(letter: str, title: str) -> str:
    return rf"$\mathbf{{({letter})}}$ {title}"


def panel_markers(fig, axes, labels) -> None:
    """Blue "lower/higher is better" marker centered over every panel.

    ``labels`` is one string for all panels or one per panel ("" = no marker).
    The markers share one row above the panel titles; an invisible suptitle makes
    the constrained layout reserve that row.
    """
    from matplotlib.transforms import blended_transform_factory
    if isinstance(labels, str):
        labels = [labels] * len(axes)
    fig.suptitle(max(labels, key=len), fontsize=MARKER_SIZE, fontweight="bold", color="none")
    y = fig._suptitle.get_position()[1]
    for ax, label in zip(axes, labels):
        if not label:
            continue
        t = fig.text(0.5, y, label, transform=blended_transform_factory(ax.transAxes, fig.transFigure),
                     ha="center", va="top", fontsize=MARKER_SIZE, fontweight="bold", color="blue")
        t.set_in_layout(False)


def panel_legend(ax, *args, **kw):
    """Legend inside a panel, at FONTSIZE - 2."""
    kw.setdefault("frameon", False)
    kw.setdefault("fontsize", LEGEND_SIZE)
    kw.setdefault("columnspacing", 1.0)
    kw.setdefault("handletextpad", 0.4)
    kw.setdefault("borderaxespad", 0.3)
    return ax.legend(*args, **kw)


def style_axis(ax, grid_axis: str = "y") -> None:
    ax.tick_params(axis="both", labelsize=TICK_SIZE, pad=1.5)
    ax.grid(axis=grid_axis, linestyle="--", linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)


def save(fig, path: Path) -> None:
    if hasattr(fig, "_row_axes"):
        fix_panel_width(fig, fig._row_axes)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf")
    fig.savefig(path.with_suffix(".png"), dpi=200)
    plt.close(fig)
    print(f"Saved {path}")


def bar_labels(ax, bars, values, y_max, fmt="{:.2f}", clip=None, rotation=90):
    for bar, v in zip(bars, values):
        if not np.isfinite(v):
            continue
        h = min(v, clip) if clip else v
        ax.text(bar.get_x() + bar.get_width() / 2, h + y_max * 0.02,
                fmt.format(v), ha="center", va="bottom", fontsize=BAR_VALUE_SIZE,
                rotation=rotation)


# --------------------------------------------------------------------------
# Data loading (rq/ only)
# --------------------------------------------------------------------------
class Data:
    def __init__(self, rq: Path):
        self.rq = rq
        pc = pd.read_csv(rq / "rq1_view" / "rq1_per_circuit.csv")
        self.pc = pc[pc.model.isin(MODELS)].copy()
        # circuits where Harvest finished (ratios are only defined there)
        self.harvest_circuits = {
            m: set(self.pc[(self.pc.compiler == "Harvest") & (self.pc.model == m)].circuit)
            for m in MODELS
        }
        self.rq1 = pd.read_csv(rq / "rq1" / "rq1.csv", low_memory=False)
        self.rq2_ratios = pd.read_csv(rq / "rq2" / "rq2_ratios.csv")
        self.rq2_summary = pd.read_csv(rq / "rq2" / "rq2_ablation_summary.csv")
        self.rq2_nego = pd.read_csv(rq / "rq2" / "rq2_negotiation_cdf.csv")
        self.rq2_sens = pd.read_csv(rq / "rq2" / "rq2_sensitivity.csv")
        self.rq3 = pd.read_csv(rq / "rq3" / "rq3_levels.csv")
        self.rq4 = pd.read_csv(rq / "rq4" / "rq4_curves_per_circuit.csv")
        self.rq4_obl = pd.read_csv(rq / "rq4" / "rq4_oblivious_vs_aware.csv")
        self.rq4_plug = pd.read_csv(rq / "rq4" / "rq4_pluggability.csv")
        self.rq5_census = pd.read_csv(rq / "rq5" / "rq5_census.csv")
        self.rq5_faults = pd.read_csv(rq / "rq5" / "rq5_faults.csv")
        self.rq5_fit = pd.read_csv(rq / "rq5" / "rq5_scaling_fit.csv")

    def ratios(self, model: str) -> pd.DataFrame:
        """Per-circuit ratios compiler / Harvest on circuits Harvest finished."""
        s = self.pc[(self.pc.model == model)
                    & self.pc.circuit.isin(self.harvest_circuits[model])]
        return s

    def template_volumes(self) -> pd.DataFrame:
        """Harvest volume per fixed template, from `auto_volumes` (mean over seeds)."""
        rows = []
        d = self.rq1[self.rq1.model.isin(MODELS) & (self.rq1.status == "ok")]
        for _, r in d.iterrows():
            try:
                av = json.loads(r.auto_volumes)
            except (TypeError, ValueError):
                continue
            for tpl, v in av.items():
                rows.append((r.circuit, r.model, tpl, float(v)))
        tv = pd.DataFrame(rows, columns=["circuit", "model", "template", "volume"])
        return tv.groupby(["circuit", "model", "template"], as_index=False).volume.mean()


# --------------------------------------------------------------------------
# Fig. 1  RQ1 - state of the art: time, area, volume (normalized to Harvest)
# --------------------------------------------------------------------------
def fig_sota(D: Data, out: Path) -> None:
    """(a) makespan / T_cp; (b) area / n; (c) volume / (n * T_cp). All size-normalized."""
    metrics = [
        ("vol_per_qubit_cp", "Space-time volume", r"Volume / ($n$ $\times$ depth)", 9.0,
         r"solid line: $n$ data patches for depth steps"),
        ("T_over_cp", "Timesteps", r"Timesteps / depth", 3.0,
         r"solid line: circuit depth"),
        ("area_per_qubit", "Patches per logical qubit", r"Patches / $n$", 6.0,
         "solid line: data patches only"),
    ]
    vals = {m: {} for m in MODELS}
    for m in MODELS:
        r = D.ratios(m).copy()
        r["area_per_qubit"] = r.area / r.num_qubits
        r["vol_per_qubit_cp"] = r.volume / (r.num_qubits * r.critical_path)
        for c in SOTA_ORDER:
            rc = r[r.compiler == c]
            vals[m][c] = {k: gmean(rc[k]) for k, *_ in metrics}

    fig, axes = row_figure(3)
    xs = np.arange(len(SOTA_ORDER))
    w = 0.38
    for i, (ax, (key, title, ylabel, clip, refl)) in enumerate(zip(axes, metrics)):
        for j, m in enumerate(MODELS):
            v = np.array([vals[m][c][key] for c in SOTA_ORDER])
            bars = ax.bar(xs + (j - 0.5) * w, np.minimum(v, clip), width=w,
                          color=[BAR_COLOR[c][m] for c in SOTA_ORDER], hatch=MODEL_HATCH[m],
                          edgecolor="black", linewidth=0.45)
            bar_labels(ax, bars, v, clip, clip=clip)
        ax.axhline(1.0, color="black", linewidth=0.9)
        # separate Harvest (rightmost) from the baselines
        ax.axvline(len(SOTA_ORDER) - 1.5, color="black", linestyle="--", linewidth=0.7, alpha=0.7)
        ax.set_xticks(xs)
        ax.set_xticklabels(SOTA_ORDER, rotation=30, ha="right", rotation_mode="anchor",
                           fontsize=TICK_SIZE)
        ax.set_ylim(0, clip * 1.75)
        ax.set_ylabel(ylabel, fontsize=LABEL_SIZE, labelpad=1)
        ax.set_title(panel_title(chr(97 + i), title), fontsize=TITLE_SIZE, loc="left", pad=3)
        style_axis(ax)
    panel_legend(axes[2], handles=model_legend_handles(), loc="upper left", ncol=2,
                 handlelength=1.5, handleheight=1.2, columnspacing=0.6)
    panel_markers(fig, axes, LOWER)
    match_axes_height(fig)
    save(fig, out / "fig_rq1_sota.pdf")
    # numbers for the text
    rows = [(m, c, *[vals[m][c][k] for k, *_ in metrics]) for m in MODELS for c in SOTA_ORDER]
    pd.DataFrame(rows, columns=["model", "compiler"] + [k for k, *_ in metrics]).round(3) \
        .to_csv(out / "fig_rq1_sota_values.csv", index=False)


# --------------------------------------------------------------------------
# Fig. 2  RQ1 - per-circuit distribution of the volume ratio
# --------------------------------------------------------------------------
def fig_sota_distribution(D: Data, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(PAPER_WIDTH, ROW_HEIGHT), sharey=True)
    tight_layout_engine(fig)
    for i, (ax, m) in enumerate(zip(axes, MODELS)):
        r = D.ratios(m)
        for c in BASELINES:
            v = np.sort(r[r.compiler == c].volume_ratio.dropna().to_numpy())
            if not len(v):
                continue
            frac = np.arange(1, len(v) + 1) / len(v)
            wins = int((v > 1.01).sum())
            ax.plot(frac, v, color=COMPILER_COLORS[c], linewidth=1.4,
                    label=c if i == 0 else None)
            ax.text(1.0, v[-1], f" {wins}/{len(v)}", fontsize=FONTSIZE,
                    color=COMPILER_COLORS[c], va="center", ha="left")
        ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda y, _: f"{y:g}"))
        ax.yaxis.set_minor_formatter(mtick.NullFormatter())
        ax.set_yticks([0.5, 1, 2, 5, 10, 20])
        ax.set_xlim(0, 1.12)
        ax.set_title(panel_title(chr(97 + i), f"{MODEL_LABELS[m]} magic states"),
                     fontsize=TITLE_SIZE, loc="left", pad=3)
        style_axis(ax, "both")
    for ax in axes:
        ax.set_ylabel("Volume / Harvest volume", fontsize=LABEL_SIZE, labelpad=2)
    for ax in axes:
        ax.set_xlabel("Fraction of circuits", fontsize=LABEL_SIZE)
    h, l = axes[0].get_legend_handles_labels()
    panel_legend(axes[0], h, l, loc="upper left", ncol=2, handlelength=1.4)
    panel_markers(fig, axes, r"Above 1: Harvest better $\uparrow$")
    save(fig, out / "fig_rq1_per_circuit.pdf")


# --------------------------------------------------------------------------
# Fig. 2b  RQ1 - cost against circuit size (#qubits as the reference)
# --------------------------------------------------------------------------
QUBIT_BINS = [1, 4, 9, 19, 34, 59, 99]
QUBIT_LABELS = ["2-4", "5-9", "10-19", "20-34", "35-59", "60-98"]
COMPILER_MARKERS = {"Harvest": "o", "EAF": "s", "PureMagic": "^", "Litinski": "D", "O3LS": "X"}


def size_curves(D: Data, model: str) -> pd.DataFrame:
    r = D.ratios(model).copy()
    r["area_per_qubit"] = r.area / r.num_qubits
    r["vol_per_qubit_cp"] = r.volume / (r.num_qubits * r.critical_path)
    r["bin"] = pd.cut(r.num_qubits, QUBIT_BINS, labels=QUBIT_LABELS)
    g = (r.groupby(["compiler", "bin"], observed=False)
          .agg(n=("circuit", "size"), T_over_cp=("T_over_cp", gmean),
               area_per_qubit=("area_per_qubit", gmean),
               vol_per_qubit_cp=("vol_per_qubit_cp", gmean))
          .reset_index())
    g["model"] = model
    return g




SIZE_WINDOW = 9   # rolling geometric mean over this many neighbouring circuits


def fig_size(D: Data, out: Path) -> pd.DataFrame:
    """Circuits sorted by size on x; per framework: faint per-circuit markers and a
    rolling geometric mean line."""
    metrics = [
        ("vol_per_qubit_cp", "Space-time volume", r"Volume / ($n$ $\times$ depth)",
         [1, 3, 10, 30, 100]),
        ("T_over_cp", "Timesteps", r"Timesteps / depth",
         [1, 3, 10, 30, 100]),
        ("area_per_qubit", "Patches per logical qubit", r"Patches / $n$", [1, 2, 3, 5, 10]),
    ]
    all_curves = []
    for model in MODELS:
        r = D.ratios(model).copy()
        r["area_per_qubit"] = r.area / r.num_qubits
        r["vol_per_qubit_cp"] = r.volume / (r.num_qubits * r.critical_path)
        # one shared order of circuits: by qubits, then by number of rotations
        order = (r[r.compiler == "Harvest"].sort_values(["num_qubits", "ops", "circuit"])
                 .circuit.tolist())
        pos = {c: i for i, c in enumerate(order)}
        nq = r[r.compiler == "Harvest"].set_index("circuit").num_qubits.reindex(order).to_numpy()
        fig, axes = row_figure(3)
        for i, (ax, (key, title, ylabel, yt)) in enumerate(zip(axes, metrics)):
            for c in COMPILERS:
                s_ = r[r.compiler == c].set_index("circuit")[key].reindex(order)
                x = np.arange(len(order))
                col = COMPILER_COLORS[c]   # one model per figure: use the full hue
                roll = np.exp(np.log(s_).rolling(SIZE_WINDOW, center=True,
                                                  min_periods=SIZE_WINDOW // 2 + 1).mean())
                ax.plot(x, roll.to_numpy(), color=col, linewidth=1.5 if c == "Harvest" else 1.2,
                        zorder=4 if c == "Harvest" else 3, label=c)
                all_curves.append(pd.DataFrame({"model": model, "compiler": c, "metric": key,
                                                "circuit": order, "num_qubits": nq,
                                                "value": s_.to_numpy(),
                                                "rolling_gmean": roll.to_numpy()}))
            ax.axhline(1.0, color="black", linewidth=0.9)
            ax.set_yscale("log")
            ax.yaxis.set_major_locator(mtick.FixedLocator(yt))
            ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda y, _: f"{y:g}"))
            ax.yaxis.set_minor_formatter(mtick.NullFormatter())
            # x ticks: label positions with the qubit count of the circuit there
            ticks = [k for k in np.linspace(0, len(order) - 1, 7).round().astype(int)]
            ax.set_xticks(ticks)
            ax.set_xticklabels([str(int(nq[k])) for k in ticks], fontsize=TICK_SIZE)
            ax.set_xlim(-1, len(order))
            ax.set_ylabel(ylabel, fontsize=LABEL_SIZE, labelpad=1)
            ax.set_title(panel_title(chr(97 + i), title), fontsize=TITLE_SIZE, loc="left", pad=3)
            style_axis(ax, "both")
        axes[1].set_xlabel("Logical qubits $n$", fontsize=LABEL_SIZE)
        h, l = axes[0].get_legend_handles_labels()
        # legend in the empty upper-left of (b); raise its top so the curves stay clear
        lo, hi = axes[1].get_ylim()
        axes[1].set_ylim(lo, hi * 6)
        panel_legend(axes[1], h, l, loc="upper left", ncol=2, handlelength=1.4,
                     columnspacing=0.8, labelspacing=0.25)
        panel_markers(fig, axes, LOWER)
        save(fig, out / f"fig_rq1_size_{model}.pdf")
    return pd.concat(all_curves)


# --------------------------------------------------------------------------
# Fig. 2c  RQ1 - per circuit family (volume, timesteps, patches per qubit)
# --------------------------------------------------------------------------
FAMILY_LABELS = {
    "qft": "QFT", "qaoa": "QAOA", "heisenberg_square": "Heisenberg", "ising": "Ising",
    "adder": "Adder", "dnn": "DNN", "knn": "kNN", "wstate": "W state",
    "multiplier": "Multiplier", "random": "Random", "swap_test": "Swap test",
    "vqe_uccsd": "VQE-UCCSD", "qugan": "QuGAN", "other": "Other",
}
FAMILY_MIN_CIRCUITS = 3   # smaller families are merged into "Other"


def family_curves(D: Data, model: str) -> pd.DataFrame:
    r = D.ratios(model).copy()
    r["area_per_qubit"] = r.area / r.num_qubits
    r["vol_per_qubit_cp"] = r.volume / (r.num_qubits * r.critical_path)
    sizes = r[r.compiler == "Harvest"].groupby("family").circuit.nunique()
    keep = set(sizes[sizes >= FAMILY_MIN_CIRCUITS].index)
    r["fam"] = np.where(r.family.isin(keep), r.family, "other")
    g = (r.groupby(["compiler", "fam"])
          .agg(n=("circuit", "nunique"), T_over_cp=("T_over_cp", gmean),
               area_per_qubit=("area_per_qubit", gmean),
               vol_per_qubit_cp=("vol_per_qubit_cp", gmean))
          .reset_index())
    g["model"] = model
    order = list(sizes[sizes >= FAMILY_MIN_CIRCUITS].sort_values(ascending=False).index) + ["other"]
    return g, order


def fig_family(D: Data, out: Path) -> pd.DataFrame:
    """One figure per supply model; three stacked panels share the family axis."""
    metrics = [
        ("vol_per_qubit_cp", "Space-time volume", r"Vol. / ($n$ $\times$ depth)", 10.0),
        ("T_over_cp", "Timesteps", r"Timesteps / depth", 3.0),
        ("area_per_qubit", "Patches per logical qubit", r"Patches / $n$", 7.0),
    ]
    all_g = []
    for model in MODELS:
        g, order = family_curves(D, model)
        all_g.append(g)
        fig, axes = plt.subplots(3, 1, figsize=(PAPER_WIDTH, 6.6), sharex=True)
        tight_layout_engine(fig)
        xs = np.arange(len(order))
        w = 0.16
        for i, (ax, (key, title, ylabel, clip)) in enumerate(zip(axes, metrics)):
            for j, c in enumerate(COMPILERS):
                v = g[g.compiler == c].set_index("fam").reindex(order)[key].to_numpy()
                bars = ax.bar(xs + (j - 2) * w, np.minimum(v, clip), width=w,
                              color=BAR_COLOR[c][model], hatch=MODEL_HATCH[model],
                              edgecolor="black", linewidth=0.35, label=c)
                for bar, val in zip(bars, v):
                    if np.isfinite(val) and val > clip:
                        y = clip * (1.02 if j % 2 == 0 else 1.17)
                        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{val:.0f}",
                                ha="center", va="bottom", fontsize=BAR_VALUE_SIZE)
            ax.axhline(1.0, color="black", linewidth=0.9)
            ax.set_ylim(0, clip * 1.32)
            ax.set_ylabel(ylabel, fontsize=LABEL_SIZE, labelpad=1)
            ax.set_title(panel_title(chr(97 + i), title), fontsize=TITLE_SIZE, loc="left", pad=2)
            style_axis(ax)
        n = g[g.compiler == "Harvest"].set_index("fam").reindex(order).n
        axes[-1].set_xticks(xs)
        axes[-1].set_xticklabels([f"{FAMILY_LABELS.get(f, f)}\n({int(k)})" for f, k in zip(order, n)],
                                 fontsize=TICK_SIZE)
        h, l = axes[0].get_legend_handles_labels()
        panel_legend(axes[0], h, l, loc="upper right", ncol=5, handlelength=1.4)
        for ax in axes:   # wide stacked panels: marker at the right end of each title row
            ax.set_title(LOWER, loc="right", fontsize=MARKER_SIZE, fontweight="bold",
                         color="blue", pad=2)
        save(fig, out / f"fig_rq1_family_{model}.pdf")
    return pd.concat(all_g)


# --------------------------------------------------------------------------
# Fig. 3  RQ2 - where does the advantage come from?
# --------------------------------------------------------------------------
TEMPLATES = ["ring", "blocks4", "dense4", "dense4full"]
TEMPLATE_LABELS = {"ring": "Ring", "blocks4": "Blocks4", "dense4": "Dense4",
                   "dense4full": "Dense4F", "auto": "Auto", "PureMagic": "PureMagic"}
ABLATIONS = ["-admission", "-pruning", "-priority", "-retry", "-placement",
             "-matching", "-negotiation", "-yfactor"]
ABLATION_LABELS = {"-admission": "Admission", "-pruning": "Pruning", "-priority": "Priority",
                   "-retry": "Retry", "-placement": "Placement", "-matching": "Matching",
                   "-negotiation": "Negotiation", "-yfactor": "Y-term"}


def template_ratio_table(D: Data) -> pd.DataFrame:
    """geomean(volume_X / volume_Harvest-auto) for every template and PureMagic."""
    tv = D.template_volumes()
    rows = []
    for m in MODELS:
        r = D.ratios(m)
        h = r[r.compiler == "Harvest"].set_index("circuit").volume
        pm = r[r.compiler == "PureMagic"].set_index("circuit").volume
        for tpl in TEMPLATES:
            t = tv[(tv.model == m) & (tv.template == tpl)].set_index("circuit").volume
            common = t.index.intersection(h.index)
            rows.append((m, tpl, gmean(t[common] / h[common]),
                         gmean(pm[common.intersection(pm.index)] / t[common.intersection(pm.index)])))
        rows.append((m, "auto", 1.0, gmean(pm[h.index.intersection(pm.index)] / h[h.index.intersection(pm.index)])))
        rows.append((m, "PureMagic", gmean(pm[h.index.intersection(pm.index)] / h[h.index.intersection(pm.index)]), 1.0))
    return pd.DataFrame(rows, columns=["model", "layout", "vol_over_auto", "pm_over_layout"])


def fig_contributions(D: Data, out: Path) -> pd.DataFrame:
    tr = template_ratio_table(D)
    fig, axes = row_figure(3)

    # (a) layout template
    ax = axes[0]
    order = TEMPLATES + ["auto", "PureMagic"]
    xs = np.arange(len(order))
    w = 0.45
    ymax = 3.6
    for j, m in enumerate(MODELS):
        v = np.array([tr[(tr.model == m) & (tr.layout == k)].vol_over_auto.iloc[0] for k in order])
        cols = [BAR_COLOR["PureMagic" if k == "PureMagic" else "Harvest"][m] for k in order]
        bars = ax.bar(xs + (j - 0.5) * w, v, width=w, color=cols,
                      hatch=MODEL_HATCH[m], edgecolor="black", linewidth=0.45)
        bar_labels(ax, bars, v, ymax)
    # separator stops below the legend row
    ax.axvline(len(TEMPLATES) + 0.5, ymax=0.78, color="black", linestyle="--", linewidth=0.7,
               alpha=0.7)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([TEMPLATE_LABELS[k] for k in order], rotation=45, ha="right",
                       rotation_mode="anchor", fontsize=TICK_SIZE)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Volume ratio", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("a", "Layout (vs. Auto)"), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax)

    # (b) leave-one-out ablation
    ax = axes[1]
    s = D.rq2_summary[D.rq2_summary.template == "all"]
    xs = np.arange(len(ABLATIONS))
    ymax = 3.2
    tallest = max(s[s.ablation.isin(ABLATIONS)].volume_ratio_geomean)
    for j, m in enumerate(MODELS):
        v = np.array([s[(s.model == m) & (s.ablation == a)].volume_ratio_geomean.iloc[0]
                      for a in ABLATIONS])
        bars = ax.bar(xs + (j - 0.5) * 0.5, v, width=w, color=BAR_COLOR["Harvest"][m],
                      hatch=MODEL_HATCH[m], edgecolor="black", linewidth=0.45)
        # label only the tallest bar; the others are all close to 1
        bar_labels(ax, bars, np.where(v == tallest, v, np.nan), ymax)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([ABLATION_LABELS[a] for a in ABLATIONS], rotation=45, ha="right",
                       rotation_mode="anchor", fontsize=TICK_SIZE)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Volume ratio", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("b", "Without component"), fontsize=TITLE_SIZE,
                 loc="left", pad=3)
    style_axis(ax)

    # (c) negotiation: per-run makespan reduction, sorted
    ax = axes[2]
    n = D.rq2_nego
    for tpl in ["ring", "blocks4", "dense4"]:   # cultivated magic states only
        v = np.sort(n[(n.template == tpl) & (n.model == "cultivation")]
                    .makespan_reduction.to_numpy())[::-1] * 100
        frac = np.arange(1, len(v) + 1) / len(v)
        ax.plot(frac, v, color=TEMPLATE_COLORS[tpl], linewidth=1.6, label=TEMPLATE_LABELS[tpl])

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xlabel("Fraction of runs", fontsize=LABEL_SIZE, labelpad=1)
    ax.set_ylabel("Reduction (%)", fontsize=LABEL_SIZE, labelpad=1)
    ax.set_xlim(0, 1.02)
    # many runs gain 0 % and a few lose, so a plain log axis is impossible: symmetric
    # log, linear within +-1 %; the top is raised to leave room for the legend
    ax.set_yscale("symlog", linthresh=1.0, linscale=0.6)
    ax.set_ylim(-15, 1000)
    ax.yaxis.set_major_locator(mtick.FixedLocator([-10, 0, 10]))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda y, _: f"{y:g}"))
    ax.yaxis.set_minor_locator(mtick.NullLocator())
    ax.set_xticks([0, 0.5, 1])
    ax.set_title(panel_title("c", "Negotiation gain"), fontsize=TITLE_SIZE, loc="left", pad=3)
    panel_legend(ax, loc="upper center", ncol=3, handlelength=1.0, columnspacing=0.6,
                 handletextpad=0.3)
    style_axis(ax, "both")

    panel_legend(axes[0], handles=model_legend_handles("Harvest"), loc="upper center",
                 ncol=2, handlelength=1.5, handleheight=1.0, columnspacing=0.6)
    direction_labels = [LOWER, HIGHER, HIGHER]
    panel_markers(fig, axes, direction_labels)
    match_axes_height(fig)
    save(fig, out / "fig_rq2_contributions.pdf")
    return tr


# --------------------------------------------------------------------------
# Fig. 3b  RQ2 - framework vs. scheduler, scheduler gain per family, ablation
# Data: new_experiments/E10_framework_vs_scheduler + rq/rq2 (leave-one-out)
# --------------------------------------------------------------------------
E10_BARS = [("EAF", "blocks4"), ("EAF", "auto"), ("Harvest", "blocks4"), ("Harvest", "auto")]
E10_LABELS = {("EAF", "blocks4"): "EAF\nBlocks4", ("EAF", "auto"): "EAF\nAuto",
              ("Harvest", "blocks4"): "Harvest\nBlocks4", ("Harvest", "auto"): "Harvest\nAuto"}


def e10_tables(ne: Path, rq: Path):
    tab = pd.read_csv(ne / "E10_framework_vs_scheduler" / "e10_table.csv")
    pc = pd.read_csv(ne / "E10_framework_vs_scheduler" / "e10_per_circuit.csv")
    fam = pd.read_csv(rq / "suite.csv")[["circuit", "family"]]
    x = pc[(pc.compiler == "EAF") & (pc.template == "auto") & (pc.pruning == "on")].merge(fam, on="circuit")
    n_inst = x[x.model == "instant"].groupby("family").size()
    single = set(n_inst[n_inst < 2].index)
    x["fam"] = x.family.where(~x.family.isin(single), "other")
    g = x.groupby(["fam", "model"]).volume_ratio.apply(gmean).unstack()
    g["n"] = x[x.model == "instant"].groupby("fam").size()
    order = g.drop(index="other").sort_values("cultivation", ascending=False).index.tolist() + ["other"]
    return tab, g.loc[order]


def fig_sources(D: Data, ne: Path, rq: Path, out: Path) -> pd.DataFrame:
    tab, fam = e10_tables(ne, rq)
    fig, axes = row_figure(3)
    w = 0.38

    # (a) framework vs. scheduler
    ax = axes[0]
    xs = np.arange(len(E10_BARS))
    ymax = 3.0
    for j, m in enumerate(MODELS):
        v = []
        for comp, tpl in E10_BARS:
            r = tab[(tab.supply == m) & (tab.scheduler == comp) & (tab.layout == tpl) & (tab.pruning == "on")]
            v.append(float(r.vol_geomean.iloc[0]))
        v = np.array(v)
        cols = [BAR_COLOR[comp][m] for comp, _ in E10_BARS]
        bars = ax.bar(xs + (j - 0.5) * w, v, width=w, color=cols, hatch=MODEL_HATCH[m],
                      edgecolor="black", linewidth=0.45)
        bar_labels(ax, bars, v, ymax)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    # separator stops below the legend row
    ax.axvline(1.5, ymax=0.78, color="black", linestyle="--", linewidth=0.7, alpha=0.7)
    ax.set_xticks(xs)
    ax.set_xticklabels([E10_LABELS[k] for k in E10_BARS], rotation=45, ha="right",
                       rotation_mode="anchor", fontsize=TICK_SIZE)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Volume ratio", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("a", "Framework vs. sched."), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax)
    panel_legend(ax, handles=model_legend_handles(), loc="upper center", ncol=2,
                 handlelength=1.5, handleheight=1.0, columnspacing=0.6)

    # (b) scheduler gain per family: EAF inside the framework over Harvest
    ax = axes[1]
    xs = np.arange(len(fam))
    ymax = 1.4
    for j, m in enumerate(MODELS):
        v = fam[m].to_numpy()
        ax.bar(xs + (j - 0.5) * w, v, width=w, color=BAR_COLOR["EAF"][m],
               hatch=MODEL_HATCH[m], edgecolor="black", linewidth=0.45)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([FAMILY_LABELS.get(k, k) for k in fam.index],
                       rotation=90, fontsize=TICK_SIZE)
    ax.set_ylim(0.85, ymax)
    ax.set_ylabel("EAF / Harvest", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("b", "Scheduler gain"), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax)

    # (c) leave-one-out ablation
    ax = axes[2]
    s = D.rq2_summary[D.rq2_summary.template == "all"]
    xs = np.arange(len(ABLATIONS))
    ymax = 2.6
    tallest = max(s[s.ablation.isin(ABLATIONS)].volume_ratio_geomean)
    for j, m in enumerate(MODELS):
        v = np.array([s[(s.model == m) & (s.ablation == a)].volume_ratio_geomean.iloc[0]
                      for a in ABLATIONS])
        bars = ax.bar(xs + (j - 0.5) * w, v, width=w, color=BAR_COLOR["Harvest"][m],
                      hatch=MODEL_HATCH[m], edgecolor="black", linewidth=0.45)
        # label only the tallest bar; the others are all close to 1
        bar_labels(ax, bars, np.where(v == tallest, v, np.nan), ymax)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([ABLATION_LABELS[a] for a in ABLATIONS], rotation=45, ha="right",
                       rotation_mode="anchor", fontsize=TICK_SIZE)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Volume ratio", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("c", "Without component"), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax)

    panel_markers(fig, axes, [LOWER, HIGHER, HIGHER])
    match_axes_height(fig)
    save(fig, out / "fig_rq2_sources.pdf")
    return fam


# --------------------------------------------------------------------------
# Fig. 4  RQ3 - provisioning: magic terminals vs. volume, before/after pruning
# --------------------------------------------------------------------------
RQ3_LEVELS = {"ring": [1, 2, 4, 8, 16], "blocks4": [1, 2, 4, 8, 16], "dense4": [1, 2, 4]}
RQ3_MODEL_COLORS = {"instant": code_palette_deep[0], "cultivation": code_palette_deep[1]}


def rq3_curves(D: Data) -> pd.DataFrame:
    d = D.rq3.copy()
    d["lvl"] = d.level.astype(int)
    rows = []
    for tpl, levels in RQ3_LEVELS.items():
        for m in MODELS:
            s = d[(d.template == tpl) & (d.model == m)]
            # circuits present at every chosen level
            ok = s[s.lvl.isin(levels)].groupby("circuit").lvl.nunique()
            circuits = ok[ok == len(levels)].index
            s = s[s.circuit.isin(circuits)]
            # "max": every circuit's largest magic level (level 0 = all terminals)
            mx = s.loc[s.groupby("circuit").magic_terminals.idxmax()]
            for lab, sub in [(str(l), s[s.lvl == l]) for l in levels] + [("max", mx)]:
                rows.append((tpl, m, lab, len(sub), gmean(sub.large_pruned),
                             gmean(sub.large_initial), gmean(sub.direct_over_large_pruned),
                             float(sub.magic_terminals.median())))
    return pd.DataFrame(rows, columns=["template", "model", "level", "n", "pruned",
                                       "unpruned", "direct_over_large", "m_median"])


def fig_provisioning(D: Data, out: Path) -> pd.DataFrame:
    c = rq3_curves(D)
    fig, axes = row_figure(3, sharey=True)
    for i, (ax, tpl) in enumerate(zip(axes, RQ3_LEVELS)):
        for m in MODELS:
            s = c[(c.template == tpl) & (c.model == m)]
            x = np.arange(len(s))
            # color = magic-state model, solid = pruned, dashed = unpruned
            ax.plot(x, s.pruned, color=RQ3_MODEL_COLORS[m], marker="o", linestyle="-",
                    label=f"{MODEL_LABELS[m]}, pruned")
            ax.plot(x, s.unpruned, color=RQ3_MODEL_COLORS[m], marker="s", markerfacecolor="white",
                    linestyle="--", label=f"{MODEL_LABELS[m]}, unpruned")
            labels = list(s.level)
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, fontsize=TICK_SIZE)
        ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
        n = int(c[(c.template == tpl)].n.min())
        ax.set_title(panel_title(chr(97 + i), f"{TEMPLATE_LABELS[tpl]} ({n} circuits)"),
                     fontsize=TITLE_SIZE, loc="left", pad=3)
        ax.set_ylim(0, 2.9)   # room for the four-entry legend above the curves
        ax.set_yticks([0, 0.5, 1.0, 1.5, 2.0, 2.5])
        style_axis(ax, "both")
    for ax in axes:   # every panel gets its own y-axis title
        ax.set_ylabel("Volume ratio", fontsize=LABEL_SIZE, labelpad=2)
    axes[1].set_xlabel("# magic patches", fontsize=LABEL_SIZE)
    h, l = axes[0].get_legend_handles_labels()
    panel_legend(axes[0], h, l, loc="upper right", handlelength=1.5, labelspacing=0.15)
    panel_markers(fig, axes, LOWER)
    save(fig, out / "fig_rq3_provisioning.pdf")
    return c


# --------------------------------------------------------------------------
# Fig. 5  RQ4 - resource-aware vs. oblivious under different supply models
# --------------------------------------------------------------------------
RQ4_LEVELS = [1, 2, 4, 8, 16, 32]
RQ4_MODELS = [("dist4", r"Distillation, $\mu=4$"), ("dist10", r"Distillation, $\mu=10$"),
              ("cultivation", "Cultivation")]


def rq4_curves(D: Data) -> pd.DataFrame:
    d = D.rq4[D.rq4.level.isin(RQ4_LEVELS)]
    rows = []
    for model, _ in RQ4_MODELS + [("lognormal", ""), ("multiplexed", ""), ("instant", "")]:
        s = d[d.model == model]
        both = None
        for mode in ["aware", "oblivious"]:
            ok = s[s["mode"] == mode].groupby("circuit")["level"].nunique()
            cs = set(ok[ok == len(RQ4_LEVELS)].index)
            both = cs if both is None else (both & cs if cs else both)
        s = s[s.circuit.isin(both)]
        for mode in ["aware", "oblivious"]:
            for lvl in RQ4_LEVELS:
                sub = s[(s["mode"] == mode) & (s.level == lvl)]
                if sub.empty:
                    continue
                rows.append((model, mode, lvl, len(sub), gmean(sub.T_over_cp),
                             gmean(np.maximum(sub.bound_over_cp, 1.0))))
    return pd.DataFrame(rows, columns=["model", "mode", "level", "n", "T_over_cp", "lb_over_cp"])


def supply_rate_sweep(ne: Path, rq: Path) -> pd.DataFrame:
    """PureMagic/Harvest volume vs. mean cultivation delay (47-circuit subset).
    Means 1-8 from E14, means 10 and PureMagic's published rate from rq_cult_sweep."""
    e14 = pd.read_csv(ne / "E14_cultivation_sensitivity" / "e14_table.csv")
    rows = [(float(r.cultivation_mean), float(r.vol_geomean), int(r.vol_n)) for r in e14.itertuples()]
    cs = pd.read_csv(rq / "rq_cult_sweep" / "summary.csv")
    cs = cs[(cs.scope == "per_delay") & (cs.mean_delay > 8.5)]
    rows += [(float(r.mean_delay), float(r.pm_over_harvest_volume), int(r.n_shared)) for r in cs.itertuples()]
    return pd.DataFrame(rows, columns=["mean", "pm_over_harvest", "n"]).sort_values("mean")


def fig_supply(D: Data, ne: Path, rq: Path, out: Path) -> pd.DataFrame:
    c = rq4_curves(D)
    sw = supply_rate_sweep(ne, rq)
    fig, axes = row_figure(3)
    ax0, ax1, ax2 = axes
    ax1.sharey(ax0)
    panels = [(ax0, "dist4", r"Distillation, $\mu=4$"), (ax1, "cultivation", "Cultivation")]
    for i, (ax, model, title) in enumerate(panels):
        a = c[(c.model == model) & (c["mode"] == "aware")]
        o = c[(c.model == model) & (c["mode"] == "oblivious")]
        ax.plot(a.level, a.lb_over_cp, color="black", linestyle=":", linewidth=1.2,
                label="Lower bound", zorder=5)
        ax.plot(o.level, o.T_over_cp, color=OBLIVIOUS_COLOR, marker="s",
                linestyle="--", label="Magic-agnostic (replayed)")
        ax.plot(a.level, a.T_over_cp, color=COMPILER_COLORS["Harvest"], marker="o",
                label="Harvest (resource-aware)")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.xaxis.set_major_locator(mtick.FixedLocator(RQ4_LEVELS))
        ax.xaxis.set_major_formatter(mtick.FixedFormatter([str(l) for l in RQ4_LEVELS]))
        ax.xaxis.set_minor_locator(mtick.NullLocator())
        ax.yaxis.set_major_locator(mtick.FixedLocator([1, 3, 10, 30]))
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda y, _: f"{y:g}"))
        ax.yaxis.set_minor_formatter(mtick.NullFormatter())
        ax.set_xlabel("# magic patches", fontsize=LABEL_SIZE)
        ax.set_ylabel(r"Timesteps / depth", fontsize=LABEL_SIZE, labelpad=2)
        ax.set_title(panel_title(chr(97 + i), title), fontsize=TITLE_SIZE,
                     loc="left", pad=3)
        style_axis(ax, "both")
    ax0.set_ylim(top=200)   # shared y: room for the legend above the curves
    h, l = ax0.get_legend_handles_labels()
    panel_legend(ax0, h[::-1], l[::-1], loc="upper right", handlelength=1.8,
                 labelspacing=0.3)

    # (c) supply-rate sweep against PureMagic
    ax = ax2
    ax.axhspan(1.0, 1.45, color=BAR_COLOR["Harvest"]["cultivation"], alpha=0.35, linewidth=0)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    ax.plot(sw["mean"], sw.pm_over_harvest, color=COMPILER_COLORS["PureMagic"], marker="o")
    ax.axvline(3, color="0.4", linestyle=":", linewidth=1.0)
    ax.text(3.15, 1.42, r"default $\bar{d}=3$", fontsize=LEGEND_SIZE, va="top", color="0.3")
    ax.text(26, 1.03, "Harvest lower", fontsize=LEGEND_SIZE, va="bottom", ha="right", color="0.25")
    ax.text(1.05, 0.97, "PureMagic lower", fontsize=LEGEND_SIZE, va="top", color="0.25")
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(mtick.FixedLocator([1, 2, 3, 5, 10, 26]))
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:g}"))
    ax.xaxis.set_minor_locator(mtick.NullLocator())
    ax.set_ylim(0.65, 1.45)
    ax.set_ylabel("PureMagic / Harvest", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_xlabel("Mean cultivation delay", fontsize=LABEL_SIZE)
    ax.set_title(panel_title("c", "Supply rate"), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax, "both")

    panel_markers(fig, axes, [LOWER, LOWER, HIGHER])
    save(fig, out / "fig_rq4_supply.pdf")
    return c


# --------------------------------------------------------------------------
# Fig. 6  RQ5 - compile time
# --------------------------------------------------------------------------
COMPILE_MIN_BIN = 3   # bins with fewer circuits are left out


def fig_compile(D: Data, out: Path) -> None:
    fig, axes = row_figure(2)
    ax = axes[0]
    # Same circuits for every compiler (EAF fails on the largest ones), so each line
    # averages the same set; geometric mean per half-decade bin of |O|, no model fit.
    r = D.ratios("instant")
    r = r[r.compile_time_s > 0]
    k = r.groupby("circuit").compiler.nunique()
    r = r[r.circuit.isin(k[k == len(COMPILERS)].index)]
    n_common = r.circuit.nunique()
    edges = 10 ** np.arange(0, 5.01, 0.5)
    r = r.assign(bin=pd.cut(r.ops, edges, right=False))
    rows = []
    for c in COMPILERS:
        g = (r[r.compiler == c].groupby("bin", observed=True)
             .agg(n=("circuit", "size"), ops=("ops", gmean), t=("compile_time_s", gmean),
                  t_min=("compile_time_s", "min"), t_max=("compile_time_s", "max")))
        g = g[g.n >= COMPILE_MIN_BIN]
        ax.plot(g.ops, g.t, color=COMPILER_COLORS[c], marker=COMPILER_MARKERS[c],
                markersize=5, linewidth=1.6, label=c, zorder=4 if c == "Harvest" else 3)
        rows.append(g.assign(compiler=c).reset_index())
    pd.concat(rows).to_csv(out / "fig_rq5_compile_values.csv", index=False)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Pauli rotations $|O|$", fontsize=LABEL_SIZE, labelpad=1)
    ax.set_ylabel("Compile time (s)", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("a", f"Compile time (free model, {n_common} circuits)"),
                 fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax, "both")
    panel_legend(ax, loc="upper left", ncol=3, handlelength=1.8)

    # (b) Harvest phase breakdown by circuit size
    ax = axes[1]
    d = D.rq1[(D.rq1.model == "instant") & (D.rq1.status == "ok")].copy()
    bins = [0, 300, 1000, 3000, 1e9]
    labs = ["<300", "300-1k", "1k-3k", ">3k"]
    d["bin"] = pd.cut(d.ops, bins=bins, labels=labs)
    phases = [("t_place_s", "Placement"), ("t_schedule_s", "Scheduling"),
              ("t_prune_s", "Pruning"), ("t_validate_s", "Validation")]
    g = d.groupby("bin", observed=False)[[p for p, _ in phases]].sum()
    share = g.div(g.sum(axis=1), axis=0) * 100
    bottom = np.zeros(len(share))
    xs = np.arange(len(share))
    for k, (p, lab) in enumerate(phases):
        ax.bar(xs, share[p].to_numpy(), bottom=bottom, width=0.62, color=PHASE_COLORS[k],
               hatch=code_hatches[k], edgecolor="black", linewidth=0.45, label=lab)
        bottom += share[p].to_numpy()
    ax.set_xticks(xs)
    ax.set_xticklabels(labs, fontsize=TICK_SIZE)
    ax.set_ylim(0, 170)   # headroom above 100 % for the legend
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel(r"Pauli rotations $|O|$", fontsize=LABEL_SIZE, labelpad=1)
    ax.set_ylabel("Share of time (%)", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("b", "Harvest phases"), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax)
    panel_legend(ax, loc="upper center", ncol=2, handlelength=1.3, columnspacing=0.6,
                 labelspacing=0.2)
    # a phase share has no better direction, so (b) gets no marker
    panel_markers(fig, axes, [LOWER, ""])
    match_axes_height(fig)
    save(fig, out / "fig_rq5_compile.pdf")


# --------------------------------------------------------------------------
# LaTeX tables
# --------------------------------------------------------------------------
def f2(x, nd=2):
    return "--" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def tab_sota(D: Data, out: Path) -> pd.DataFrame:
    rows = []
    for c in COMPILERS:
        row = {"compiler": c}
        for m in MODELS:
            r = D.ratios(m)
            rc = r[r.compiler == c]
            allc = D.pc[(D.pc.model == m) & (D.pc.compiler == c)]
            v = rc.volume_ratio.dropna()
            row.update({
                f"{m}_vol": gmean(v), f"{m}_T": gmean(rc.T_ratio), f"{m}_A": gmean(rc.area_ratio),
                f"{m}_Tcp": gmean(rc.T_over_cp), f"{m}_patches": float(rc.area.median()),
                f"{m}_W": int((v > 1.01).sum()), f"{m}_Ti": int(((v >= 0.99) & (v <= 1.01)).sum()),
                f"{m}_L": int((v < 0.99).sum()), f"{m}_n": len(v),
                f"{m}_Tfaster": int((rc.T_ratio < 0.99).sum()),
                f"{m}_ct": gmean(rc.compile_time_s),
                f"{m}_done": int(allc.completed.sum()) if "completed" in allc else len(allc),
            })
        rows.append(row)
    t = pd.DataFrame(rows)
    nI, nC = int(t.instant_n.iloc[0]), int(t.cultivation_n.iloc[0])
    lines = [
        r"% Generated by make_eval_plots.py from rq/rq1_view/rq1_per_circuit.csv",
        r"\begin{table}[t]",
        r"\centering\small",
        rf"\caption{{Comparison with state-of-the-art lattice-surgery compilers on the {nI} (instant) / {nC} (cultivation) circuits Harvest has completed (a baseline missing a circuit is left out of that circuit's ratios). "
        r"Ratios are geometric means of compiler\,/\,Harvest per circuit (lower is better, Harvest $=1$). "
        r"$T/T_{cp}$: timesteps over the critical-path length. W/T/L: circuits on which Harvest has lower / equal ($\pm$1\%) / higher volume. "
        r"$T{<}$H: circuits with fewer timesteps than Harvest. Compile time is the geometric mean in seconds; Harvest's includes all four layout templates.}",
        r"\label{tab:sota}",
        r"\setlength{\tabcolsep}{3.2pt}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{l rrrrrrr rrrrrrr}",
        r"\toprule",
        r" & \multicolumn{7}{c}{Instant magic states} & \multicolumn{7}{c}{Cultivated magic states} \\",
        r"\cmidrule(lr){2-8}\cmidrule(lr){9-15}",
        r"Compiler & Vol. & $T$ & Area & $T/T_{cp}$ & W/T/L & $T{<}$H & Time [s] & Vol. & $T$ & Area & $T/T_{cp}$ & W/T/L & $T{<}$H & Time [s] \\",
        r"\midrule",
    ]
    for _, r in t.iterrows():
        cells = [r.compiler]
        for m in MODELS:
            wtl = "--" if r.compiler == "Harvest" else f"{r[f'{m}_W']}/{r[f'{m}_Ti']}/{r[f'{m}_L']}"
            tf = "--" if r.compiler == "Harvest" else f"{r[f'{m}_Tfaster']}"
            vol = f2(r[f"{m}_vol"])
            if r.compiler == "Harvest":
                vol = r"\textbf{1.00}"
            cells += [vol, f2(r[f"{m}_T"]), f2(r[f"{m}_A"]), f2(r[f"{m}_Tcp"]), wtl, tf,
                      f2(r[f"{m}_ct"])]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    (out / "tab_rq1_sota.tex").write_text("\n".join(lines) + "\n")
    print(f"Saved {out / 'tab_rq1_sota.tex'}")
    return t


def tab_contributions(D: Data, tr: pd.DataFrame, out: Path) -> None:
    s = D.rq2_summary[D.rq2_summary.template == "all"]
    lines = [
        r"% Generated by make_eval_plots.py from rq/rq2/rq2_ablation_summary.csv and rq/rq1/rq1.csv (auto_volumes)",
        r"\begin{table}[t]",
        r"\centering\small",
        r"\caption{Where Harvest's advantage comes from. Top: volume of Harvest on a single fixed layout template, relative to Harvest's per-circuit choice (Auto), and PureMagic's volume relative to that template ($>1$: Harvest better). "
        r"Bottom: leave-one-out ablation, volume and timesteps of the variant relative to full Harvest (geometric mean, 10th--90th percentile, share of runs that get worse).}",
        r"\label{tab:contributions}",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{l rr rr}",
        r"\toprule",
        r" & \multicolumn{2}{c}{Instant} & \multicolumn{2}{c}{Cultivation} \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"Layout & Vol./Auto & PureMagic/Vol. & Vol./Auto & PureMagic/Vol. \\",
        r"\midrule",
    ]
    for tpl in TEMPLATES + ["auto"]:
        cells = [TEMPLATE_LABELS[tpl]]
        for m in MODELS:
            x = tr[(tr.model == m) & (tr.layout == tpl)].iloc[0]
            cells += [f2(x.vol_over_auto), f2(x.pm_over_layout)]
        lines.append(" & ".join(cells) + r" \\")
    lines += [
        r"\midrule",
        r"Without & Vol. [p10, p90] & $T$ / worse & Vol. [p10, p90] & $T$ / worse \\",
        r"\midrule",
    ]
    for a in ABLATIONS:
        cells = [ABLATION_LABELS[a]]
        for m in MODELS:
            x = s[(s.model == m) & (s.ablation == a)].iloc[0]
            cells += [f"{x.volume_ratio_geomean:.2f} [{x.p10:.2f}, {x.p90:.2f}]",
                      f"{x.T_ratio_geomean:.2f} / {100 * x.share_worse:.0f}\\%"]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (out / "tab_rq2_contributions.tex").write_text("\n".join(lines) + "\n")
    print(f"Saved {out / 'tab_rq2_contributions.tex'}")


def tab_models(D: Data, c4: pd.DataFrame, out: Path) -> None:
    p = D.rq4_plug.set_index("model")
    o = D.rq4_obl.set_index("model")
    names = {"instant": "Instant", "dist4": r"Distillation $\mu{=}4$", "dist10": r"Distillation $\mu{=}10$",
             "cultivation": "Cultivation (exp.)", "lognormal": "Cultivation (log-normal)$^\\dagger$",
             "multiplexed": "Multiplexed cultivation$^\\dagger$"}
    lines = [
        r"% Generated by make_eval_plots.py from rq/rq4/*.csv",
        r"\begin{table}[t]",
        r"\centering\small",
        r"\caption{Magic-state models behind the \texttt{advance}/\texttt{avail}/\texttt{consume} interface. "
        r"LoC: lines implementing the interface; no model required changes to the scheduler or validator. "
        r"All schedules pass (V1)--(V4) before and after pruning. Oblivious: the instant-model schedule replayed under the model; "
        r"it violates (V4) without stalls, and the ratio gives its stall-inserted timesteps over Harvest's (geometric mean / max). $^\dagger$New in this paper.}",
        r"\label{tab:models}",
        r"\begin{tabular}{l r c r r r}",
        r"\toprule",
        r"Model & LoC & Restr.\ stable & Schedules valid & Oblivious invalid & Oblivious / aware \\",
        r"\midrule",
    ]
    for m in ["instant", "dist4", "dist10", "cultivation", "lognormal", "multiplexed"]:
        x = p.loc[m]
        valid = f"{int(x.validated_post_pass)}/{int(x.schedules)}"
        if m in o.index and m != "instant":
            ob = o.loc[m]
            inv = f"{int(ob.invalid_unmodified)}/{int(ob.schedules)}"
            ratio = f"{ob.oblivious_over_aware_geomean:.2f} / {ob.oblivious_over_aware_max:.1f}"
        else:
            inv, ratio = "--", "--"
        lines.append(" & ".join([names[m], str(int(x.interface_loc)),
                                 r"\checkmark" if bool(x.restriction_stable) else "",
                                 valid, inv, ratio]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (out / "tab_rq4_models.tex").write_text("\n".join(lines) + "\n")
    print(f"Saved {out / 'tab_rq4_models.tex'}")


def tab_validity(D: Data, out: Path) -> None:
    c = D.rq5_census
    c = c[c.experiment != "all"]
    f = D.rq5_faults
    total = int(c.schedules.sum())
    checked = int(c.checked_post.sum())
    viol = int(c.violations.sum())
    kinds = {
        "skip_dep": "Schedule before a predecessor", "no_defer": "Commit conflicting routes",
        "reuse_terminal": "Reuse a magic terminal", "early_consume": "Consume a state before it is ready",
        "drop_y_port": r"Drop a port of a $Y$ factor", "prune_used": "Prune a used tile",
        "drop_dependency": "Drop a dependency", "overlap_route": "Overlap two routes",
        "disconnect_route": "Disconnect a route", "unavailable_state": "Use an unavailable state",
    }
    lines = [
        r"% Generated by make_eval_plots.py from rq/rq5/rq5_census.csv and rq/rq5/rq5_faults.csv",
        rf"% TODO: census lists {total} schedules but only {checked} were checked (difference: RQ4 rows) -- confirm these are the oblivious replays.",
        r"% TODO: fault descriptions are inferred from the fault names -- check against the injector.",
        r"% NOTE: the per-rule labels in rq5_faults.csv look swapped (V2<->V3); rules are omitted until checked.",
        r"\begin{table}[t]",
        r"\centering\small",
        rf"\caption{{Validator results. {checked:,} Harvest schedules from RQ1--RQ5 were checked against (V1)--(V4) before and after pruning, with {viol} violations. "
        r"Below: injected scheduler faults and random schedule corruptions; applicable runs are those in which the fault changes the schedule.}",
        r"\label{tab:validity}",
        r"\begin{tabular}{ll rr rr}",
        r"\toprule",
        r" & & \multicolumn{2}{c}{Instant} & \multicolumn{2}{c}{Cultivation} \\",
        r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}",
        r"Study & Fault & Applicable & Caught & Applicable & Caught \\",
        r"\midrule",
    ]
    for study, label in [("scheduler", "Scheduler bug"), ("corrupt", "Corruption")]:
        first = True
        for k in f[f.study == study].kind.unique():
            cells = [label if first else "", kinds.get(k, k.replace("_", r"\_"))]
            first = False
            for m in MODELS:
                x = f[(f.study == study) & (f.kind == k) & (f.model == m)]
                if x.empty or int(x.applicable.iloc[0]) == 0:
                    cells += ["0", "n/a"]
                else:
                    x = x.iloc[0]
                    cells += [str(int(x.applicable)), f"{100 * x.caught_share:.0f}\\%"]
            lines.append(" & ".join(cells) + r" \\")
        if study == "scheduler":
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (out / "tab_rq5_validity.tex").write_text("\n".join(lines) + "\n")
    print(f"Saved {out / 'tab_rq5_validity.tex'}")



# --------------------------------------------------------------------------
# Figure wrappers: one .tex per figure, to \input{figures/evaluation/<name>}
# --------------------------------------------------------------------------
FIGURE_TEX = {
    "fig_rq1_family_cultivation": (
        r"""\textbf{Results per circuit family} (RQ1), cultivated magic states. Geometric means per family for \textbf{(a)}~normalized space--time volume, \textbf{(b)}~timesteps over the circuit depth, and \textbf{(c)}~patches per logical qubit. Families with fewer than three circuits are merged into \emph{Other}; numbers in parentheses give the circuits per family. The solid line marks the lower bound. Clipped bars are labeled with their value.""",
        "fig:rq1-family"),
    "fig_rq1_family_instant": (
        r"""\textbf{Results per circuit family} (RQ1), instant magic states. Geometric means per family for \textbf{(a)}~normalized space--time volume, \textbf{(b)}~timesteps over the circuit depth, and \textbf{(c)}~patches per logical qubit. Families with fewer than three circuits are merged into \emph{Other}; numbers in parentheses give the circuits per family. The solid line marks the lower bound. Clipped bars are labeled with their value.""",
        "fig:rq1-family-instant"),
    "fig_rq1_per_circuit": (
        r"""\textbf{Per-circuit volume relative to Harvest} (RQ1) under \textbf{(a)}~instant and \textbf{(b)}~cultivated magic states. Each line sorts one compiler's volume ratios; values above one favor Harvest. Labels give the number of circuits on which Harvest has the lower volume.""",
        "fig:rq1-per-circuit"),
    "fig_rq1_size_cultivation": (
        r"""\textbf{Scaling with circuit size} (RQ1), cultivated magic states. Circuits are sorted by the number of logical qubits $n$ (tick labels). \textbf{(a)}~Normalized space--time volume, \textbf{(b)}~timesteps over the circuit depth, and \textbf{(c)}~patches per logical qubit. Lines show the geometric mean over nine neighboring circuits. The solid black line marks the lower bound.""",
        "fig:rq1-size"),
    "fig_rq1_size_instant": (
        r"""\textbf{Scaling with circuit size} (RQ1), instant magic states. Circuits are sorted by the number of logical qubits $n$ (tick labels). \textbf{(a)}~Normalized space--time volume, \textbf{(b)}~timesteps over the circuit depth, and \textbf{(c)}~patches per logical qubit. Lines show the geometric mean over nine neighboring circuits. The solid black line marks the lower bound.""",
        "fig:rq1-size-instant"),
    "fig_rq1_sota": (
        r"""\textbf{Comparison with the state of the art} (RQ1). Geometric means over all circuits under instant (dark) and cultivated (light) magic states, normalized to circuit size $n$ and circuit depth (the longest chain of dependent rotations, i.e., the fewest timesteps any schedule needs). \textbf{(a)}~Space--time volume per data patch and depth step. \textbf{(b)}~Timesteps over the depth. \textbf{(c)}~Patches per logical qubit. The solid line marks the respective lower bound: $n$ data patches for depth steps. Bars above the axis limit are clipped and labeled with their value.""",
        "fig:rq1-sota"),
    "fig_rq2_sources": (
        r"""\textbf{Sources of the improvement} (RQ2), 47 circuits. \textbf{(a)}~Volume of EAF and Harvest on the blocks-of-four template and with the per-circuit template choice (Auto), all with pruning, relative to Harvest (Auto). \textbf{(b)}~Volume of EAF over Harvest when both run inside Harvest's framework (Auto, pruning), per circuit family; \emph{Other} merges families with one circuit. \textbf{(c)}~Leave-one-out ablation: volume of Harvest without one component, relative to full Harvest.""",
        "fig:rq2-sources"),
    "fig_rq2_contributions": (
        r"""\textbf{Sources of the improvement} (RQ2). \textbf{(a)}~Volume of Harvest restricted to a single layout template, and of PureMagic, relative to Harvest's per-circuit template choice (Auto). \textbf{(b)}~Leave-one-out ablation: volume of Harvest without one component, relative to full Harvest. \textbf{(c)}~Timestep reduction from negotiated-congestion routing per run, sorted, for three templates.""",
        "fig:rq2-contributions"),
    "fig_rq3_provisioning": (
        r"""\textbf{Layout provisioning} (RQ3). Space--time volume as the working layout provides more magic-state patches, relative to the pruned volume with a single magic-state patch, on the \textbf{(a)}~ring, \textbf{(b)}~blocks-of-four, and \textbf{(c)}~dense template. Filled markers show the reported (pruned) volume, open markers the volume of the working layout before pruning. \emph{max} uses every magic-state patch of the template.""",
        "fig:rq3-provisioning"),
    "fig_rq4_supply": (
        r"""\textbf{Magic-state supply} (RQ4). Timesteps over the circuit depth as the number of magic-state patches grows under \textbf{(a)}~distillation with $\mu=4$ and \textbf{(b)}~cultivation. Harvest schedules against the supply model; the magic-agnostic schedule is computed for instant supply and replayed with stalls. The dotted line is the lower bound $\max(\text{depth}, \text{supply})$. \textbf{(c)}~Volume of PureMagic over Harvest as the mean cultivation delay (in timesteps) grows; values above one favor Harvest.""",
        "fig:rq4-supply"),
    "fig_rq5_compile": (
        r"""\textbf{Compilation cost} (RQ5). \textbf{(a)}~Compile time under instant magic states over the number of Pauli rotations: geometric mean per half-decade of $|O|$, on the circuits every compiler finished (EAF fails on the six largest, $|O| > 20$k). Harvest's time includes all four layout templates; the baselines' times are for their best variant only. \textbf{(b)}~Share of Harvest's compile time per stage, by circuit size.""",
        "fig:rq5-compile"),
}


def write_figure_tex(out: Path, tex_dir: str = "figures/evaluation") -> None:
    for name, (caption, label) in FIGURE_TEX.items():
        body = "\n".join([
            r"\begin{figure}[t]",
            r"  \centering",
            rf"  \includegraphics[width=\linewidth]{{{tex_dir}/{name}.pdf}}",
            rf"  \caption{{{caption}}}",
            rf"  \label{{{label}}}",
            r"\end{figure}",
        ]) + "\n"
        (out / f"{name}.tex").write_text(body)
        print(f"Saved {out / (name + '.tex')}")


# --------------------------------------------------------------------------
def main(rq: Path, out: Path, ne: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    D = Data(rq)
    fig_sota(D, out)
    fig_sota_distribution(D, out)
    sc = fig_size(D, out)
    fc = fig_family(D, out)
    tr = fig_contributions(D, out)
    fam = fig_sources(D, ne, rq, out)
    c3 = fig_provisioning(D, out)
    c4 = fig_supply(D, ne, rq, out)
    fig_compile(D, out)
    t1 = tab_sota(D, out)
    # tab_contributions(D, tr, out)  # dropped from the paper; the figure carries RQ2
    tab_models(D, c4, out)
    tab_validity(D, out)
    write_figure_tex(out)
    # numbers used in the text
    with pd.option_context("display.width", 200, "display.max_columns", 40):
        (out / "numbers_for_text.txt").write_text(
            "RQ1 table\n" + t1.round(3).to_string() + "\n\nRQ1 by size\n" + sc.round(3).to_string() + "\n\nRQ1 by family\n" + fc.round(3).to_string() + "\n\nRQ2 layout\n" + tr.round(3).to_string()
            + "\n\nRQ3 curves\n" + c3.round(3).to_string() + "\n\nRQ4 curves\n" + c4.round(3).to_string()
            + "\n\nRQ2 scheduler gain per family\n" + fam.round(3).to_string()
            + "\n\nRQ3 supply-rate sweep\n" + supply_rate_sweep(ne, rq).round(3).to_string()
            + "\n\nRQ5 scaling fit\n" + D.rq5_fit.to_string() + "\n")


if __name__ == "__main__":
    rq_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("rq")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("figures/evaluation")
    ne_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else rq_dir.parent / "new_experiments"
    main(rq_dir, out_dir, ne_dir)
