#!/usr/bin/env python3
"""Run the experiments of this set (E10-E14, E19) in one worker pool.

    python eval/new_experiments/run_new.py --exp E10,E11,E12,E13,E14,E19 --jobs 2

Rows go to ``eval/new_experiments/<ID>_<name>/raw/<ID>.csv`` (crash-safe;
a rerun skips finished rows).  Order: E10, then E11/E12/E13 below 400 qubits,
then E14, E19, and last the E11/E12 runs of the n >= 400 Ising circuits.
Log: ``eval/new_experiments/run.log``.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import newexp_common as common  # noqa: E402

for _dir in common.DIRS.values():
    sys.path.insert(0, str(_dir))

from rq_common import run_tasks  # noqa: E402

MODULES = {"E10": "e10_tasks", "E11": "e11_tasks", "E12": "e12_tasks", "E13": "e13_tasks", "E14": "e14_tasks",
           "E19": "e19_tasks"}
RANK = {"E10": 0, "E11": 1, "E12": 1, "E13": 1, "E14": 2, "E19": 3}


def priority(task):
    if task.exp in ("E11", "E12") and task.kwargs["circ"]["num_qubits"] >= 400:
        return 4
    return RANK[task.exp]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--exp", default="E10,E11,E12,E13,E14,E19")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(HERE / "run.log"), logging.StreamHandler(sys.stdout)])
    tasks, columns = [], {}
    for exp in args.exp.split(","):
        exp_tasks = importlib.import_module(MODULES[exp]).build_tasks()
        common.CSV_PATHS[exp].parent.mkdir(parents=True, exist_ok=True)
        columns[exp] = common.COLUMNS
        print(f"{exp}: {len(exp_tasks)} task(s), {sum(len(t.keys) for t in exp_tasks)} row(s), "
              f"cost estimate {sum(t.cost for t in exp_tasks) / 3600:.1f} (relative units)")
        tasks += exp_tasks
    if args.dry_run:
        return 0
    run_tasks(tasks, columns, jobs=args.jobs, priority=priority)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
