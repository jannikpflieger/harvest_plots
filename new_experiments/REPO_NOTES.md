# Repo notes for experiments E10–E14, E19, E20

Checkout: `harvest_magic_state_rust`, branch `harvest-rust`, HEAD `bbbc72a`
(Harvest with the Rust router, `HarvestConfig.backend = "rust"`,
`terminals = "route"`). Written 2026-10-29 before any run of this set.

## Earlier experiments (do not touch)

- `src/scripts/eval/` (`run_eval.py`, `plot_e1_sota.py` … `plot_e8_scaling.py`)
  and `experiments/eval/`: the earlier E1–E9 set. Not used, not modified.
- `src/scripts/rq/` + `results/rq/`: the RQ1–RQ5 pipeline the paper's current
  numbers come from. This set **reuses** its code (suite, placement cache,
  compilers, magic models, validator, crash-safe CSV runner) but writes only
  under `eval/new_experiments/`.

## Pipeline pieces

| Piece | Where |
|---|---|
| Circuit suite (130 RQ1 `core` circuits; 47-circuit `small` subset) | `results/rq/suite.csv`, built by `src/scripts/rq/prepare_suite.py` |
| One Harvest / EAF run (layout, placement, schedule, prune, validate) | `rq_common.run_in_tree` → `harvest/baselines/harvest.py` (`HarvestAdapter`), `harvest/baselines/silva.py` (`SilvaEAFAdapter`) |
| Template `auto` (best volume of ring / blocks4 / dense4 / dense4full) | `rq_common.run_auto` |
| Litinski / O3LS / PureMagic runs | `rq_common.run_external` → `harvest/baselines/{litinski,o3ls,puremagic}.py` |
| Magic-state models (instant, cultivation Exp(mean 3), …) | `rq_common.MODELS`, `harvest/baselines/cultivation.py` |
| Validator (V1 dependencies, V2 realizations, V3 disjoint resources per step, V4 magic state available) | `harvest/eval/validate.py`, called through `harvest.py:validate_run` before and after pruning |
| Pruning | `harvest/layout/pruner.py:prune_lattice` via `DAGProcessor.prune_after_scheduling` |
| Runner (crash-safe CSV, resume, OOM retry) | `rq_common.run_tasks`, `CsvLog` |

## Baselines and versions

| Tool | Code | Version |
|---|---|---|
| Harvest | in repo | `harvest-rust@bbbc72a` (+ the two hooks below) |
| EAF (Silva et al., TQC 2024) | in-repo reimplementation, `silva.py`, variant `silva_eaf_pruned` | no official code used |
| Litinski (Game of Surface Codes) | in-repo analytic model, `litinski.py` (paper released no compiler) | — |
| O3LS (Zhu et al.) | in-repo reimplementation, `o3ls.py` (no released code) | — |
| PureMagic | external Rust binary, `~/.cache/harvest-tools/PureMagic` | commit `f990c3e` (`tools.json` still labels it "QCE paper snapshot requested") |

## Area and volume (details with code citations: `E12_area_audit/audit_E12_E13.md`)

Volume = `area_tiles × T` for every tool.

- Harvest: tiles retained after pruning (used routing cells, used magic patches,
  every register qubit's data patch); not a bounding box.
- EAF: same layout and the same pruning (`prune=True` in RQ1).
- Litinski: closed-form block size plus port tiles.
- O3LS: full board + 1 port tile.
- PureMagic: its whole generated rectangle (data + bus + magic nodes, each one tile).

## Existing data reused

- RQ1: Harvest `auto` rows (this checkout), PureMagic rows
  (`harvest_magic_state_perf`), EAF / Litinski / O3LS rows (`harvest_magic_state`,
  EAF on blocks4). Seeds 42–51.
- RQ2–RQ5 (this checkout): 47-circuit subset, seeds 42–44.

## Timeouts

3600 s per (circuit, tool, config), as in the RQ scripts; recorded as `status=timeout`.
A worker killed twice (out of memory) is recorded as `status=crashed`.
