#!/usr/bin/env python3
"""E13 analysis: PureMagic under cultivation with vs without its injection-failure
(S-correction) model, paired by (circuit, variant, seed), and the RQ1
cultivation ratio PureMagic / Harvest (auto) under each.
Outputs: ``e13_paired.csv``, ``e13_table.csv/.md``, ``fig_e13_cdf.pdf``.
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


def main() -> int:
    off = st.read_rows(common.CSV_PATHS["E13"])
    print("E13 status", off.status.value_counts().to_dict())
    rq1 = st.rq1_rows(("cultivation",))
    on = rq1[rq1.compiler == "PureMagic"]
    keys = ["circuit", "variant", "seed"]
    pair = on[keys + ["T_cycles", "volume_tile_cycles", "area_tiles", "status"]].merge(
        off[keys + ["T_cycles", "volume_tile_cycles", "area_tiles", "status"]], on=keys,
        suffixes=("_on", "_off"))
    pair = pair[(pair.status_on == "ok") & (pair.status_off == "ok")]
    pair["T_off_over_on"] = pair.T_cycles_off / pair.T_cycles_on
    pair["area_equal"] = pair.area_tiles_off == pair.area_tiles_on
    pair.to_csv(HERE / "e13_paired.csv", index=False)
    rows = []
    for v, g in pair.groupby("variant"):
        per = g.groupby("circuit").T_off_over_on.mean()
        row = {"comparison": f"PureMagic {v}: T(no correction) / T(correction)", "runs": len(g),
               "area_unchanged_runs": int(g.area_equal.sum())}
        row.update(st.ratio_stats(per, "T_"))
        rows.append(row)
    panels = {}
    for label, pm in (("correction on (RQ1)", on), ("correction off (E13)", off)):
        df = pd.concat([rq1[rq1.compiler == "Harvest"], pm.assign(compiler="PureMagic")], ignore_index=True)
        best = rq1_plots.per_circuit(df)
        s = best[(best.compiler == "PureMagic") & best.volume_ratio.notna()]
        row = {"comparison": f"PureMagic best variant / Harvest auto, cultivation, {label}"}
        row.update(st.ratio_stats(s.volume_ratio, "vol_"))
        row["T_ratio_geomean"] = st.geomean(s.T_ratio)
        row["pm_faster_circuits"] = int((s.T_ratio < 1 - st.TIE).sum())
        rows.append(row)
        panels[label] = s.volume_ratio
    tab = pd.DataFrame(rows)
    tab.to_csv(HERE / "e13_table.csv", index=False)
    (HERE / "e13_table.md").write_text(st.md_table(tab))
    st.cdf_figure(panels, HERE / "fig_e13_cdf", "PureMagic volume / Harvest (cultivation)",
                  title="PureMagic correction model on vs off")
    print(tab.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
