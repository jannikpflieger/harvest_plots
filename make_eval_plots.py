"""Evaluation figures and LaTeX tables for Harvest (Section 7).

Data: ONLY the `rq/` results directory (rq1_view, rq1, rq2, rq3, rq4, rq5).
Style: follows plot_code/single_column_paper_plots.py and the combined
row scripts (1 x N panels, page width, pastel bars with hatches, shared
legend, bold "(a)" panel titles, blue "lower/higher is better" marker).

Usage:  python make_eval_plots.py /path/to/rq  figures/evaluation

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

plt.rcParams.update({
    "font.family": "serif",
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
_BASE_WIDTH = 7.2


def L(x: float) -> float:
    """Scale a left margin chosen for a 7.2in figure to the current width."""
    return x * _BASE_WIDTH / PAPER_WIDTH


def R(x: float) -> float:
    """Scale a right margin chosen for a 7.2in figure to the current width."""
    return 1 - (1 - x) * _BASE_WIDTH / PAPER_WIDTH
LABEL_SIZE = 8.5
TICK_SIZE = 7.5
TITLE_SIZE = 9.0
LEGEND_SIZE = 7.2
VALUE_SIZE = 5.8

# Order used in every plot and table: baselines first, Harvest last (rightmost).
COMPILERS = ["Litinski", "O3LS", "EAF", "PureMagic", "Harvest"]
BASELINES = COMPILERS[:-1]
SOTA_ORDER = COMPILERS
MODELS = ["instant", "cultivation"]
MODEL_LABELS = {"instant": "Instant", "cultivation": "Cultivation"}

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
TEMPLATE_COLORS = {"ring": code_palette_deep[5], "blocks4": code_palette_deep[8],
                   "dense4": code_palette_deep[9]}
OBLIVIOUS_COLOR = code_palette_deep[7]
PHASE_COLORS = [code_palette[5], code_palette[6], code_palette[7], code_palette[8]]
MODEL_HATCH = {"instant": code_hatches[0], "cultivation": code_hatches[1]}


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


def better_marker(fig, text: str, x: float = 0.5, ha: str = "center") -> None:
    fig.text(x, 0.99, text, ha=ha, va="top", fontsize=LEGEND_SIZE,
             fontweight="bold", color="blue")


def style_axis(ax, grid_axis: str = "y") -> None:
    ax.tick_params(axis="both", labelsize=TICK_SIZE, pad=1.5)
    ax.grid(axis=grid_axis, linestyle="--", linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)


def save(fig, path: Path) -> None:
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
                fmt.format(v), ha="center", va="bottom", fontsize=VALUE_SIZE - 0.3,
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
        ("vol_per_qubit_cp", "Space-time volume", r"Volume / $(n \cdot T_{cp})$", 9.0,
         r"solid line: $n$ data patches for $T_{cp}$"),
        ("T_over_cp", "Timesteps", r"Timesteps / $T_{cp}$", 3.0,
         r"solid line: critical path $T_{cp}$"),
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

    fig, axes = plt.subplots(1, 3, figsize=(PAPER_WIDTH, 2.35))
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
        ax.set_ylim(0, clip * 1.45)
        ax.set_ylabel(ylabel, fontsize=LABEL_SIZE - 0.5, labelpad=1)
        ax.set_title(panel_title(chr(97 + i), title), fontsize=TITLE_SIZE, loc="left", pad=3)
        style_axis(ax)
    fig.legend(handles=model_legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False,
               fontsize=LEGEND_SIZE, handlelength=1.4, columnspacing=1.0)
    better_marker(fig, r"Lower is better $\downarrow$")
    fig.subplots_adjust(left=L(0.065), right=R(0.995), bottom=0.30, top=0.85, wspace=0.30)
    save(fig, out / "fig_rq1_sota.pdf")
    # numbers for the text
    rows = [(m, c, *[vals[m][c][k] for k, *_ in metrics]) for m in MODELS for c in SOTA_ORDER]
    pd.DataFrame(rows, columns=["model", "compiler"] + [k for k, *_ in metrics]).round(3) \
        .to_csv(out / "fig_rq1_sota_values.csv", index=False)


# --------------------------------------------------------------------------
# Fig. 2  RQ1 - per-circuit distribution of the volume ratio
# --------------------------------------------------------------------------
def fig_sota_distribution(D: Data, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(PAPER_WIDTH, 2.35), sharey=True)
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
            ax.text(1.0, v[-1], f" {wins}/{len(v)}", fontsize=VALUE_SIZE,
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
    axes[0].set_ylabel("Volume / Harvest volume", fontsize=LABEL_SIZE, labelpad=2)
    fig.supxlabel("Fraction of circuits", fontsize=LABEL_SIZE, y=0.14)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, frameon=False,
               fontsize=LEGEND_SIZE, handlelength=1.4, columnspacing=1.0)
    better_marker(fig, r"Above 1: Harvest better $\uparrow$")
    fig.subplots_adjust(left=L(0.09), right=R(0.97), bottom=0.31, top=0.85, wspace=0.08)
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
        ("vol_per_qubit_cp", "Space-time volume", r"Volume / $(n \cdot T_{cp})$",
         [1, 2, 5, 10, 20, 50]),
        ("T_over_cp", "Timesteps", r"Timesteps / $T_{cp}$",
         [1, 1.5, 2, 3, 5, 10, 20]),
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
        fig, axes = plt.subplots(1, 3, figsize=(PAPER_WIDTH, 2.45))
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
            ax.set_xticklabels([str(int(nq[k])) for k in ticks], fontsize=TICK_SIZE - 0.5)
            ax.set_xlim(-1, len(order))
            ax.set_ylabel(ylabel, fontsize=LABEL_SIZE - 0.5, labelpad=1)
            ax.set_title(panel_title(chr(97 + i), title), fontsize=TITLE_SIZE, loc="left", pad=3)
            style_axis(ax, "both")
        fig.supxlabel("Logical qubits $n$",
                      fontsize=LABEL_SIZE, y=0.12)
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=5, frameon=False,
                   fontsize=LEGEND_SIZE, handlelength=1.8, columnspacing=1.0)
        better_marker(fig, r"Lower is better $\downarrow$")
        fig.subplots_adjust(left=L(0.07), right=R(0.995), bottom=0.32, top=0.86, wspace=0.30)
        save(fig, out / f"fig_rq1_size_{model}.pdf")
    return pd.concat(all_curves)


# --------------------------------------------------------------------------
# Fig. 2c  RQ1 - per circuit family (volume, timesteps, patches per qubit)
# --------------------------------------------------------------------------
FAMILY_LABELS = {
    "qft": "QFT", "qaoa": "QAOA", "heisenberg_square": "Heisenberg", "ising": "Ising",
    "adder": "Adder", "dnn": "DNN", "knn": "kNN", "wstate": "W state",
    "multiplier": "Multiplier", "random": "Random", "swap_test": "Swap test",
    "vqe_uccsd": "VQE-UCCSD", "other": "Other",
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
        ("vol_per_qubit_cp", "Space-time volume", r"Vol. / $(n \cdot T_{cp})$", 10.0),
        ("T_over_cp", "Timesteps", r"Timesteps / $T_{cp}$", 3.0),
        ("area_per_qubit", "Patches per logical qubit", r"Patches / $n$", 7.0),
    ]
    all_g = []
    for model in MODELS:
        g, order = family_curves(D, model)
        all_g.append(g)
        fig, axes = plt.subplots(3, 1, figsize=(PAPER_WIDTH, 5.6), sharex=True)
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
                                ha="center", va="bottom", fontsize=VALUE_SIZE - 0.8)
            ax.axhline(1.0, color="black", linewidth=0.9)
            ax.set_ylim(0, clip * 1.32)
            ax.set_ylabel(ylabel, fontsize=LABEL_SIZE - 0.5, labelpad=1)
            ax.set_title(panel_title(chr(97 + i), title), fontsize=TITLE_SIZE, loc="left", pad=2)
            style_axis(ax)
        n = g[g.compiler == "Harvest"].set_index("fam").reindex(order).n
        axes[-1].set_xticks(xs)
        axes[-1].set_xticklabels([f"{FAMILY_LABELS.get(f, f)}\n({int(k)})" for f, k in zip(order, n)],
                                 fontsize=TICK_SIZE - 0.5)
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=5, frameon=False,
                   fontsize=LEGEND_SIZE, handlelength=1.4, columnspacing=1.0)
        better_marker(fig, r"Lower is better $\downarrow$")
        fig.subplots_adjust(left=L(0.075), right=R(0.995), bottom=0.12, top=0.93, hspace=0.32)
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
ABLATION_LABELS = {"-admission": "Better availability", "-pruning": "Pruning", "-priority": "Priority",
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
    fig, axes = plt.subplots(1, 3, figsize=(PAPER_WIDTH, 2.45),
                             gridspec_kw={"width_ratios": [1.05, 1.35, 0.95]})

    # (a) layout template
    ax = axes[0]
    order = TEMPLATES + ["auto", "PureMagic"]
    xs = np.arange(len(order))
    w = 0.38
    ymax = 2.3
    for j, m in enumerate(MODELS):
        v = np.array([tr[(tr.model == m) & (tr.layout == k)].vol_over_auto.iloc[0] for k in order])
        cols = [BAR_COLOR["PureMagic" if k == "PureMagic" else "Harvest"][m] for k in order]
        bars = ax.bar(xs + (j - 0.5) * w, v, width=w, color=cols,
                      hatch=MODEL_HATCH[m], edgecolor="black", linewidth=0.45)
        bar_labels(ax, bars, v, ymax)
    ax.axvline(len(TEMPLATES) + 0.5, color="black", linestyle="--", linewidth=0.7, alpha=0.7)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([TEMPLATE_LABELS[k] for k in order], rotation=35, ha="right",
                       rotation_mode="anchor", fontsize=TICK_SIZE - 0.5)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Geomean volume ratio", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("a", "Layout (vs. Auto)"), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax)

    # (b) leave-one-out ablation
    ax = axes[1]
    s = D.rq2_summary[D.rq2_summary.template == "all"]
    xs = np.arange(len(ABLATIONS))
    ymax = 2.3
    for j, m in enumerate(MODELS):
        v = np.array([s[(s.model == m) & (s.ablation == a)].volume_ratio_geomean.iloc[0]
                      for a in ABLATIONS])
        bars = ax.bar(xs + (j - 0.5) * w, v, width=w, color=BAR_COLOR["Harvest"][m],
                      hatch=MODEL_HATCH[m], edgecolor="black", linewidth=0.45)
        bar_labels(ax, bars, v, ymax)
    ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([ABLATION_LABELS[a] for a in ABLATIONS], rotation=35, ha="right",
                       rotation_mode="anchor", fontsize=TICK_SIZE - 0.5)
    ax.set_ylim(0, ymax)
    ax.set_title(panel_title("b", "Without component (vs. full)"), fontsize=TITLE_SIZE,
                 loc="left", pad=3)
    style_axis(ax)

    # (c) negotiation: per-run makespan reduction, sorted
    ax = axes[2]
    n = D.rq2_nego
    for k, tpl in enumerate(["ring", "blocks4", "dense4"]):
        for m, ls in [("instant", "-"), ("cultivation", "--")]:
            v = np.sort(n[(n.template == tpl) & (n.model == m)].makespan_reduction.to_numpy())[::-1] * 100
            frac = np.arange(1, len(v) + 1) / len(v)
            ax.plot(frac, v, color=TEMPLATE_COLORS[tpl], linestyle=ls, linewidth=1.2,
                    label=TEMPLATE_LABELS[tpl] if m == "instant" else None)
    ax.plot([], [], color="gray", linestyle="-", label="Instant")
    ax.plot([], [], color="gray", linestyle="--", label="Cultivation")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xlabel("Fraction of runs", fontsize=LABEL_SIZE - 0.5, labelpad=1)
    ax.set_ylabel("Timestep reduction (%)", fontsize=LABEL_SIZE - 0.5, labelpad=1)
    ax.set_xlim(0, 1.02)
    ax.set_xticks([0, 0.5, 1])
    ax.set_title(panel_title("c", "Negotiation gain"), fontsize=TITLE_SIZE, loc="left", pad=3)
    ax.legend(loc="upper right", frameon=False, fontsize=LEGEND_SIZE - 1, handlelength=1.6,
              labelspacing=0.25)
    style_axis(ax, "both")

    fig.legend(handles=model_legend_handles("Harvest"), loc="lower center", bbox_to_anchor=(0.36, 0.0), ncol=2, frameon=False,
               fontsize=LEGEND_SIZE, handlelength=1.4, columnspacing=1.0)
    direction_labels = [
        r"Lower is better $\downarrow$",
        r"Higher: component matters more $\uparrow$",
        r"Higher is better $\uparrow$",
    ]
    for panel_ax, label in zip(axes, direction_labels):
        panel_ax.text(0.5, 1.20, label, transform=panel_ax.transAxes,
                      ha="center", va="bottom", fontsize=LEGEND_SIZE,
                      fontweight="bold", color="blue", clip_on=False)
    fig.subplots_adjust(left=L(0.07), right=R(0.995), bottom=0.38, top=0.85, wspace=0.28)
    save(fig, out / "fig_rq2_contributions.pdf")
    return tr


# --------------------------------------------------------------------------
# Fig. 4  RQ3 - provisioning: magic terminals vs. volume, before/after pruning
# --------------------------------------------------------------------------
RQ3_LEVELS = {"ring": [1, 2, 4, 8, 16], "blocks4": [1, 2, 4, 8, 16], "dense4": [1, 2, 4]}


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
    fig, axes = plt.subplots(1, 3, figsize=(PAPER_WIDTH, 2.35), sharey=True,
                             gridspec_kw={"width_ratios": [1, 1, 0.8]})
    for i, (ax, tpl) in enumerate(zip(axes, RQ3_LEVELS)):
        for m in MODELS:
            s = c[(c.template == tpl) & (c.model == m)]
            x = np.arange(len(s))
            ax.plot(x, s.pruned, color=LINE_COLOR["Harvest"][m], marker="o", linestyle="-",
                    label=f"{MODEL_LABELS[m]}, pruned")
            ax.plot(x, s.unpruned, color=LINE_COLOR["Harvest"][m], marker="s", markerfacecolor="white",
                    linestyle=":", label=f"{MODEL_LABELS[m]}, unpruned")
            labels = list(s.level)
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, fontsize=TICK_SIZE)
        ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--")
        n = int(c[(c.template == tpl)].n.min())
        ax.set_title(panel_title(chr(97 + i), f"{TEMPLATE_LABELS[tpl]} ({n} circuits)"),
                     fontsize=TITLE_SIZE, loc="left", pad=3)
        ax.set_ylim(0, 1.45)
        style_axis(ax, "both")
    axes[0].set_ylabel("Volume / volume at\n1 magic patch", fontsize=LABEL_SIZE, labelpad=2)
    fig.supxlabel("# magic patches", fontsize=LABEL_SIZE, y=0.14)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, frameon=False,
               fontsize=LEGEND_SIZE, handlelength=1.6, columnspacing=1.0)
    better_marker(fig, r"Lower is better $\downarrow$")
    fig.subplots_adjust(left=L(0.09), right=R(0.995), bottom=0.31, top=0.85, wspace=0.08)
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


def fig_supply(D: Data, out: Path) -> pd.DataFrame:
    c = rq4_curves(D)
    fig, axes = plt.subplots(1, 3, figsize=(PAPER_WIDTH, 2.35), sharey=True)
    for i, (ax, (model, title)) in enumerate(zip(axes, RQ4_MODELS)):
        a = c[(c.model == model) & (c["mode"] == "aware")]
        o = c[(c.model == model) & (c["mode"] == "oblivious")]
        ax.plot(a.level, a.lb_over_cp, color="black", linestyle=":", linewidth=1.2,
                label=r"Lower bound $\max(T_{cp}, \mathrm{supply})$", zorder=5)
        ax.plot(o.level, o.T_over_cp, color=OBLIVIOUS_COLOR, marker="s",
                linestyle="--", label="Magic-oblivious (replayed)")
        ax.plot(a.level, a.T_over_cp, color=COMPILER_COLORS["Harvest"], marker="o",
                label="Harvest (resource-aware)")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.xaxis.set_major_locator(mtick.FixedLocator(RQ4_LEVELS))
        ax.xaxis.set_major_formatter(mtick.FixedFormatter([str(l) for l in RQ4_LEVELS]))
        ax.xaxis.set_minor_locator(mtick.NullLocator())
        ax.yaxis.set_major_locator(mtick.FixedLocator([1, 2, 5, 10, 20]))
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda y, _: f"{y:g}"))
        ax.yaxis.set_minor_formatter(mtick.NullFormatter())
        n = int(a.n.min())
        ax.set_title(panel_title(chr(97 + i), f"{title} ({n})"), fontsize=TITLE_SIZE,
                     loc="left", pad=3)
        style_axis(ax, "both")
    axes[0].set_ylabel(r"Timesteps / $T_{cp}$", fontsize=LABEL_SIZE, labelpad=2)
    fig.supxlabel("# magic patches", fontsize=LABEL_SIZE, y=0.14)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=3,
               frameon=False, fontsize=LEGEND_SIZE, handlelength=1.8, columnspacing=1.0)
    better_marker(fig, r"Lower is better $\downarrow$")
    fig.subplots_adjust(left=L(0.08), right=R(0.995), bottom=0.31, top=0.85, wspace=0.08)
    save(fig, out / "fig_rq4_supply.pdf")
    return c


# --------------------------------------------------------------------------
# Fig. 6  RQ5 - compile time
# --------------------------------------------------------------------------
def fig_compile(D: Data, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(PAPER_WIDTH, 2.35),
                             gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    r = D.ratios("instant")
    for c in COMPILERS:
        s = r[(r.compiler == c)].dropna(subset=["compile_time_s"])
        s = s[s.compile_time_s > 0].sort_values("ops")
        ax.scatter(s.ops, s.compile_time_s, s=9, color=COMPILER_COLORS[c],
                   edgecolors="black", linewidths=0.3, label=c, zorder=3)
        if len(s) > 5:
            k, b = np.polyfit(np.log10(s.ops), np.log10(s.compile_time_s), 1)
            xx = np.logspace(np.log10(s.ops.min()), np.log10(s.ops.max()), 50)
            ax.plot(xx, 10 ** b * xx ** k, color=COMPILER_COLORS[c], linewidth=1.0)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Pauli rotations $|O|$", fontsize=LABEL_SIZE - 0.5, labelpad=1)
    ax.set_ylabel("Compile time (s)", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("a", "Compile time (instant)"), fontsize=TITLE_SIZE, loc="left", pad=3)
    ax.set_title(r"Lower is better $\downarrow$", fontsize=LEGEND_SIZE, loc="right", pad=3,
                 fontweight="bold", color="blue")
    style_axis(ax, "both")
    ax.legend(loc="upper left", frameon=False, fontsize=LEGEND_SIZE - 1, ncol=2,
              handletextpad=0.2, columnspacing=0.6, labelspacing=0.2)

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
    counts = d.groupby("bin", observed=False).size()
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{l}\n(n={counts[l]})" for l in labs], fontsize=TICK_SIZE - 0.5)
    ax.set_ylim(0, 100)
    ax.set_xlabel(r"Pauli rotations $|O|$", fontsize=LABEL_SIZE - 0.5, labelpad=1)
    ax.set_ylabel("Share of time (%)", fontsize=LABEL_SIZE, labelpad=2)
    ax.set_title(panel_title("b", "Harvest phases"), fontsize=TITLE_SIZE, loc="left", pad=3)
    style_axis(ax)
    fig.subplots_adjust(left=L(0.08), right=R(0.995), bottom=0.31, top=0.85, wspace=0.28)
    h, l = ax.get_legend_handles_labels()
    panel_center = ax.get_position().x0 + ax.get_position().width / 2
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(panel_center, 0.0), ncol=4,
               frameon=False, fontsize=LEGEND_SIZE - 0.5, handlelength=1.3,
               columnspacing=0.6)
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
        r"""\textbf{Results per circuit family} (RQ1), cultivated magic states. Geometric means per family for \textbf{(a)}~normalized space--time volume, \textbf{(b)}~timesteps over the critical path, and \textbf{(c)}~patches per logical qubit. Families with fewer than three circuits are merged into \emph{Other}; numbers in parentheses give the circuits per family. The solid line marks the lower bound. Clipped bars are labeled with their value.""",
        "fig:rq1-family"),
    "fig_rq1_family_instant": (
        r"""\textbf{Results per circuit family} (RQ1), instant magic states. Geometric means per family for \textbf{(a)}~normalized space--time volume, \textbf{(b)}~timesteps over the critical path, and \textbf{(c)}~patches per logical qubit. Families with fewer than three circuits are merged into \emph{Other}; numbers in parentheses give the circuits per family. The solid line marks the lower bound. Clipped bars are labeled with their value.""",
        "fig:rq1-family-instant"),
    "fig_rq1_per_circuit": (
        r"""\textbf{Per-circuit volume relative to Harvest} (RQ1) under \textbf{(a)}~instant and \textbf{(b)}~cultivated magic states. Each line sorts one compiler's volume ratios; values above one favor Harvest. Labels give the number of circuits on which Harvest has the lower volume.""",
        "fig:rq1-per-circuit"),
    "fig_rq1_size_cultivation": (
        r"""\textbf{Scaling with circuit size} (RQ1), cultivated magic states. Circuits are sorted by the number of logical qubits $n$ (tick labels). \textbf{(a)}~Normalized space--time volume, \textbf{(b)}~timesteps over the critical path, and \textbf{(c)}~patches per logical qubit. Lines show the geometric mean over nine neighboring circuits. The solid black line marks the lower bound.""",
        "fig:rq1-size"),
    "fig_rq1_size_instant": (
        r"""\textbf{Scaling with circuit size} (RQ1), instant magic states. Circuits are sorted by the number of logical qubits $n$ (tick labels). \textbf{(a)}~Normalized space--time volume, \textbf{(b)}~timesteps over the critical path, and \textbf{(c)}~patches per logical qubit. Lines show the geometric mean over nine neighboring circuits. The solid black line marks the lower bound.""",
        "fig:rq1-size-instant"),
    "fig_rq1_sota": (
        r"""\textbf{Comparison with the state of the art} (RQ1). Geometric means over all circuits under instant (dark) and cultivated (light) magic states, normalized to circuit size $n$ and critical-path length $T_{cp}$. \textbf{(a)}~Space--time volume per data patch and critical-path step. \textbf{(b)}~Timesteps over the critical path. \textbf{(c)}~Patches per logical qubit. The solid line marks the respective lower bound: $n$ data patches for $T_{cp}$ steps. Bars above the axis limit are clipped and labeled with their value.""",
        "fig:rq1-sota"),
    "fig_rq2_contributions": (
        r"""\textbf{Sources of the improvement} (RQ2). \textbf{(a)}~Volume of Harvest restricted to a single layout template, and of PureMagic, relative to Harvest's per-circuit template choice (Auto). \textbf{(b)}~Leave-one-out ablation: volume of Harvest without one component, relative to full Harvest. \textbf{(c)}~Timestep reduction from negotiated-congestion routing per run, sorted, for three templates.""",
        "fig:rq2-contributions"),
    "fig_rq3_provisioning": (
        r"""\textbf{Layout provisioning} (RQ3). Space--time volume as the working layout provides more magic-state patches, relative to the pruned volume with a single magic-state patch, on the \textbf{(a)}~ring, \textbf{(b)}~blocks-of-four, and \textbf{(c)}~dense template. Filled markers show the reported (pruned) volume, open markers the volume of the working layout before pruning. \emph{max} uses every magic-state patch of the template.""",
        "fig:rq3-provisioning"),
    "fig_rq4_supply": (
        r"""\textbf{Magic-state protocols} (RQ4). Timesteps over the critical path as the number of magic-state patches grows under \textbf{(a)}~distillation with $\mu=4$, \textbf{(b)}~distillation with $\mu=10$, and \textbf{(c)}~cultivation. Harvest schedules against the supply model; the magic-oblivious schedule is computed for instant supply and replayed with stalls. The dotted line is the lower bound $\max(T_{cp}, \text{supply})$. Panel titles give the number of circuits.""",
        "fig:rq4-supply"),
    "fig_rq5_compile": (
        r"""\textbf{Compilation cost} (RQ5). \textbf{(a)}~Compile time over the number of Pauli rotations under instant magic states, with log--log fits; Harvest's time includes all four layout templates. \textbf{(b)}~Share of Harvest's compile time per stage, by circuit size.""",
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
def main(rq: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    D = Data(rq)
    fig_sota(D, out)
    fig_sota_distribution(D, out)
    sc = fig_size(D, out)
    fc = fig_family(D, out)
    tr = fig_contributions(D, out)
    c3 = fig_provisioning(D, out)
    c4 = fig_supply(D, out)
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
            + "\n\nRQ5 scaling fit\n" + D.rq5_fit.to_string() + "\n")


if __name__ == "__main__":
    rq_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("rq")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("figures/evaluation")
    main(rq_dir, out_dir)
