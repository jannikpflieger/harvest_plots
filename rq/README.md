# results/rq (branch `harvest-rust`)

Data of the five research-question experiments, produced by
`src/scripts/rq/` on this branch (Harvest with the Rust router,
`HarvestConfig.backend = "rust"`, and the default `terminals = "route"`).
How the experiments are defined: `src/scripts/rq/README.md`. Current run
status: `src/scripts/rq/STATUS.md`.

Counts below are as of 2026-10-29, 15:15. The runs are still in progress;
the CSVs grow as trials finish.

## How the data was produced

- One systemd user unit (`harvest-rq-rust`) runs
  `src/scripts/rq/run_all.py --experiments rq1,rq2,rq3,rq4,rq5 --rq1-templates auto
  --skip-compilers eaf,litinski,o3ls,puremagic --jobs 4`.
  Trials run cheapest first in one worker pool.
- Every trial appends one or more rows to `<exp>/<exp>.csv` as soon as it
  finishes (`<exp>.lock` serialises writers). Rerunning the command skips
  every `run_key` already present. Rows with `status=error` are retried.
  A trial whose worker died twice is written as `status=crashed`.
- Only Harvest runs on this branch. The other compilers' RQ1 rows come from
  other checkouts (see `rq1_view/`).
- Every Harvest schedule is replayed through the validator (rules V1–V4)
  before and after pruning (`validated_pre`, `validated_post`,
  `n_violations`).
- Circuit suite: `suite.csv` (copied from the main checkout). RQ1 uses the
  `core` tier (130 circuits); RQ2–RQ5 use the `small` tier (47 circuits,
  2–98 qubits).

## Contents

### `rq1/` — Harvest on the RQ1 suite

- `rq1.csv`: 1,012 of 1,370 trials done (93 circuits so far, 2–98 qubits),
  all `status=ok`.
- Template `auto`: each trial is scheduled on ring, blocks4, dense4 and
  dense4full. The row is the run with the smallest volume, with
  `template_chosen`, every candidate's volume in `auto_volumes`, and
  `compile_time_s` summed over all four.
- Supply models:
  - `instant`: one run per circuit.
  - `cultivation` (mean 3 cycles per state): seeds 42–51 (3 seeds for
    n ≥ 400).
  - `cultivation_pm` (PureMagic's published rate): seed 42, for the Ising
    circuits with n ≥ 400 and every wstate size.
- Not yet run: the circuits of 64 qubits and more that are still queued
  (random 70–90q, qaoa/qft N64–99, square_heisenberg N64/N81, Ising
  n400–n440, wstate n118/n380).

### `rq1_view/` — snapshot with every compiler (made by hand, not by the runner)

- `rq1.csv`:
  - This branch's Harvest rows, restricted to circuits whose Harvest trials
    are complete per model.
  - PureMagic rows (both variants, all 3,200 trials) from
    `harvest_magic_state_perf/results/rq/rq1/rq1.csv`, rerun with the
    per-model work-directory fix.
  - EAF / Litinski / O3LS rows from the main checkout (old code; EAF on
    blocks4).
- Tables:
  - `rq1_table.csv/.tex`: Table 1.
  - `rq1_per_circuit.csv`: per circuit, compiler and model, the best
    variant's mean T, area and volume.
  - `rq1_losses.csv`, `rq1_family_advantage.csv`, `rq1_ising_large.csv`.
- Figures (`.png` + `.pdf`):
  - `fig1_family_volume`, `fig1_per_circuit_volume`, `fig2a_volume_decomposition`
  - `fig1_family_raw_{area,timesteps,volume}`
  - `fig1_{tiles,timesteps}_vs_size` (+ `_by_family_{instant,cultivation}`)
  - `fig1_geomean_bars`: geomean T, area and volume per compiler.
  - `fig1_by_size_{instant,cultivation}`: per circuit relative to Harvest,
    circuits sorted by size.
  - `fig1_ising_large_*`: empty until the n ≥ 400 circuits finish.
- Layout pictures, PureMagic's generated topology next to Harvest's `auto`
  layout after pruning (`src/scripts/rq/plot_layouts.py`):
  - `layout_<circuit>_<model>` for multiplier_n15, ising_n34, adder_n28,
    qft_N016, dnn_n16, square_heisenberg_N25, wstate_n36, knn_n25 (instant
    and cultivation).
  - `layouts_summary.csv`: tile counts by role, time steps and volume per
    picture.
- Rebuild with `python src/scripts/rq/rq1_view.py $PWD`.

### `rq2/` — ablation and sensitivity (complete)

- `rq2.csv`: 6,016 rows, 47 circuits, all `status=ok`.
- Ablation (4,512 rows):
  - Variants: `full`, `-negotiation`, `-retry`, `-admission`, `-matching`,
    `-priority`, `-placement`, `-yfactor`.
  - Templates ring / blocks4 / dense4; instant (one run) and cultivation
    (seeds 42–44).
  - Under the `route` default, `-matching` means terminals by Euclidean
    distance instead of the router's choice, and `-retry` means no greedy
    fill (the retry pass does not run for `route`).
- Sensitivity (1,504 rows): blocks4; I_max ∈ {0, 1, 2, 8}, α ∈ {1, 4},
  β ∈ {1, 3}, each against the defaults (I_max 4, α 2, β 1.5).
- Derived tables:
  - `rq2_ablation_summary.csv` (incl. `-pruning`, derived from the
    unpruned area).
  - `rq2_ratios.csv`, `rq2_sensitivity.csv`, `rq2_negotiation_cdf.csv`,
    `rq2_placement_by_template.csv`.
- Figures: `fig3_ablation`, `fig3_sensitivity`, `fig3_negotiation_cdf`.

### `rq3/` — schedule large, report small

- `rq3.csv`: 3,080 of 3,232 trials done (6,136 rows; each trial writes one
  `large` and one `direct` row), 45 of 47 circuits, all `status=ok`.
- Magic levels M ∈ {1, 2, 4, 8, 16, 32, all} × ring / blocks4 / dense4 ×
  instant + cultivation (seeds 42–44).
  - `large`: schedule on the full layout, with pruned and unpruned volume.
  - `direct`: reschedule from scratch on the pruned footprint.
- Derived: `rq3_summary.csv`, `rq3_levels.csv`, `rq3_removed_tiles.csv`.
- Figures: `fig4_provisioning`, `fig4_removed_tiles`.

### `rq4/` — magic-state supply models

- `rq4.csv`: 4,018 of 4,030 trials done (5,496 rows), 47 circuits, all
  `status=ok`.
- Ring layouts with M ∈ {1, 2, 4, 8, 16, 32, 64} magic patches
  (`layout` = `ring_m<M>`).
  - `aware`: scheduled under each of instant, dist4, dist10, cultivation,
    multiplexed and lognormal; seeds 42–44 for the stochastic models.
  - `oblivious`: the instant schedule replayed under dist4, dist10 and
    cultivation, with V4 violations of the unmodified schedule and the
    stall-inserted makespan.
- Derived: `rq4_curves.csv`, `rq4_curves_per_circuit.csv`,
  `rq4_oblivious_vs_aware.csv`, `rq4_pluggability.csv/.tex`.
- Figure: `fig5_magic_terminals`.

### `rq5/` — validity (complete)

- `rq5.csv`: 8,178 rows, 47 circuits, blocks4, instant + cultivation (seed 42).
  - `study=scheduler` (564 rows): 6 injected faults (`no_defer`,
    `reuse_terminal`, `skip_dep`, `early_consume`, `prune_used`,
    `drop_y_port`), with `fault_activations` and `caught`.
  - `study=corrupt_base` (94 rows): the unmodified schedule.
  - `study=corrupt` (7,520 rows): 20 random mutations per kind
    (`drop_dependency`, `overlap_route`, `disconnect_route`,
    `unavailable_state`).
  - `status=n/a` (980 rows) marks a mutation that cannot be applied, e.g.
    `unavailable_state` under instant supply.
- The census and scaling outputs read every schedule in `rq1`–`rq4`.
- Figures: `fig_rq5_faults`, `fig_rq5_scaling`, `fig_rq5_progress_bound`.
  `compile_time_s` includes the placement time stored in the placement cache.

### `cache/`

- `placement/`: symlink to the main checkout's cache of qubit-to-site
  assignments, one JSON per circuit, template and placement mode. Shared by
  every checkout and computed once.
- `trans/`: PureMagic input files (only written by `plot_layouts.py` on this
  branch).

## Column reference

Leading columns per experiment are each script's `COLUMNS`. Shared columns
(circuit features, T, area and volume before and after pruning, tiles by
role, compile time by phase, validator results, scheduler instrumentation)
are listed in `src/scripts/rq/README.md` under "Columns". Keys outside a
CSV's header are kept in `extra_json`. `rq_common.read_rows` merges them
back and keeps the newest row per `run_key`.
