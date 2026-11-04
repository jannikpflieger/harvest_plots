# Experiments E10–E14, E19, E20: report

Checkout `harvest_magic_state_rust` (branch `harvest-rust`, `bbbc72a`). Repo
summary: `REPO_NOTES.md`. Raw data: `<ID>_<name>/raw/<ID>.csv`.

## Executive summary

Status 2026-10-30 04:30:
- All new runs are complete (21,708; all `ok`).
- No validator violation in any Harvest or EAF run, before or after pruning.
- RQ1 Harvest is complete on all 120 circuits (two qft_N099 trials lost in
  the reboot were rerun at 04:28).
- The RQ1 EAF and O3LS baseline rows (main checkout, not part of this set)
  are still running. E11 and E12 count EAF on 99–110 and O3LS on 117–118 of
  the 120 circuits.

**Supported.**
- **Harvest + its framework has the lowest volume** on the RQ1 suite against
  all four baselines under the RQ1 accounting (retained tiles). The same
  holds with Harvest priced on its bounding box under instant supply, and
  for fast-to-moderate cultivation (E14, mean delay ≤ 5).
- Against EAF, Litinski and O3LS the lead holds in every accounting and
  template tested (E11, E12).
- **Harvest's scheduler beats EAF's on the same layout:** 1.02–1.07× in
  geomean (E10, held-out seeds). It is rarely worse, and the gain reaches
  ~1.2× on Ising, knn, wstate and swap_test (E10).
- **Pruning is robust to supply randomness** (E19). A layout pruned for one
  seed serves every other seed with no makespan loss.
- **The correction model does not matter** (E13): < 0.2% change, no ranking
  change.

**Weakened.**
- **"Harvest's scheduler is ~1.4× better than EAF"** is not supported. About
  1.33× of the RQ1 gap is the template (EAF runs blocks4, Harvest picks
  dense templates).
  - With EAF in Harvest's framework, the gap is 1.07× (instant) and 1.09×
    (cultivation) (E10).
  - With both on blocks4 it is 1.01–1.04× on all 120 circuits (E11).
- **The volume lead over PureMagic depends on the accounting, the supply
  rate and circuit size.**
  - With Harvest priced on its bounding box like the others, PureMagic is
    ahead under cultivation: 0.97×, 55 wins / 59 losses (E12).
  - With slower supply (mean delay > ~5.4 cycles), PureMagic wins (E14).
  - PureMagic is faster in makespan at every tested rate (E14) and on the
    RQ1 suite (T ratio 0.92–0.94).
  - On the 11 Ising circuits with ≥ 400 qubits, PureMagic beats Harvest by
    1.4–1.6× in volume; Harvest's makespan there is ~1.8× PureMagic's (E11).
- **Harvest with a single template does not beat PureMagic under
  cultivation:** dense4full 1.00×, blocks4 0.88× (E11). Against the best
  baseline per circuit, dense4full-Harvest is at 0.95× and blocks4-Harvest at
  0.83×. Per-circuit template selection carries the result.
- **Pruning itself contributes little:** 1.6–4% on `auto` (E10, E19). The
  large savings come from template choice.

**What the main claim should be.**
> A layout-aware framework (dense templates chosen per circuit by volume, plus
> post-scheduling pruning) reduces spacetime volume by ~1.3× over the
> blocks-style layouts of prior work. Harvest's scheduler adds a further
> 5–9% (up to ~20% on arithmetic, Ising and state-preparation circuits) over
> EAF's on identical layouts. Against PureMagic, Harvest is ahead in volume
> when magic-state supply is fast relative to consumption and on small to
> medium circuits; with slow supply, rectangle area accounting or large
> circuits, the two are comparable or PureMagic is ahead.

**Changes recommended for the paper.**
- RQ1 should show Harvest with a fixed template (dense4full) and EAF in the
  same framework (E10), or label the RQ1 EAF comparison as template +
  scheduler.
- State the area accounting explicitly. Give bbox numbers next to retained
  numbers.
- Show the cultivation-mean sweep (E14) or justify the mean of 3.
- Give the RQ3/RQ4 subset sizes per magic level (E20) instead of "37/38".

## Protocol (fixed before the first run, 2026-10-29 22:55)

- **Seeds.**
  - Tuning seeds 42–51: the RQ1 seeds. They were visible while Harvest was
    being changed (router-chosen terminals, template `auto`), so they count as
    tuning seeds.
  - Held-out seeds 1000–1009: never used before. Every new stochastic run of
    E10 and E14 uses them.
  - E19 compiles with seed A = 2000 and reschedules with the held-out seeds.
  - **Exception: E11, E12 and E13 use seeds 42–51** so that each Harvest row
    pairs with the existing baseline rows of RQ1. The baselines were not rerun
    on new seeds (EAF and O3LS cost hours). Their held-out counterparts are
    E10 (Harvest vs EAF) and E14 at mean 3 (Harvest vs PureMagic), both on the
    47-circuit subset.
- **Circuit sets.**
  - Subset: the 47-circuit `small` tier (RQ2–RQ5).
  - RQ1 set: the 130 `core` circuits minus the 10 random circuits = 120
    circuits. Random circuits were dropped by the authors on 2026-10-29, before
    this set; they appear as "not run" in E20.
- **Validator.** Runs on every Harvest and EAF output, before and after pruning
  (`validated_pre`, `validated_post`, `n_violations`). Any violation is a
  blocker.
- **Timeout.** 3600 s per (circuit, tool, config), as in the existing RQ
  scripts. A twice-OOM-killed worker is recorded as `crashed`.
- **Ties.** ±1% for W/T/L. "Win" always means the row's tool beats Harvest.

## Runtime estimate (written before starting)

| Exp | Runs | Estimate (CPU-h) | Basis |
|---|---|---|---|
| E10 | 4,136 (2,068 Harvest + 2,068 EAF) | ~6 | RQ2: Harvest ~1 s/run on the subset; RQ1: EAF ~10 s/run on blocks4 |
| E11 | 2,486 Harvest | ~8–12 | about half of the RQ1 `auto` cost (26 CPU-h incl. cached placement time) |
| E12 | 419 Harvest | ~1–2 | reruns of the ring / dense4 trials `auto` chose |
| E13 | 2,400 PureMagic | <1 | PureMagic ~0.1 s/run |
| E14 | 7,520 Harvest + 4,700 PureMagic | ~3 | as above |
| E19 | 47 × 11 Harvest | <1 | as above |

Total: about 20–25 CPU-h, run in one memory-capped pool (`harvest-newexp`, 2
workers, 4 GB) next to the still-running RQ1 and baseline jobs. That is more
than 6 h wall time. So the order is: smallest informative subset first (E10 on
47 circuits), then E11/E12/E13 below 400 qubits, then E14, E19, and last the
E11/E12 runs of the eleven 400+-qubit Ising circuits. Those need ~3.3 GB per
worker, and they get more memory once RQ1 finishes.

---

## E20 — failure and subset report

**Hypothesis.** None; bookkeeping.

**Setup.**
- `E20_failure_report/make_e20.py` reads `results/rq/suite.csv` and every RQ1
  CSV:
  - Harvest `auto` from this checkout;
  - PureMagic from `harvest_magic_state_perf`;
  - EAF, Litinski and O3LS from `harvest_magic_state`.
- It also reads the RQ2–RQ5 CSVs.
- The expected trials are the keys `rq1_sota.build_tasks` generates.
- No new runs.
- Snapshot updated 2026-10-30 04:35. RQ1 Harvest is complete; the EAF / O3LS
  baselines are still running. Rerun the script for the final table.

**Result.**
- **Outputs:**
  - `e20_status.csv`: one row per candidate circuit (338) with qubits,
    rotations (π/8 products), suite status and one status column per
    tool/config (RQ1) and per RQ2–RQ5.
  - `e20_summary.csv`: counts per tool/config.
- **Suite.**
  - 338 candidates: 130 `core` (RQ1), 172 `extra` (other qaoa/qft sizes and
    random seeds; never run), 26 Clifford-only (nothing to schedule), 8 failed
    to load (mid-circuit measurement/reset) and 2 over the T budget
    (e.g. factor247_n15, ~1.5M T).
- **RQ1 failures (snapshot 2026-10-30 04:35):**
  - EAF under cultivation: on random_90q_depth100_seed1 and _seed2, the
    first seed crashed twice (out of memory). The other 8 seeds are still
    to run.
  - O3LS `o3ls_min` crashed on ising_n412, cultivation, 1 of 3 seeds.
  - Everything else is ok or still running.
    - Still running: EAF 23 circuits (cultivation) and 12 (instant); O3LS 2.
  - Litinski and PureMagic: 130/130 ok in every config.
  - Harvest: 120/120 ok in every config.
    - Two qft_N099 trials were lost in the 2026-10-29 reboot and rerun on
      2026-10-30.
    - Harvest was not run on the 10 random circuits.
- **Subset criteria (exact):**
  - **47 (RQ2–RQ5).** `prepare_suite.py`: among usable `core` circuits, every
    Ising circuit below 100 qubits, plus per family the circuits with
    100 ≤ rotations ≤ 6000, sorted by rotations, of which the smallest, the
    median and the largest are kept. No random circuits qualify.
  - **37 and 38 (RQ3, RQ4).**
    - With the now complete RQ3/RQ4 data (redrawn 2026-10-29 23:00), all 47
      circuits enter both analyses.
    - Smaller counts appear only at high magic levels, because a template must
      offer at least M distinct magic patches for level M to exist.
    - **RQ3:**
      - blocks4: 47 circuits up to M = 16, 37 at M = 32, 26 at "all";
      - dense4: 47 up to M = 4, 37 at M = 8, 22 at M = 12;
      - ring: 45 at M = 32, 30 at "all".
    - **RQ4 (ring):** 47 up to M = 16, 45 at M = 32, 30 at M = 64.
    - **The paper's 37/38:** "37" matches RQ3's blocks4/32 and dense4/8
      levels. "38" does not occur in the current data.
    - **Stale counts.** The RQ3/RQ4 figures drawn earlier on 2026-10-29, while
      the largest circuits were still running, showed 37 circuits at every
      RQ3 level and 43 in RQ4. The main checkout's older RQ3/RQ4 tables give
      37/39 and 40–45. The paper's numbers probably come from such an
      incomplete snapshot; we cannot confirm which one.
    - **Recommendation.** The paper should state the per-level rule above
      instead of a single subset size.

**What it means for the paper.** RQ2–RQ4 use the same 47 circuits. The
per-level counts come from the template geometry, not from failures. No tool
silently drops circuits: every failure is a row.

**Caveats.** Snapshot while the EAF/O3LS baselines are still running; rerun
`make_e20.py` when `harvest-rq` finishes.

---

## E10 — framework vs. scheduler

**Hypothesis.** Harvest's volume advantage over EAF in RQ1 comes from Harvest's
scheduler. If instead it comes from the framework (template choice and
pruning), then EAF running inside the same framework should close most of the
gap.

**Setup.**
- Circuits: the 47-circuit subset.
- Schedulers:
  - Harvest;
  - EAF (`silva_eaf_pruned`, the same adapter and settings as RQ1), on the
    same layouts, placement cache, pruner and validator.
- Templates: ring, blocks4, dense4 and dense4full were all run.
  - `auto` = per run the template with the smallest volume, chosen separately
    for each pruning setting.
  - Reported layouts: blocks4 (RQ1's EAF setting), dense4full and `auto`.
- Pruning:
  - on = `volume_pruned`;
  - off = the same run priced on the unpruned layout (`volume_initial`), not
    a separate run.
- Supply:
  - instant (deterministic, 1 run);
  - cultivation Exp(mean 3) on held-out seeds 1000–1009.
  - For cultivation, per circuit the mean over the 10 seeds is used.
- Reference: full Harvest (Harvest, auto, pruning on). The ratio is
  config / reference, so > 1 means worse than Harvest.
- Data:
  - 4,136 runs, all `ok`;
  - 0 validator violations, before or after pruning;
  - wall time 01:20, 2026-10-30.
- Files: `e10_table.csv/.md`, `e10_per_circuit.csv`, `fig_e10_cdf.pdf`,
  `fig_e10_bars.pdf`.

**Result.** Volume relative to full Harvest, 47 circuits. W/T/L counts wins
for the row's config (±1% tie).

| Supply | Scheduler | Layout | Pruning | Geomean | W/T/L | p10 | p90 | T ratio | Area ratio |
|---|---|---|---|---|---|---|---|---|---|
| instant | Harvest | blocks4 | on | 1.393 | 0/0/47 | 1.21 | 1.60 | 0.98 | 1.42 |
| instant | Harvest | blocks4 | off | 1.895 | 0/0/47 | 1.39 | 2.54 | 0.98 | 1.93 |
| instant | Harvest | dense4full | on | 1.042 | 0/22/25 | 1.00 | 1.12 | 0.99 | 1.05 |
| instant | Harvest | auto | off | 1.041 | 0/27/20 | 1.00 | 1.08 | 1.00 | 1.04 |
| instant | EAF | blocks4 | on (= RQ1 EAF) | 1.425 | 0/0/47 | 1.26 | 1.64 | 1.07 | 1.34 |
| instant | EAF | blocks4 | off | 2.057 | 0/0/47 | 1.62 | 2.54 | 1.07 | 1.93 |
| instant | EAF | dense4full | on | 1.106 | 1/8/38 | 1.00 | 1.23 | 1.06 | 1.04 |
| instant | **EAF** | **auto** | **on** | **1.072** | 3/17/27 | 1.00 | 1.23 | 1.07 | 1.00 |
| instant | EAF | auto | off | 1.126 | 0/7/40 | 1.00 | 1.27 | 1.08 | 1.05 |
| cultivation | Harvest | blocks4 | on | 1.342 | 0/9/38 | 1.00 | 1.70 | 0.95 | 1.41 |
| cultivation | Harvest | blocks4 | off | 1.582 | 0/0/47 | 1.07 | 2.08 | 0.95 | 1.66 |
| cultivation | Harvest | dense4full | on | 1.113 | 0/29/18 | 1.00 | 1.59 | 1.18 | 0.94 |
| cultivation | Harvest | auto | off | 1.016 | 0/30/17 | 1.00 | 1.06 | 1.00 | 1.02 |
| cultivation | EAF | blocks4 | on (= RQ1 EAF) | 1.432 | 0/0/47 | 1.23 | 1.73 | 1.03 | 1.39 |
| cultivation | EAF | blocks4 | off | 1.707 | 0/0/47 | 1.34 | 2.09 | 1.03 | 1.66 |
| cultivation | EAF | dense4full | on | 1.160 | 0/11/36 | 1.00 | 1.63 | 1.23 | 0.94 |
| cultivation | **EAF** | **auto** | **on** | **1.086** | 2/12/33 | 1.00 | 1.26 | 1.10 | 0.99 |
| cultivation | EAF | auto | off | 1.106 | 0/11/36 | 1.00 | 1.33 | 1.10 | 1.01 |

The table omits dense4full with pruning off; it is in `e10_table.csv`.

**Scheduler alone.** EAF / Harvest on the same template, pruning on, per
circuit:

| Template | Instant | Cultivation |
|---|---|---|
| blocks4 | 1.023 (W/T/L 13/13/21, p10–p90 0.93–1.12) | 1.067 (9/10/28, 0.97–1.26) |
| dense4full | 1.061 (6/15/26, 0.98–1.23) | 1.042 (5/17/25, 0.99–1.11) |
| auto | 1.072 (3/17/27, 1.00–1.23) | 1.086 (2/12/33, 1.00–1.26) |

**Framework alone.**
- EAF on blocks4 / EAF on auto, both pruned: 1.330 for instant (0/1/46) and
  1.319 for cultivation (0/8/39).
- Pruning, Harvest auto: 4.1% for instant and 1.6% for cultivation. On
  blocks4 it is much larger (1.36× and 1.18×), because blocks4 has many
  unused magic and routing tiles.

**Where the scheduler matters** (EAF auto / Harvest auto, pruned):
- EAF is ≥ 10% worse on ising (1.20–1.22), knn (1.16–1.23), wstate
  (1.15–1.24), swap_test (1.17–1.21), multiplier (1.11–1.12) and adder
  (1.10–1.11).
- About half the families are tied (basis_change, basis_trotter, qaoa,
  vqe_uccsd, variational, …).
- EAF is better on qpe (0.94) and on pea under instant supply (0.91).

**Template choice.** `auto` picks similar templates for both schedulers:
dense4 or dense4full in nearly all cases, blocks4 in about 19% of
cultivation runs, and ring rarely.

**Seed variability (cultivation).** The median coefficient of variation of
volume over the 10 held-out seeds is about 1% for every config. The maximum
is 6–7% for `auto` and 12–13% for blocks4.

**What it means for the paper.**
- RQ1 compares Harvest (auto, pruned) with EAF (blocks4, pruned): a gap of
  1.43×.
- About 1.33× of that gap is the framework: template choice. Only 1.07–1.09×
  is Harvest's scheduler.
- Put EAF into Harvest's framework and it comes within 7% (instant) and 9%
  (cultivation) of full Harvest in geomean. It ties on about a third of the
  circuits and wins on 2–3.
- The scheduler's advantage is real and consistent: few wins for EAF, and
  p90 of 1.23–1.26. But it is concentrated in arithmetic, Ising and
  state-preparation circuits.
- The claim "Harvest's scheduler beats EAF by ~1.4× in volume" is not
  supported.
- The supported claim: the framework (volume-driven template selection plus
  pruning) gives ~1.3×, and on top of it Harvest's scheduler gives a
  further ~7–9%, up to ~20% on some families.

**Caveats.**
- Only the 47-circuit subset; large circuits are not covered. The scheduler
  gap may grow with size, since Ising, the biggest family, shows the largest
  gap.
- EAF is our reimplementation (no official code). Its cost model was not
  changed.
- Pruning off is computed by re-pricing the same schedule on the unpruned
  layout. It is not a run without pruning, but the schedule does not depend
  on pruning.
- `auto` for EAF picks with knowledge of all four EAF volumes; this is the
  same oracle-style selection Harvest's `auto` uses.

## E11 — fixed-template fairness

**Hypothesis.** RQ1 lets Harvest pick the best of four templates per run
(`auto`), while every baseline runs a single fixed configuration. If that
choice drives the result, Harvest fixed to one template should lose much of
its lead.

**Setup.**
- Harvest fixed to blocks4 (EAF's RQ1 template) and to dense4full.
- 120 RQ1 circuits; instant, and cultivation with seeds 42–51 (42–44 for
  n ≥ 400).
- The baselines are the unchanged RQ1 rows, with the same per-circuit "best
  variant" rule as RQ1 (`rq1_plots.per_circuit`).
- 2,486 runs, all `ok`; 0 validator violations.
- **Coverage.** All 120 circuits for Harvest, PureMagic and Litinski. EAF
  and O3LS are counted on fewer circuits because their RQ1 rows are still
  running: EAF 110 (instant) and 99 (cultivation), O3LS 117–118.
- Files: `e11_table.csv/.md`, `fig_e11_cdf.pdf`.

**Result.** Baseline volume / Harvest volume (> 1 = Harvest better); W/T/L =
baseline wins / ties / losses.

| Supply | Harvest | EAF | PureMagic | Litinski | O3LS | Best baseline per circuit |
|---|---|---|---|---|---|---|
| instant | auto (RQ1) | 1.410 (0/3/107) | 1.321 (14/1/105) | 1.930 (16/11/93) | 3.212 | 1.091 (30/15/75) |
| instant | dense4full | 1.332 (3/0/107) | 1.250 (14/2/104) | 1.826 (36/4/80) | 3.042 | 1.032 (53/6/61) |
| instant | **blocks4** | **1.037** (30/25/55) | **0.979** (61/3/56) | 1.430 (67/1/52) | 2.367 | **0.808** (102/4/14) |
| cultivation | auto (RQ1) | 1.423 (1/2/96) | 1.156 (30/0/90) | 2.153 (2/1/117) | 5.066 | 1.093 (31/3/86) |
| cultivation | dense4full | 1.334 (12/1/86) | **1.002** (33/0/87) | 1.867 (3/0/117) | 4.461 | **0.947** (36/0/84) |
| cultivation | **blocks4** | **1.040** (20/24/55) | **0.879** (84/6/30) | 1.636 (58/0/62) | 3.832 | **0.830** (102/4/14) |

**Large Ising circuits** (the 11 with ≥ 400 qubits, which came in last).
PureMagic beats Harvest `auto` clearly here:
- volume 0.73× (instant) and 0.64× (cultivation);
- T 0.58× and 0.55×, i.e. Harvest's makespan is about 1.8× PureMagic's;
- PureMagic's area is 1.17–1.26× larger.

These 11 circuits move the 120-circuit PureMagic geomean from 1.23 to 1.16
(cultivation).

**What it means for the paper.**
- **dense4full alone keeps the lead over EAF, Litinski and O3LS.** Against
  PureMagic it keeps 1.25× under instant supply, but is **level under
  cultivation (1.00×)**. The best baseline per circuit then beats it in
  geomean (0.95×). `auto` adds about 6–15% on top of dense4full (template
  choice per circuit).
- **On blocks4**, the template EAF uses:
  - Harvest and EAF are within 4% of each other.
  - PureMagic is slightly better under instant supply (0.98×) and **12%
    better than Harvest under cultivation** (84 wins).
  - The best baseline per circuit beats blocks4-Harvest on 102 of 120
    circuits.
- **Large circuits are a weak spot.** On Ising with ≥ 400 qubits, Harvest's
  makespan is about 1.8× PureMagic's under both supply models, which costs
  1.4–1.6× in volume. The paper should not claim scaling advantages there.
- **The layout carries the volume result.** This confirms E10 on all 120
  circuits: Harvest's lead comes mostly from the dense templates (fewer
  idle tiles after pruning), not from scheduling on a given layout.
- **RQ1 should report Harvest with a fixed template** (dense4full) next to
  `auto`. The "EAF on blocks4" comparison mainly measures template choice
  and should be labelled that way. Running EAF on dense4full or `auto` too
  (as in E10) would make RQ1 a fair scheduler comparison.

**Caveats.**
- EAF and O3LS are on fewer circuits until their RQ1 runs finish.
- Seeds 42–51, chosen to pair with RQ1; see Protocol. The 400+-qubit
  circuits use seeds 42–44, as in RQ1.
- The volume numbers count retained tiles, as in RQ1; E12 shows how a
  rectangle accounting narrows the margins further.

## E12 — area accounting audit

**Audit (done).** Full table with code citations:
`E12_area_audit/audit_E12_E13.md`. Volume = `area_tiles × T` for every tool.

| Compiler | `area_tiles` counts | Magic patches | Unused tiles counted? |
|---|---|---|---|
| Harvest | tiles retained after pruning (used routing cells, used magic patches, all register data patches) | 1 tile each, only if used | no (pruned) |
| EAF | same layout and pruning as Harvest | same | no (pruned) |
| Litinski | closed-form block (compact 1.5n+3, intermediate 2n+4, fast 2n+√(8n)+1) + port tiles | 1 (instant); 1–3 sized to the block (cultivation) | yes (whole block) |
| O3LS | full board + 1 port tile | 1 | yes (whole board) |
| PureMagic (bus, magic routing) | its whole generated rectangle: data + bus + magic nodes | every non-data tile in the magic-routing variant is a dual-purpose magic/route node, counted once | yes (whole rectangle) |

- **Asymmetry.** Only Harvest and EAF are priced on a pruned footprint, and
  pruned tiles leave holes that are not counted. The other three report a
  rectangle or block. `auto` also selects the template by post-pruning volume.
- **What is being measured.** For Harvest, the retained-tile area vs the
  bounding box of the pruned layout. E11 and E12 runs record
  `area_bbox_pruned`.

**Hypothesis.** Harvest's RQ1 volume lead partly comes from counting only
retained tiles, while the other tools report full rectangles. Pricing Harvest
on a rectangle should shrink the lead.

**Setup.**
- Every RQ1 Harvest `auto` trial is rerun with its chosen template and seed,
  and the bounding box of the pruned layout is measured.
  - ring and dense4 trials: rerun in E12 (419 runs);
  - blocks4 and dense4full trials: rerun in E11.
- Every rerun reproduces the RQ1 volume exactly: 1,243/1,243 trials
  (`e12_reproduction.csv`).
- Three Harvest accountings:
  - **retained:** as in RQ1;
  - **bbox:** bounding box of the pruned layout × T;
  - **unpruned:** all non-blocked tiles of the chosen template × T.
- The baselines are unchanged from RQ1. EAF stays at retained tiles in all
  three rows; "EAF (unpruned)" is EAF on all its layout tiles.
- 0 validator violations.
- All 120 circuits for Harvest, PureMagic and Litinski. EAF and O3LS are
  counted on fewer circuits because their RQ1 rows are still running (EAF
  110/99, O3LS 117/118).
- Files: `e12_table.csv/.md`, `e12_trials.csv`, `fig_e12_cdf.pdf`.

**Harvest area under the three accountings** (geomean over trials):

| | bbox / retained | unpruned / retained | bbox / unpruned |
|---|---|---|---|
| instant | 1.213 | 1.084 | 1.119 |
| cultivation | 1.205 | 1.065 | 1.132 |

The bounding box is larger than the full unpruned template in 82–89% of the
trials. The dense templates have blocked cells, so even the unpruned count is
not a rectangle.

**Result.** Baseline volume / Harvest volume (W/T/L = baseline wins vs Harvest).

| Accounting (Harvest) | Supply | EAF | PureMagic | Litinski | O3LS | Ranking |
|---|---|---|---|---|---|---|
| retained (RQ1) | instant | 1.410 (0/3/107) | 1.321 (14/1/105) | 1.930 (16/11/93) | 3.212 | H < PM < EAF < Lit < O3LS |
| retained (RQ1) | cultivation | 1.423 (1/2/96) | 1.156 (30/0/90) | 2.153 (2/1/117) | 5.066 | H < PM < EAF < Lit < O3LS |
| **bbox** | instant | (1.151)* | **1.090** (25/11/84) | 1.593 (57/3/60) | 2.642 | H < PM < EAF < Lit < O3LS |
| **bbox** | cultivation | (1.162)* | **0.970** (55/6/59) | 1.807 (19/7/94) | 4.238 | **PM < H** < EAF < Lit < O3LS |
| unpruned | instant | 1.293 | 1.218 (19/1/100) | 1.781 (27/10/83) | 2.960 | H < PM < EAF < Lit < O3LS |
| unpruned | cultivation | 1.324 | 1.087 (33/0/87) | 2.025 (6/1/113) | 4.759 | H < PM < EAF < Lit < O3LS |

\* EAF priced on retained tiles against Harvest on its bbox: not a like-for-like
comparison. Like-for-like, both on the bbox: on the 47-circuit subset (E10,
`e12_subset_eaf_bbox.csv`), EAF's bbox/retained factor is 1.229 (instant) and
1.205 (cultivation), the same as Harvest's (1.222 and 1.196). EAF vs Harvest
is therefore about **1.4× in all three accountings** (estimate: 1.15 × 1.23
≈ 1.41 and 1.16 × 1.205 ≈ 1.40). Both run on the same layouts, so the
accounting cancels. "EAF (unpruned)" vs Harvest unpruned is 1.86 (instant)
and 1.67 (cultivation). The ranking in the bbox rows places EAF by this
like-for-like estimate.

**What it means for the paper.**
- Against the tools that report a rectangle (PureMagic, Litinski, O3LS), part
  of Harvest's lead comes from the accounting.
- With Harvest also priced as a rectangle (bbox):
  - **PureMagic:**
    - instant: shrinks from 1.32× to 1.09×;
    - cultivation: **flips from 1.16× to 0.97×**. PureMagic has the lower
      geomean volume and wins on 55 of 120 circuits (59 losses).
    - Under cultivated supply the two are at parity, with PureMagic slightly
      ahead.
  - **Litinski** (instant) stays at 1.59× geomean, but it wins on 57 of 120
    circuits. The geomean comes from a long tail (p90 8.4×).
- Harvest stays first in every accounting except bbox + cultivation, where
  PureMagic is first.
- Options for the paper:
  - report the bbox numbers next to retained, or
  - state clearly that Harvest's area counts only retained tiles, i.e. it
    assumes pruned tiles can be reused, which a fixed chip cannot do. E19
    shows that the pruned shape is stable across seeds, so this is a fixed
    footprint; the question is only whether holes count.
- Main claim vs PureMagic under cultivated supply: "comparable volume", not
  "1.16× better".

**Caveats.**
- EAF and O3LS are on fewer circuits until their RQ1 runs finish.
- Seeds 42–51, chosen to pair with RQ1; see Protocol.
- The bbox is one possible rectangle. A tool could pack the pruned tiles more
  tightly; the bbox is an upper bound on what a rectangle needs.
- The baselines were not re-priced with pruning; giving them pruning would
  need changes to their models, which was not done.

## E13 — Clifford-correction parity

**Audit (step 1, done).** Details and citations:
`E12_area_audit/audit_E12_E13.md`.

| Tool | Models the π/4 correction? | How | Enabled in our runs? |
|---|---|---|---|
| Harvest | no | 1 step + 1 magic state per π/8 product | — |
| EAF | no | 1 step per product | — |
| Litinski | no (stated: "Clifford corrections are commuted forward and cost no time", `litinski.py:11-13`) | — | — |
| O3LS | no (π/8 = one P⊗Z measurement, frame absorbed, `o3ls.py:36-39`) | — | — |
| PureMagic | yes, unless `--no-t-failures` | 50% coin per T (`PM scheduler.rs:1274-1315`). On failure a per-qubit S power is tracked, which relabels the basis of later T gates on that qubit and so changes their routing. No extra correction cycle is scheduled: our input has no explicit S products, and pending corrections at the end are not paid. | instant: off. cultivation and `cultivation_pm`: **on** |

**Mismatch.** Under cultivated supply PureMagic carried a correction model
that no other tool, Harvest included, carries. Its RQ1 cultivation numbers are
therefore slightly pessimistic for PureMagic.

**Step 2 (cheap fix, running).**
- Rerun PureMagic (both variants) under cultivation with `--no-t-failures`,
  same seeds 42–51, on the RQ1 set. The rerun is enabled by
  `run_external(..., no_t_failures=True)`; the default is unchanged.
- The flag only skips the coin flip. Cultivation draws use a separate random
  stream, so supply times per seed are unchanged.
- No Harvest correction model is needed.

**Hypothesis.** Removing PureMagic's correction model shortens its makespan,
so RQ1 under-reports PureMagic under cultivated supply.

**Setup.**
- 120 RQ1 circuits × {puremagic, puremagic_bus} × seeds 42–51, cultivation.
- Each run is paired with the RQ1 run of the same seed (correction on).
- 2,400 runs, all `ok`.
- Files: `E13_clifford_parity/e13_paired.csv`, `e13_table.csv/.md`,
  `fig_e13_cdf.pdf`.

**Result.**
- **Area.** Unchanged in all 2,400 pairs.
- **Makespan, T(off) / T(on), per circuit (mean over seeds):**
  - puremagic: geomean 0.999, W/T/L 2/116/2;
  - puremagic_bus: geomean 0.999, W/T/L 3/117/0;
  - p10–p90 0.996–1.002 for both variants.
- **Makespan, per run:**
  - median 1.000, std 0.007, range 0.946–1.047;
  - 152 runs are > 1% faster and 85 are > 1% slower.
  - The coin flips change which routes are used, so the effect goes in both
    directions. The adder_n28 example from the audit (128 → 122) was one of
    the larger draws, not the typical case.
- **Effect on the RQ1 comparison.**
  - PureMagic (best variant) / Harvest `auto`, cultivation: 1.156 with the
    correction (RQ1), 1.155 without (E13).
  - W/T/L 30/0/90 → 28/2/90.
  - PureMagic is faster than Harvest on 78 → 76 circuits.

**What it means for the paper.** The correction mismatch is real but has no
effect on the results: under 0.2% in geomean, and no ranking change. The RQ1
PureMagic numbers can stay as they are. The paper should state in one
sentence that no tool pays for π/4 corrections and that PureMagic's optional
tracking was checked to change T by < 0.2%. No Harvest correction model is
needed.

**Caveats.**
- Seeds 42–51, chosen to pair with RQ1; see Protocol.
- The flag only removes the basis relabeling. PureMagic never schedules
  explicit correction cycles in our inputs, so this experiment does not say
  what a tool that pays for corrections would cost.

## E14 — cultivation parameter sensitivity

**Hypothesis.** Harvest's lead over PureMagic under cultivated supply (RQ1:
mean delay 3 cycles) holds for other mean delays.

**Setup.**
- 47-circuit subset, Exp(mean m) cultivation delay with m ∈ {1, 2, 3, 5, 8},
  held-out seeds 1000–1009.
- Harvest `auto` = per run the best of its four templates. The m = 3 runs are
  reused from E10.
- PureMagic: per circuit the better of its two variants (as in RQ1), with
  correction tracking on (RQ1 setting; E13 shows it does not matter).
- 9,400 Harvest and 4,700 PureMagic runs, all `ok`; 0 validator violations.
- Ratio = PureMagic / Harvest, per circuit mean over 10 seeds.
- Files: `e14_table.csv/.md`, `e14_per_circuit.csv`, `fig_e14_cdf.pdf`,
  `fig_e14_ratio_vs_mean.pdf`.

**Result.**

| Mean delay | Volume PM / H | W/T/L (PM) | p10–p90 | T ratio | Area ratio | PM faster on | Seed CV (median) H / PM |
|---|---|---|---|---|---|---|---|
| 1 | 1.244 | 8/1/38 | 0.85–1.52 | 0.959 | 1.297 | 19 | 0.4% / 0.2% |
| 2 | 1.185 | 12/0/35 | 0.85–1.47 | 0.955 | 1.241 | 30 | 0.7% / 0.2% |
| 3 | 1.128 | 13/0/34 | 0.84–1.36 | 0.953 | 1.184 | 33 | 0.9% / 0.3% |
| 5 | 1.019 | 23/1/23 | 0.80–1.33 | 0.885 | 1.147 | 38 | 1.2% / 0.3% |
| 8 | **0.882** | **31/1/15** | 0.66–1.19 | 0.914 | 0.959 | 28 | 1.1% / 0.5% |

Absolute geomeans:
- Harvest T: 600 → 691 cycles from m = 1 to 8; area: 56 → 76 tiles.
- PureMagic T: 575 → 632; area: constant at 73 tiles.
- `auto` shifts from dense4 at m = 1 (290 of 470 runs) to blocks4 at
  m = 8 (275 of 470). Blocks4 offers more magic ports; that is the source of
  the area growth.

**Crossover.** PureMagic's volume ratio falls steadily with the delay. Parity
(geomean 1.0) is at **m ≈ 5.4 cycles** (interpolated between m = 5 and 8). At
m = 5 the circuits split evenly (23/23). At m = 8 PureMagic is 12% better and
wins on 31 of 47.

**What it means for the paper.**
- Harvest's volume lead under cultivation **depends on the supply rate**.
  It is 24% at fast supply and shrinks to zero around a 5-cycle mean delay.
  PureMagic wins at slower supply.
- PureMagic is faster in makespan (T) at every rate. Harvest's lead comes
  from area only.
- When supply is slow, Harvest adds magic ports to keep T down (blocks4),
  which costs area. PureMagic keeps a fixed footprint and accepts waiting.
- The cultivation mean of 3 used in RQ1 is in the range where Harvest wins.
  The paper should either
  - justify the choice of 3 physically, or
  - show this sweep and state the regime: "Harvest wins in volume when the
    magic supply is fast relative to consumption".
- On the held-out seeds at m = 3, PureMagic / Harvest is 1.128 on this
  subset. The RQ1 tuning-seed value on all 120 circuits is 1.156 (E13); the
  difference comes from the circuit set as well as the seeds.

**Caveats.**
- 47-circuit subset only.
- Exponential delay only; no lognormal.
- EAF was not part of the sweep.
- PureMagic's sampler allows 0-delay draws, while Harvest's delay is at
  least 1 (see audit). This gives PureMagic slightly faster supply at every
  m, most at m = 1.
- Volume counts retained tiles. Under the E12 bbox accounting the crossover
  would move to a shorter delay.

## E19 — robustness of pruning under stochastic supply

**Hypothesis.** A layout pruned after one cultivation outcome (seed A) still
works for other outcomes. If pruning removes tiles that other seeds need,
then rescheduling on the fixed pruned layout costs makespan.

**Setup.**
- 47-circuit subset, cultivation with mean delay 3.
- Seed A = 2000: `auto` picks a template, Harvest schedules and the layout is
  pruned.
- That pruned layout (`rq3_provisioning.right_sized_layout`) is then fixed.
  Harvest reschedules on it with held-out seeds B = 1000–1009.
- Reference: the E10 run with the same template and seed B on the full
  layout.
- 517 runs, all `ok`. 0 validator violations: every schedule on the fixed
  layout is valid.
- Files: `e19_pairs.csv`, `e19_table.csv/.md`, `fig_e19_cdf.pdf`.

**Result.**

| Metric | Value |
|---|---|
| Makespan, fixed pruned layout / full layout (per circuit, geomean) | 1.000 (W/T/L 0/47/0) |
| Max makespan ratio over all 470 (circuit, seed) pairs | 1.0005 |
| (circuit, seed) pairs with makespan +> 1% | 0 |
| Volume, fixed pruned layout / full layout pruned per seed B | 1.001 (1/44/2) |
| Volume, fixed pruned layout / full layout unpruned | 0.983 (15/32/0, p10 0.94) |
| Median seed CV of the fixed-layout volume | 0.8% |

**What it means for the paper.**
- Pruning is robust to the supply randomness. A layout pruned for one seed
  serves every other seed with no measurable loss in makespan, and its
  volume equals that of per-seed pruning.
- So pruning can be done once, ahead of time; it does not need the seed of
  the actual run. This supports treating the pruned area as a real hardware
  footprint (see E12 for the rectangle question).
- Pruning removes little under cultivation: 1.7% of the volume in geomean
  and at most ~6% (p10). That matches E10, where pruning gives 1.6% on
  `auto`. The large savings come from template choice, not from pruning.

**Caveats.**
- 47-circuit subset, mean delay 3 only.
- One seed A.
- Rescheduling uses the same router, so it naturally prefers the same tiles.

---

## Code changes (all opt-in; defaults unchanged)

- `src/scripts/rq/rq_common.py`:
  - `CSV_PATHS` registry so experiments outside `results/rq` keep their CSVs
    elsewhere;
  - `run_external(..., no_t_failures=None)`: PureMagic override for E13; the
    work directory is separate when it is set.
- `src/harvest/baselines/silva.py`: EAF passes its (pruned) processor to the
  caller's `sink`, as the Harvest adapter already did. This is measurement
  only, for the bounding box.
- `eval/new_experiments/`: runner, task builders and analysis scripts.

No Harvest scheduler behavior was changed, and no baseline setting was changed
except PureMagic's `--no-t-failures` in E13.
