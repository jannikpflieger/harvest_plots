"""E11: Harvest on a single fixed template (blocks4, dense4full) on the RQ1 set
(core tier without random circuits), with the RQ1 seeds so every baseline row
of RQ1 pairs with it: instant + cultivation seeds 42-51 (42-44 for n >= 400)."""

from newexp_common import TUNING_SEEDS, in_tree_task, suite

EXP = "E11"
TEMPLATES = ("blocks4", "dense4full")


def seeds_for(circ):
    return TUNING_SEEDS[:3] if circ["num_qubits"] >= 400 else TUNING_SEEDS


def build_tasks():
    tasks = []
    for circ in suite(small=False):
        for model, seeds in (("instant", [None]), ("cultivation", seeds_for(circ))):
            for seed in seeds:
                for template in TEMPLATES:
                    tasks.append(in_tree_task(EXP, circ, "harvest", template, model, seed))
    return tasks
