"""E10 grid: scheduler {Harvest, EAF-in-Harvest} x template {ring, blocks4, dense4,
dense4full} x supply {instant, cultivation mean 3 with the 10 held-out seeds} on
the 47-circuit subset.  ``auto`` (best volume of the four) and pruning on/off
(``volume_pruned`` / ``volume_initial`` of the same run) are derived in
``analyze.py``; no extra runs."""

from newexp_common import AUTO_TEMPLATES, HELD_OUT_SEEDS, in_tree_task, suite

EXP = "E10"


def build_tasks():
    tasks = []
    for circ in suite(small=True):
        for model, seeds in (("instant", [None]), ("cultivation", HELD_OUT_SEEDS)):
            for seed in seeds:
                for template in AUTO_TEMPLATES:
                    tasks.append(in_tree_task(EXP, circ, "harvest", template, model, seed))
                    tasks.append(in_tree_task(EXP, circ, "eaf", template, model, seed, 10.0))
    return tasks
