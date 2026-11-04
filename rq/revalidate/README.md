# Re-validation of RQ1-RQ4 with the paper's rules

Script: `src/scripts/rq/revalidate.py`. The stored HARVEST rows of `results/rq/rq1..rq4` are
recompiled (schedules are not stored; the scheduler is deterministic) with the experiments' own
task builders, and every schedule is checked with the strict validator in the paper's numbering
(V1 dependencies, V2 realizability incl. exactly one port per operand and boundary type, V3
exclusivity, V4 magic availability). RQ1 `auto` rows rebuild only the reported template.
EAF and external baselines are not rerun.

- `revalidate.csv`: one row per task. `status` ok / violation / not_reproduced / error;
  `reproduced` = T and volume equal the stored rows; `paper_*` = strict-validator counts over
  every schedule the task checked (`paper_n_schedules`); `paper_n_probes` = V4-only checks of
  RQ4's unmodified oblivious replays, which are meant to fail and are not counted.
- `summary.csv`: per experiment, schedules checked and violations per rule.
