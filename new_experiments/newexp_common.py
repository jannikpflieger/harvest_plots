"""Shared settings and runners for experiments E10-E14, E19, E20.

Reuses the RQ pipeline (``src/scripts/rq/rq_common.py``): the same suite,
placement cache, compilers, magic models, validator and crash-safe CSV log.
Each experiment writes ``eval/new_experiments/<ID>_<name>/raw/<ID>.csv``.

Seeds (fixed before any run of this set; never chosen after looking at results):

* ``TUNING_SEEDS`` 42-51: the RQ1 seeds (RQ2-RQ5 use 42-44).  These results
  were visible while Harvest was being changed (router-chosen terminals,
  template ``auto``), so they count as tuning seeds.
* ``HELD_OUT_SEEDS`` 1000-1009: never used before this set.  Every new
  stochastic run reports on these.
* ``SEED_A`` 2000: the seed E19 compiles and prunes with (disjoint from both).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src" / "scripts" / "rq"))
sys.path.insert(0, str(HERE))

import rq_common  # noqa: E402
from rq_common import (AUTO_TEMPLATES, CSV_PATHS, MODELS, RunTimeout, run_external, run_in_tree,  # noqa: E402,F401
                       run_key)

TUNING_SEEDS = list(range(42, 52))
HELD_OUT_SEEDS = list(range(1000, 1010))
SEED_A = 2000
TIMEOUT = 3600.0  # s per (circuit, tool, config), as in the RQ scripts

DIRS = {
    "E10": HERE / "E10_framework_vs_scheduler",
    "E11": HERE / "E11_fixed_template",
    "E12": HERE / "E12_area_audit",
    "E13": HERE / "E13_clifford_parity",
    "E14": HERE / "E14_cultivation_sensitivity",
    "E19": HERE / "E19_pruning_robustness",
    "E20": HERE / "E20_failure_report",
}
for _exp, _dir in DIRS.items():
    CSV_PATHS[_exp] = _dir / "raw" / f"{_exp}.csv"

# E14: cultivation (exponential) with other means; "cultivation" itself is mean 3.
CULT_MEANS = (1, 2, 3, 5, 8)


def cult_model(mean: float) -> str:
    if mean == rq_common.CULT_MEAN:
        return "cultivation"
    name = f"cultivation_mean{mean:g}"
    MODELS.setdefault(name, {"magic_model": "cultivation", "cultivation_mean_cycles": float(mean)})
    rq_common.STOCHASTIC.add(name)
    return name


for _mean in CULT_MEANS:
    cult_model(_mean)


def footprint(processor, num_qubits: int) -> dict:
    """Tile counts and bounding boxes of a (pruned) processor's layout.

    Retained tiles follow ``processor_patch_count``: routing cells left in the
    routing graph, patches with a retained port and every register qubit's
    data patch.  ``area_bbox_pruned`` is the bounding box of those tiles;
    ``area_bbox_initial`` that of every non-blocked tile of the layout.
    """
    eng = processor.eng
    cells = {n for n in processor.graph if isinstance(n, tuple)}
    names = set(processor.ports_by_patch) | {f"q_{i}" for i in range(num_qubits)}
    for name in names:
        patch = eng.patches.get(name)
        if patch is not None:
            cells |= set(patch.cells)
    full = [(x, y) for x in range(eng.W) for y in range(eng.H) if eng.occ.get((x, y)) != "BLOCKED"]

    def box(points):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        return w, h

    pw, ph = box(cells)
    fw, fh = box(full)
    return {"retained_cells": len(cells), "bbox_w_pruned": pw, "bbox_h_pruned": ph,
            "area_bbox_pruned": pw * ph, "bbox_w_initial": fw, "bbox_h_initial": fh,
            "area_bbox_initial": fw * fh, "layout_W": eng.W, "layout_H": eng.H}


def run_measured(circ, compiler, template, model, seed, timeout=TIMEOUT, extra=None, sink=None,
                 **kwargs):
    """``run_in_tree`` (Harvest or EAF) plus the footprint columns."""
    sink = {} if sink is None else sink
    row = run_in_tree(circ, compiler, template, model, seed, timeout=timeout, extra=extra,
                      sink=sink, **kwargs)
    if row.get("status", "ok") == "ok" and "processor" in sink:
        row.update(footprint(sink["processor"], circ["num_qubits"]))
        if row.get("T_cycles"):
            row["volume_bbox_pruned"] = row["area_bbox_pruned"] * row["T_cycles"]
    return row


def suite(small: bool):
    """47-circuit ``small`` tier (RQ2-RQ5) or the RQ1 ``core`` tier without random circuits."""
    circuits = rq_common.load_suite(["core"], small_only=small)
    return circuits if small else [c for c in circuits if c["family"] != "random"]


def _harvest_version() -> str:
    import subprocess

    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()

    dirty = git("status", "--porcelain", "--", "src", "rust")
    return f"harvest-rust@{git('rev-parse', '--short', 'HEAD')}" + ("+local" if dirty else "")


# Version of every tool, recorded in each row (ground rule 1).
VERSIONS = {
    "harvest": _harvest_version(),
    "eaf": "in-repo reimplementation of Silva et al. (TQC 2024), src/harvest/baselines/silva.py, "
           "variant silva_eaf_pruned; no official code released",
    "puremagic": "PureMagic f990c3e (~/.cache/harvest-tools/PureMagic, cargo --release)",
}

# Leading CSV columns shared by the in-tree experiments.
COLUMNS = ["role", "tool_version", "T_over_lb", "magic_terminals", "validated_pre", "validated_post",
           "n_violations", "violations_V1", "violations_V2", "violations_V3", "violations_V4",
           "area_bbox_pruned", "area_bbox_initial", "volume_bbox_pruned", "retained_cells",
           "bbox_w_pruned", "bbox_h_pruned", "bbox_w_initial", "bbox_h_initial",
           "t_place_s", "t_schedule_s", "t_prune_s", "magic_wait_cycles", "routing_tiles_initial",
           "routing_tiles_pruned", "magic_tiles_initial", "magic_tiles_pruned", "data_tiles_initial",
           "data_tiles_pruned", "timed_out", "wall_time_s", "process_peak_rss_mb"]


def in_tree_task(exp, circ, compiler, template, model, seed, cost_factor=1.0, role=None, **kwargs):
    from rq_common import Task, cost_estimate

    key = run_key(exp, circ["circuit"], compiler, template, model, seed)
    extra = {"variant": compiler, "template": template, "model": model, "role": role or compiler,
             "compiler": "Harvest" if compiler == "harvest" else "EAF",
             "tool_version": VERSIONS[compiler]}
    return Task(exp, key, "newexp_common:run_measured", dict(
        circ=circ, compiler=compiler, template=template, model=model, seed=seed,
        timeout=TIMEOUT, extra=extra, **kwargs), cost_estimate(circ) * cost_factor)


def puremagic_task(exp, circ, variant, model, seed):
    from rq_common import Task, cost_estimate

    key = run_key(exp, circ["circuit"], "puremagic", variant, model, seed)
    extra = {"variant": variant, "template": variant, "model": model, "compiler": "PureMagic",
             "role": "puremagic", "tool_version": VERSIONS["puremagic"]}
    return Task(exp, key, "rq_common:run_external", dict(
        circ=circ, compiler="puremagic", variant=variant, model=model, seed=seed,
        timeout=TIMEOUT, extra=extra), cost_estimate(circ) * 0.05)
