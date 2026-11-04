#!/usr/bin/env python3
"""E19 analysis: rescheduling on a layout pruned under seed A, with seeds B.

Per (circuit, seed B), against E10's full-layout run of the same template and
seed: makespan ratio T_pruned / T_full; volume of the fixed pruned hardware
(A's pruned area x T_pruned) over the full-layout run's pruned volume (per-seed
pruning, an optimistic reference) and over its unpruned volume.
Outputs: ``e19_pairs.csv``, ``e19_table.csv/.md``, ``fig_e19_cdf.pdf``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import newexp_common as common  # noqa: E402
import newexp_stats as st  # noqa: E402


def main() -> int:
    e19 = st.read_rows(common.CSV_PATHS["E19"])
    if st.check_validator(e19, "E19"):
        print("BLOCKER: validator violations in E19")
    e10 = st.read_rows(common.CSV_PATHS["E10"])
    ref = e10[(e10.compiler == "Harvest") & (e10.model == "cultivation") & (e10.status == "ok")]
    b = e19[(e19.role == "B") & (e19.status == "ok")]
    pair = b[["circuit", "template", "seed", "T_cycles", "A_area_pruned", "A_T", "area_pruned_tiles"]].merge(
        ref[["circuit", "template", "seed", "T_cycles", "volume_pruned", "volume_initial",
             "area_pruned_tiles"]], on=["circuit", "template", "seed"], suffixes=("_pr", "_full"))
    for c in pair.columns:
        if c not in ("circuit", "template"):
            pair[c] = pd.to_numeric(pair[c], errors="coerce")
    pair["T_ratio"] = pair.T_cycles_pr / pair.T_cycles_full
    pair["vol_fixed"] = pair.A_area_pruned * pair.T_cycles_pr
    pair["vol_ratio_vs_full_pruned"] = pair.vol_fixed / pair.volume_pruned
    pair["vol_ratio_vs_full_unpruned"] = pair.vol_fixed / pair.volume_initial
    pair["area_ratio_vs_full_pruned"] = pair.A_area_pruned / pair.area_pruned_tiles_full
    pair.to_csv(HERE / "e19_pairs.csv", index=False)
    per = pair.groupby("circuit").agg(T_ratio=("T_ratio", "mean"), T_ratio_max=("T_ratio", "max"),
                                      v_pr=("vol_ratio_vs_full_pruned", "mean"),
                                      v_un=("vol_ratio_vs_full_unpruned", "mean"),
                                      vol_fixed_cv=("vol_fixed", lambda x: x.std() / x.mean()),
                                      n=("seed", "size"))
    per = per[per.n == len(common.HELD_OUT_SEEDS)]
    rows = []
    for col, label in (("T_ratio", "makespan: pruned layout / full layout"),
                       ("v_pr", "volume: fixed pruned layout / full layout pruned per seed"),
                       ("v_un", "volume: fixed pruned layout / full layout unpruned")):
        row = {"metric": label}
        row.update(st.ratio_stats(per[col], ""))
        rows.append(row)
    full = pair[pair.circuit.isin(per.index)]
    rows.append({"metric": "share of (circuit, seed) with makespan +>1%",
                 "n": len(full), "geomean": float((full.T_ratio > 1 + st.TIE).mean())})
    rows.append({"metric": "max makespan ratio over (circuit, seed)", "n": len(full),
                 "geomean": float(full.T_ratio.max())})
    rows.append({"metric": "median per-circuit CV of fixed-layout volume over seeds B",
                 "n": len(per), "geomean": float(per.vol_fixed_cv.median())})
    tab = pd.DataFrame(rows)
    tab.to_csv(HERE / "e19_table.csv", index=False)
    (HERE / "e19_table.md").write_text(st.md_table(tab))
    print(tab.round(4).to_string(index=False))
    st.cdf_figure({"makespan": per.T_ratio, "volume vs full (pruned per seed)": per.v_pr,
                   "volume vs full (unpruned)": per.v_un}, HERE / "fig_e19_cdf",
                  "pruned-under-seed-A layout / full layout, seeds B", title="E19")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
