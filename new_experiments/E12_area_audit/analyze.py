#!/usr/bin/env python3
"""E12 analysis: RQ1 ratios under different area accountings for Harvest.

Harvest ``auto`` (RQ1 rows, seeds 42-51) priced three ways, from the rerun of
each trial's chosen template (E11 rows for blocks4/dense4full, E12 rows for
ring/dense4; the rerun must reproduce the RQ1 volume):

* ``retained``: tiles kept after pruning (as reported in RQ1);
* ``bbox``: bounding box of the pruned layout;
* ``unpruned``: the full template layout of the chosen template.

EAF (blocks4, RQ1 rows) is priced retained and unpruned.  Baselines that report
a full block / board / rectangle (Litinski, O3LS, PureMagic) are unchanged.
Outputs: ``e12_table.csv/.md`` (ratios and ranking per accounting),
``e12_trials.csv``, ``e12_reproduction.csv``, ``fig_e12_cdf.pdf``; on the
47-circuit subset also ``e12_subset_eaf_bbox.csv`` from E10 (EAF bbox).
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
    e11 = st.read_rows(common.CSV_PATHS["E11"])
    e12 = st.read_rows(common.CSV_PATHS["E12"])
    if st.check_validator(e12, "E12"):
        print("BLOCKER: validator violations in E12")
    reruns = pd.concat([e11, e12], ignore_index=True)
    reruns = reruns[reruns.status == "ok"].copy()
    reruns["seed"] = reruns.seed.fillna(-1)
    reruns = reruns.drop_duplicates(["circuit", "template", "model", "seed"], keep="last")
    rq1 = st.rq1_rows()
    h = rq1[(rq1.compiler == "Harvest") & (rq1.status == "ok")].copy()
    h["seed"] = h.seed.fillna(-1)
    sel = reruns[["circuit", "template", "model", "seed", "volume_tile_cycles", "area_bbox_pruned"]].rename(
        columns={"template": "template_chosen", "volume_tile_cycles": "volume_re", "area_bbox_pruned": "bbox_re"})
    m = h.merge(sel, on=["circuit", "template_chosen", "model", "seed"], how="left")
    m["reproduced"] = m.volume_tile_cycles == m.volume_re
    rep = m.groupby("model").agg(trials=("circuit", "size"), rerun=("volume_re", "count"),
                                 identical=("reproduced", "sum")).reset_index()
    rep.to_csv(HERE / "e12_reproduction.csv", index=False)
    print(rep.to_string(index=False))
    m = m[m.volume_re.notna()]
    T = m.T_cycles
    m["vol_retained"] = m.area_pruned_tiles * T
    m["vol_bbox"] = pd.to_numeric(m.bbox_re, errors="coerce") * T
    m["vol_unpruned"] = m.area_initial_tiles * T
    m[["circuit", "model", "seed", "template_chosen", "T_cycles", "area_pruned_tiles",
       "bbox_re", "area_initial_tiles", "vol_retained", "vol_bbox", "vol_unpruned",
       "reproduced"]].to_csv(HERE / "e12_trials.csv", index=False)

    base = rq1[rq1.compiler != "Harvest"].copy()
    eaf_unpruned = base[base.compiler == "EAF"].copy()
    eaf_unpruned["compiler"] = "EAF (unpruned)"
    eaf_unpruned["area_tiles"] = eaf_unpruned.area_initial_tiles
    eaf_unpruned["volume_tile_cycles"] = eaf_unpruned.volume_initial
    rows, panels = [], []
    for acc in ("retained", "bbox", "unpruned"):
        hv = m.copy()
        hv["variant"] = "harvest"
        hv["volume_tile_cycles"] = hv[f"vol_{acc}"]
        hv["area_tiles"] = hv[f"vol_{acc}"] / T
        cols = [c for c in base.columns if c in hv.columns]
        df = pd.concat([base, eaf_unpruned[cols], hv[cols]], ignore_index=True)
        best = rq1_plots.per_circuit(df)
        complete = best[(best.compiler == "Harvest") & best.completed][["circuit", "model"]]
        best = best.merge(complete, on=["circuit", "model"])
        data = {}
        for model in rq1_plots.MODELS:
            b = best[best.model == model]
            gms = {}
            for comp in ["EAF", "EAF (unpruned)", "PureMagic", "Litinski", "O3LS"]:
                s = b[b.compiler == comp]
                row = {"accounting": acc, "supply": model, "baseline": comp}
                row.update(st.ratio_stats(s.volume_ratio, "vol_"))
                row["area_ratio_geomean"] = st.geomean(s.area_ratio)
                rows.append(row)
                gms[comp] = row.get("vol_geomean")
                if comp != "EAF (unpruned)":
                    data[f"{model} {comp}"] = s.volume_ratio
            ranking = sorted([("Harvest", 1.0)] + [(c, g) for c, g in gms.items() if c != "EAF (unpruned)"],
                             key=lambda x: x[1])
            rows.append({"accounting": acc, "supply": model, "baseline": "RANKING (geomean volume)",
                         "vol_n": " < ".join(c for c, _ in ranking)})
        panels.append((f"Harvest area = {acc}", {k: v for k, v in data.items() if "cultivation" in k}))
    tab = pd.DataFrame(rows)
    tab.to_csv(HERE / "e12_table.csv", index=False)
    (HERE / "e12_table.md").write_text(st.md_table(tab))
    st.cdf_figure(None, HERE / "fig_e12_cdf", "baseline volume / Harvest (cultivation)", panels=panels)
    print(tab.round(3).to_string(index=False))

    # subset: EAF and Harvest bbox on E10 (held-out seeds), template auto by retained volume
    e10 = st.read_rows(common.CSV_PATHS["E10"])
    e10 = e10[e10.status == "ok"].copy()
    e10["seed"] = e10.seed.fillna(-1)
    for c in ("volume_pruned", "area_pruned_tiles", "area_bbox_pruned", "T_cycles"):
        e10[c] = pd.to_numeric(e10[c], errors="coerce")
    e10 = e10.sort_values("volume_pruned")
    auto = e10.groupby(["circuit", "compiler", "model", "seed"], as_index=False).first()
    auto["bbox_over_retained"] = auto.area_bbox_pruned / auto.area_pruned_tiles
    sub = auto.groupby(["compiler", "model"]).bbox_over_retained.agg(
        geomean=st.geomean, max="max", n="size").reset_index()
    sub.to_csv(HERE / "e12_subset_eaf_bbox.csv", index=False)
    print(sub.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
