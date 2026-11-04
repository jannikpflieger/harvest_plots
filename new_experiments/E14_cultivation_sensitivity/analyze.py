#!/usr/bin/env python3
"""E14 analysis: Harvest (auto) vs PureMagic (best variant) as the cultivation
mean grows (1, 2, 3, 5, 8 cycles; held-out seeds 1000-1009; 47 circuits).

Harvest ``auto`` = per run the template with the smallest pruned volume;
mean 3 comes from E10's Harvest rows.  Per circuit: mean over seeds, then
PureMagic / Harvest.  Seed variation: per circuit coefficient of variation of
the volume over the 10 seeds (median over circuits).
Outputs: ``e14_table.csv/.md``, ``e14_per_circuit.csv``, ``fig_e14_ratio_vs_mean.pdf``,
``fig_e14_cdf.pdf``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import newexp_common as common  # noqa: E402
import newexp_stats as st  # noqa: E402

MEAN_OF = {common.cult_model(m): m for m in common.CULT_MEANS}


def main() -> int:
    e14 = st.read_rows(common.CSV_PATHS["E14"])
    e10 = st.read_rows(common.CSV_PATHS["E10"])
    h = pd.concat([e14[e14.compiler == "Harvest"],
                   e10[(e10.compiler == "Harvest") & (e10.model == "cultivation")]], ignore_index=True)
    if st.check_validator(h, "E14 Harvest"):
        print("BLOCKER: validator violations in E14")
    pm = e14[e14.compiler == "PureMagic"]
    print("PureMagic status", pm.status.value_counts().to_dict())
    for d in (h, pm):
        for c in ("T_cycles", "volume_tile_cycles", "area_tiles"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
    h = h[h.status == "ok"].sort_values("volume_tile_cycles")
    n_t = h.groupby(["circuit", "model", "seed"]).template.transform("size")
    h = h[n_t == len(common.AUTO_TEMPLATES)].groupby(["circuit", "model", "seed"], as_index=False).first()
    h["variant"] = "harvest"
    pm = pm[pm.status == "ok"]
    runs = pd.concat([h, pm], ignore_index=True)
    runs["mean"] = runs.model.map(MEAN_OF)
    per = runs.groupby(["circuit", "compiler", "variant", "mean"]).agg(
        T=("T_cycles", "mean"), area=("area_tiles", "mean"), volume=("volume_tile_cycles", "mean"),
        volume_std=("volume_tile_cycles", "std"), n=("volume_tile_cycles", "size")).reset_index()
    per = per[per.n == len(common.HELD_OUT_SEEDS)]
    per["volume_cv"] = per.volume_std / per.volume
    per = per.sort_values("volume").groupby(["circuit", "compiler", "mean"], as_index=False).first()
    ref = per[per.compiler == "Harvest"].set_index(["circuit", "mean"])
    idx = list(zip(per.circuit, per["mean"]))
    for c in ("volume", "T", "area"):
        per[f"{c}_ratio"] = per[c].values / ref[c].reindex(idx).values
    per.to_csv(HERE / "e14_per_circuit.csv", index=False)
    rows, cdf = [], {}
    for mean, g in per[per.compiler == "PureMagic"].groupby("mean"):
        row = {"cultivation_mean": mean}
        row.update(st.ratio_stats(g.volume_ratio, "vol_"))
        row["T_ratio_geomean"] = st.geomean(g.T_ratio)
        row["area_ratio_geomean"] = st.geomean(g.area_ratio)
        row["pm_faster_circuits"] = int((g.T_ratio < 1 - st.TIE).sum())
        row["pm_volume_cv_median"] = g.volume_cv.median()
        hc = per[(per.compiler == "Harvest") & (per["mean"] == mean)]
        row["harvest_volume_cv_median"] = hc.volume_cv.median()
        rows.append(row)
        cdf[f"mean {mean:g}"] = g.volume_ratio
    tab = pd.DataFrame(rows)
    tab.to_csv(HERE / "e14_table.csv", index=False)
    (HERE / "e14_table.md").write_text(st.md_table(tab))
    print(tab.round(3).to_string(index=False))
    st.cdf_figure(cdf, HERE / "fig_e14_cdf", "PureMagic volume / Harvest volume",
                  title="per circuit, by cultivation mean")
    trend(tab)
    return 0


def trend(tab: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt
    import rq_plotstyle as style

    style.apply()
    fig, ax = plt.subplots(figsize=(4.6, 3.3))
    for i, (col, label) in enumerate((("vol_geomean", "volume"), ("T_ratio_geomean", "makespan"),
                                      ("area_ratio_geomean", "area"))):
        ax.plot(tab.cultivation_mean, tab[col], marker="o", color=style.SERIES[i], label=label)
    ax.axhline(1, color=style.INK2, linewidth=1)
    ax.set_xlabel("mean cultivation delay [logical cycles]")
    ax.set_ylabel("geomean PureMagic / Harvest")
    ax.set_xticks(list(tab.cultivation_mean))
    ax.legend(fontsize=8)
    style.save(fig, HERE / "fig_e14_ratio_vs_mean")


if __name__ == "__main__":
    raise SystemExit(main())
