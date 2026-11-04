"""E12: footprint (bounding box) of Harvest's ``auto`` result on the RQ1 set.

E11 already reruns blocks4 and dense4full with footprint columns.  For every
RQ1 ``auto`` trial whose chosen template was ring or dense4, this reruns that
template with the same seed (the schedule is deterministic per seed, so the
volume must equal the RQ1 row; ``analyze.py`` checks it)."""

from newexp_common import ROOT, in_tree_task, suite

EXP = "E12"
RQ1_CSV = ROOT / "results" / "rq" / "rq1" / "rq1.csv"


def build_tasks():
    import pandas as pd
    from rq_common import read_rows

    rows = read_rows(RQ1_CSV)
    rows = rows[(rows.status == "ok") & rows.model.isin(["instant", "cultivation"])
                & rows.template_chosen.isin(["ring", "dense4"])]
    circuits = {c["circuit"]: c for c in suite(small=False)}
    tasks = []
    for r in rows.itertuples():
        if r.circuit not in circuits:
            continue
        seed = None if pd.isna(r.seed) else int(r.seed)
        tasks.append(in_tree_task(EXP, circuits[r.circuit], "harvest", r.template_chosen, r.model, seed))
    return tasks
