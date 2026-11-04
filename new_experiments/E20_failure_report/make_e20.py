#!/usr/bin/env python3
"""E20: status of every benchmark circuit for every tool and config already run.

Sources (no new runs):
* ``results/rq/suite.csv``: every candidate circuit, qubits, rotations, suite status.
* RQ1 rows: Harvest ``auto`` from this checkout (Rust router); PureMagic from
  ``harvest_magic_state_perf``; EAF / Litinski / O3LS from ``harvest_magic_state``.
* RQ2-RQ5 rows from this checkout.

The expected RQ1 trials are the keys ``rq1_sota.build_tasks`` generates
(Harvest: template ``auto``; EAF: ``blocks4``).  Cell values: ``ok``, or the
counts per status (``ok 7/10, timeout 3``); ``missing k/n`` = rows not written
(yet); ``n/a`` = config not part of the design for this circuit.

Output: ``e20_status.csv`` (one row per circuit), ``e20_summary.csv``
(per tool/config), ``e20_subsets.md``.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import newexp_common as common  # noqa: E402
from rq_common import RESULTS, load_suite, read_rows  # noqa: E402

CODE = common.ROOT.parent
SOURCES = {
    "Harvest": common.ROOT / "results/rq/rq1/rq1.csv",
    "PureMagic": CODE / "harvest_magic_state_perf/results/rq/rq1/rq1.csv",
    "EAF": CODE / "harvest_magic_state/results/rq/rq1/rq1.csv",
    "Litinski": CODE / "harvest_magic_state/results/rq/rq1/rq1.csv",
    "O3LS": CODE / "harvest_magic_state/results/rq/rq1/rq1.csv",
}
MODELS = ("instant", "cultivation", "cultivation_pm")


def expected_keys():
    """(tool column, model) -> circuit -> list of RQ1 run keys."""
    import rq1_sota

    circuits = load_suite(["core"])
    out = defaultdict(lambda: defaultdict(list))
    for templates, compilers in ((["auto"], {"Harvest"}), (["blocks4"], {"EAF", "PureMagic", "Litinski", "O3LS"})):
        tasks = rq1_sota.build_tasks(circuits, templates, ["instant", "cultivation"], 3600)
        tasks += rq1_sota.build_pm_cultivation_tasks(circuits, 3600, templates)
        for t in tasks:
            comp = t.kwargs["extra"]["compiler"]
            if comp not in compilers:
                continue
            col = f"{comp}:{t.kwargs['extra']['variant']}" if comp in ("PureMagic", "Litinski", "O3LS") else comp
            out[(col, t.kwargs["model"])][t.kwargs["circ"]["circuit"]].append(t.key)
    return out


def cell(keys, status_by_key, dropped):
    if dropped:
        return "not run (random family dropped)"
    counts = Counter(status_by_key.get(k, "missing") for k in keys)
    if counts == Counter({"ok": len(keys)}):
        return "ok"
    parts = [f"ok {counts.pop('ok', 0)}/{len(keys)}"]
    parts += [f"{s} {n}" for s, n in sorted(counts.items())]
    return ", ".join(parts)


def main() -> int:
    suite = pd.read_csv(RESULTS / "suite.csv")
    status = {}
    for comp, path in SOURCES.items():
        df = read_rows(path)
        df = df[df.compiler == comp]
        status.update(dict(zip(df.run_key, df.status)))
    exp = expected_keys()
    rows = []
    for r in suite.itertuples():
        row = {"circuit": r.circuit, "family": r.family, "qubits": r.num_qubits,
               "rotations": r.ops, "suite_status": r.status, "suite_reason": r.reason,
               "tier": r.tier, "small_subset": r.small}
        for (col, model), by_circ in sorted(exp.items()):
            keys = by_circ.get(r.circuit)
            name = f"{col}|{model}"
            if r.status != "ok" or r.tier != "core":
                row[name] = "n/a (not in RQ1 suite)"
            elif not keys:
                row[name] = "n/a"
            else:
                dropped = col == "Harvest" and r.family == "random"
                row[name] = cell(keys, status, dropped)
        rows.append(row)
    out = pd.DataFrame(rows)
    for e in ("rq2", "rq3", "rq4", "rq5"):
        df = read_rows(RESULTS / e / f"{e}.csv")
        per = df.groupby("circuit").status.apply(lambda s: "ok" if (s == "ok").all() else
                                                 ", ".join(f"{k} {v}" for k, v in s.value_counts().items()))
        n = df.groupby("circuit").size()
        out[e] = out.circuit.map(lambda c: f"{per[c]} ({n[c]} rows)" if c in per.index else "n/a")
    out.to_csv(HERE / "e20_status.csv", index=False)

    summ = []
    rq1 = out[(out.suite_status == "ok") & (out.tier == "core")]
    for col in [c for c in out.columns if "|" in c]:
        vals = rq1[col]
        summ.append({"tool_config": col, "circuits": int((~vals.str.startswith("n/a")).sum()),
                     "all_ok": int((vals == "ok").sum()),
                     "with_failures": int(vals.str.contains("timeout|error|crashed").sum()),
                     "incomplete": int(vals.str.contains("missing").sum()),
                     "not_run": int(vals.str.startswith("not run").sum())})
    pd.DataFrame(summ).to_csv(HERE / "e20_summary.csv", index=False)
    print(pd.DataFrame(summ).to_string(index=False))
    print(Counter(zip(out.suite_status, out.tier)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
