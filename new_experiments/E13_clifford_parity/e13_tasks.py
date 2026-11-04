"""E13 step 2: PureMagic under cultivation (mean 3) with its injection-failure /
S-correction model switched off (``--no-t-failures``), on the RQ1 set with the
RQ1 seeds 42-51, so each row pairs with the RQ1 PureMagic row of the same
seed that had it on.  Harvest, EAF, Litinski and O3LS model no correction
(see REPORT.md, E13 audit), so this puts PureMagic on the same footing."""

from newexp_common import TUNING_SEEDS, VERSIONS, run_key, suite

EXP = "E13"
PM_VARIANTS = ("puremagic_bus", "puremagic")


def build_tasks():
    from rq_common import Task, cost_estimate

    tasks = []
    for circ in suite(small=False):
        for variant in PM_VARIANTS:
            for seed in TUNING_SEEDS:
                key = run_key(EXP, circ["circuit"], "puremagic", variant, "cultivation", seed, "notfail")
                extra = {"variant": variant, "template": variant, "model": "cultivation",
                         "compiler": "PureMagic", "role": "no_t_failures",
                         "tool_version": VERSIONS["puremagic"], "no_t_failures": True}
                tasks.append(Task(EXP, key, "rq_common:run_external", dict(
                    circ=circ, compiler="puremagic", variant=variant, model="cultivation", seed=seed,
                    timeout=3600.0, extra=extra, no_t_failures=True), cost_estimate(circ) * 0.05))
    return tasks
