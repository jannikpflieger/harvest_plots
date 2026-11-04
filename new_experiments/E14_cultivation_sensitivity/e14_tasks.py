"""E14: cultivation mean in {1, 2, 3, 5, 8} logical cycles (exponential), 10
held-out seeds, 47-circuit subset.  Harvest: every ``auto`` template per run
(``auto`` is derived in ``analyze.py``); mean 3 is E10's Harvest rows (same
model and seeds).  PureMagic: both RQ1 variants (bus, magic routing) with
lambda = 1/mean.  EAF is left out (about 10x Harvest's run time per template)."""

from newexp_common import (AUTO_TEMPLATES, CULT_MEANS, HELD_OUT_SEEDS, cult_model, in_tree_task,
                           puremagic_task, suite)

EXP = "E14"
PM_VARIANTS = ("puremagic_bus", "puremagic")


def build_tasks():
    tasks = []
    for circ in suite(small=True):
        for mean in CULT_MEANS:
            model = cult_model(mean)
            for seed in HELD_OUT_SEEDS:
                if mean != 3:
                    for template in AUTO_TEMPLATES:
                        tasks.append(in_tree_task(EXP, circ, "harvest", template, model, seed))
                for variant in PM_VARIANTS:
                    tasks.append(puremagic_task(EXP, circ, variant, model, seed))
    return tasks
