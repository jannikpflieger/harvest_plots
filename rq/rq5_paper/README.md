# RQ5 fault injection with the paper's validator rules

Script: `src/scripts/rq/rq5_validity_paper.py` (`rq5_validity.py` unchanged). Same faults,
corruptions, circuits (`small` tier, blocks4, instant and cultivation seed 42) and trial seeds as
RQ5; every check uses the strict validator (exactly one port per operand and boundary type) and
the paper's numbering: V1 dependencies, V2 realizability, V3 exclusivity, V4 magic availability.

- `rq5_paper.csv`: one row per fault run / corruption trial (`status` n/a = mutation not
  applicable); `violations_V1..V4` and `first_violation_rule` in paper numbering.
- `detection.csv`: per fault / corruption kind and model, detection rate among applicable
  trials (faults: among runs where the fault activated) and the first rules that fired;
  `valid_base` = unmutated schedules flagged (should be 0).
- New corruption kind `extra_port` (not in RQ5): a second same-type port of an operand patch added
  to a route, with its edge to an adjacent route tile, on a ring schedule of the same circuit (blocks4 and the dense templates give
  each data patch one port per boundary type, so only ring offers a second one). It is checked
  against the routing graph
  before pruning (pruning drops unused ports, so afterwards no second port exists);
  `legacy_detection_rate` = share the old (non-strict) check catches.
- `fig_detection.pdf`.
