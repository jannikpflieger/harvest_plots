#!/usr/bin/env python3
"""E10 analysis: volume, makespan and area of every (scheduler, layout, pruning,
supply) config relative to full Harvest (Harvest, auto, pruning on), per circuit.

``auto`` = per run (circuit, scheduler, supply, seed, pruning setting) the
template with the smallest volume under that pruning setting.  Pruning off =
the same run priced on the unpruned layout (``volume_initial``).
Outputs: ``e10_table.csv/.md``, ``e10_per_circuit.csv``, ``e10_seed_std.csv``,
``fig_e10_cdf.pdf``, ``fig_e10_bars.pdf``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import newexp_common as common  # noqa: E402
import newexp_stats as st  # noqa: E402

LAYOUTS = ("blocks4", "dense4full", "auto")


def configs(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (circuit, scheduler, layout, pruning, supply, seed)."""
    df = df[df.status == "ok"].copy()
    for c in ("T_cycles", "volume_pruned", "volume_initial", "area_pruned_tiles", "area_initial_tiles"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["seed"] = df.seed.fillna(-1)
    out = []
    for prune, vol, area in ((True, "volume_pruned", "area_pruned_tiles"),
                             (False, "volume_initial", "area_initial_tiles")):
        d = df[["circuit", "compiler", "template", "model", "seed", "T_cycles", vol, area]].rename(
            columns={vol: "volume", area: "area", "T_cycles": "T"})
        d["pruning"] = "on" if prune else "off"
        out.append(d)
        # auto: best template of this run under this pruning setting (ties: template order)
        d = d.assign(order=d.template.map(common.AUTO_TEMPLATES.index)).sort_values(["volume", "order"])
        keys = ["circuit", "compiler", "model", "seed"]
        n = d.groupby(keys).template.transform("size")
        best = d[n == len(common.AUTO_TEMPLATES)].groupby(keys, as_index=False).first()
        best["template_chosen"] = best.template
        best["template"] = "auto"
        out.append(best.drop(columns="order"))
    return pd.concat(out, ignore_index=True)


def main() -> int:
    raw = st.read_rows(common.CSV_PATHS["E10"])
    if st.check_validator(raw, "E10"):
        print("BLOCKER: validator violations in E10")
    runs = configs(raw)
    runs = runs[runs.template.isin(LAYOUTS)]
    keys = ["circuit", "compiler", "template", "pruning", "model"]
    per = runs.groupby(keys).agg(T=("T", "mean"), area=("area", "mean"), volume=("volume", "mean"),
                                 volume_std=("volume", "std"), n=("volume", "size")).reset_index()
    expected = per.model.map({"instant": 1, "cultivation": len(common.HELD_OUT_SEEDS)})
    per = per[per.n == expected]
    ref = per[(per.compiler == "Harvest") & (per.template == "auto") & (per.pruning == "on")]
    ref = ref.set_index(["circuit", "model"])
    idx = list(zip(per.circuit, per.model))
    for c in ("volume", "T", "area"):
        per[f"{c}_ratio"] = per[c].values / ref[c].reindex(idx).values
    per["volume_cv"] = per.volume_std / per.volume
    per.to_csv(HERE / "e10_per_circuit.csv", index=False)

    rows = []
    for (comp, tmpl, prune, model), g in per.groupby(["compiler", "template", "pruning", "model"]):
        row = {"supply": model, "scheduler": comp, "layout": tmpl, "pruning": prune}
        row.update(st.ratio_stats(g.volume_ratio, "vol_"))
        row["T_ratio_geomean"] = st.geomean(g.T_ratio)
        row["area_ratio_geomean"] = st.geomean(g.area_ratio)
        if model != "instant":
            row["volume_cv_median"] = g.volume_cv.median()
        rows.append(row)
    tab = pd.DataFrame(rows)
    order = {(s, l, p): i for i, (s, l, p) in enumerate(
        (s, l, p) for s in ("Harvest", "EAF") for l in LAYOUTS for p in ("on", "off"))}
    tab = tab.sort_values(["supply", "scheduler", "layout", "pruning"],
                          key=lambda c: c.map({"instant": 0, "cultivation": 1, "Harvest": 0, "EAF": 1,
                                               "blocks4": 0, "dense4full": 1, "auto": 2, "on": 0, "off": 1}))
    tab.to_csv(HERE / "e10_table.csv", index=False)
    (HERE / "e10_table.md").write_text(st.md_table(tab))
    print(tab.round(3).to_string(index=False))

    panels = []
    for model in ("instant", "cultivation"):
        s = per[per.model == model]
        data = {}
        for comp, tmpl, prune in (("EAF", "auto", "on"), ("Harvest", "blocks4", "off"),
                                  ("EAF", "blocks4", "off"), ("Harvest", "blocks4", "on"),
                                  ("EAF", "blocks4", "on")):
            data[f"{comp} {tmpl} prune {prune}"] = s[(s.compiler == comp) & (s.template == tmpl)
                                                     & (s.pruning == prune)].volume_ratio
        panels.append((model, data))
    st.cdf_figure(None, HERE / "fig_e10_cdf", "volume / full Harvest (auto, pruned)", panels=panels)
    bars(tab)
    return 0


def bars(tab: pd.DataFrame) -> None:
    """Geomean volume ratio per config (bars), Harvest vs EAF side by side."""
    import matplotlib.pyplot as plt
    import rq_plotstyle as style

    style.apply()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    labels = [f"{l}\nprune {p}" for l in LAYOUTS for p in ("on", "off")]
    x = np.arange(len(labels))
    for ax, model in zip(axes, ("instant", "cultivation")):
        for i, comp in enumerate(("Harvest", "EAF")):
            s = tab[(tab.supply == model) & (tab.scheduler == comp)].set_index(["layout", "pruning"])
            vals = [s.vol_geomean.get((l, p), np.nan) for l in LAYOUTS for p in ("on", "off")]
            ax.bar(x + (i - 0.5) * 0.38, vals, 0.36, color=style.COMPILER_COLORS[comp], label=comp,
                   edgecolor=style.SURFACE, linewidth=2)
        ax.axhline(1, color=style.INK2, linewidth=1)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_title(model)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("geomean volume / full Harvest")
    axes[0].legend(fontsize=8)
    style.save(fig, HERE / "fig_e10_bars")


if __name__ == "__main__":
    raise SystemExit(main())
