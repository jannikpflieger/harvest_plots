"""E19: does pruning overfit to one seed?

Per circuit (47-circuit subset, cultivation mean 3): compile with ``auto`` and
seed A = 2000, prune, then reschedule from scratch on the pruned footprint
(``rq3_provisioning.right_sized_layout``: unused routing tiles and magic
patches blocked, every data patch kept) with each held-out seed B.  The
full-layout reference with the same seed B and template is E10's row.
Rows: ``role=A`` (the seed-A compile) and ``role=B`` (one per seed B)."""

from newexp_common import HELD_OUT_SEEDS, SEED_A, VERSIONS, run_key, run_measured, suite

EXP = "E19"


def run_e19(circ, timeout, extra):
    from rq3_provisioning import right_sized_layout

    sink = {}
    a = run_measured(circ, "harvest", "auto", "cultivation", SEED_A, timeout=timeout,
                     extra={**extra, "role": "A"}, sink=sink)
    rows = [a]
    if a.get("status", "ok") != "ok" or "processor" not in sink:
        return rows
    chosen = a["template_chosen"]
    for seed in HELD_OUT_SEEDS:
        layout = right_sized_layout(sink["processor"], circ["num_qubits"])
        b = run_measured(circ, "harvest", chosen, "cultivation", seed, timeout=timeout, layout=layout,
                         extra={**extra, "role": "B", "template_A": chosen,
                                "A_area_pruned": a.get("area_pruned_tiles"),
                                "A_T": a.get("T_cycles")})
        rows.append(b)
    return rows


def build_tasks():
    from rq_common import Task, cost_estimate

    tasks = []
    for circ in suite(small=True):
        base = run_key(EXP, circ["circuit"], "harvest", "auto", "cultivation")
        keys = [base + f"|A{SEED_A}"] + [base + f"|B{s}" for s in HELD_OUT_SEEDS]
        extra = {"variant": "harvest", "template": "auto", "model": "cultivation",
                 "compiler": "Harvest", "tool_version": VERSIONS["harvest"]}
        tasks.append(Task(EXP, base, "e19_tasks:run_e19", dict(circ=circ, timeout=3600.0, extra=extra),
                          cost_estimate(circ) * 14, keys=keys))
    return tasks
