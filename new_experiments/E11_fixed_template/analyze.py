#!/usr/bin/env python3
"""E11 analysis: RQ1 Table 1 with Harvest restricted to one fixed template.

For Harvest in {auto (RQ1), blocks4, dense4full}: every baseline's best variant
per circuit (mean over seeds, as in ``rq1_plots.per_circuit``) divided by that
Harvest version.  Only circuits where all three Harvest versions finished are
used, so the three tables cover the same circuits.
Outputs: ``e11_table.csv/.md``, ``e11_per_circuit.csv``, ``fig_e11_cdf.pdf``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import newexp_common as common  # noqa: E402
import newexp_stats as st  # noqa: E402
import rq1_plots  # noqa: E402

VERSIONS = ("auto", "blocks4", "dense4full")


def main() -> int:
    e11 = st.read_rows(common.CSV_PATHS["E11"])
    if st.check_validator(e11, "E11"):
        print("BLOCKER: validator violations in E11")
    rq1 = st.rq1_rows()
    base = rq1[rq1.compiler != "Harvest"]
    harvest = {"auto": rq1[rq1.compiler == "Harvest"]}
    for t in ("blocks4", "dense4full"):
        harvest[t] = e11[e11.template == t]
    bests = {}
    for v, h in harvest.items():
        h = h.copy()
        h["variant"] = "harvest"
        bests[v] = rq1_plots.per_circuit(pd.concat([base, h], ignore_index=True))
    # circuits (per model) every Harvest version completed
    done = None
    for v, b in bests.items():
        ok = set(map(tuple, b[(b.compiler == "Harvest") & b.completed][["circuit", "model"]].values))
        done = ok if done is None else done & ok
    rows, per_rows, panels = [], [], []
    for model in rq1_plots.MODELS:
        data = {}
        for v, b in bests.items():
            b = b[[(c, m) in done for c, m in zip(b.circuit, b.model)] & (b.model == model)]
            for comp in rq1_plots.BASELINES:
                s = b[b.compiler == comp]
                row = {"supply": model, "harvest": v, "baseline": comp}
                row.update(st.ratio_stats(s.volume_ratio, "vol_"))
                row["T_ratio_geomean"] = st.geomean(s.T_ratio)
                row["area_ratio_geomean"] = st.geomean(s.area_ratio)
                row["baseline_faster"] = int((s.T_ratio < 1 - st.TIE).sum())
                rows.append(row)
            best_base = b[b.compiler != "Harvest"].groupby("circuit").volume_ratio.min()
            row = {"supply": model, "harvest": v, "baseline": "best baseline per circuit"}
            row.update(st.ratio_stats(best_base, "vol_"))
            rows.append(row)
            data[f"Harvest {v}"] = best_base
            per_rows.append(b.assign(harvest_version=v))
        panels.append((f"{model}: best baseline / Harvest", data))
    tab = pd.DataFrame(rows)
    tab.to_csv(HERE / "e11_table.csv", index=False)
    (HERE / "e11_table.md").write_text(st.md_table(tab))
    pd.concat(per_rows).to_csv(HERE / "e11_per_circuit.csv", index=False)
    st.cdf_figure(None, HERE / "fig_e11_cdf", "volume of best baseline / Harvest", panels=panels)
    print(f"{len(done)} (circuit, model) pairs with all Harvest versions")
    print(tab.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
