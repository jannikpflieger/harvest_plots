# Review numbers (no new runs)

Script: `src/scripts/rq/review_numbers.py`. Sources: HARVEST from `results/rq/rq1/rq1.csv`
(template `auto`), PureMagic from `harvest_magic_state_perf`, EAF / Litinski / O3LS from
`harvest_magic_state`; family `random` left out. Per circuit, values are means over the seeds;
a (compiler, model, circuit) counts only if all its runs completed. Geomeans are over the
circuits both compilers completed (`n_shared`); models are never pooled.

- `eaf_pruning.csv`: EAF pruned (`volume_pruned`) and unpruned (`volume_initial`) volume over
  HARVEST's (pruned) volume.
- `losses_summary.csv`: circuits where HARVEST's volume is higher than the baseline's
  (`rq1_view/rq1_losses.csv`, with its `cause`), per model and baseline; Pauli products = ops.
- `large_circuits.csv`: Ising n400-n440, wstate n118 / n380; outcome per run (completed /
  timed_out / crashed / failed; `not_run` = no row). T_cp = critical path (in Pauli-product
  layers), volume_norm = volume / (n_qubits * T_cp).
- `rq2_labels.md`: meaning of every RQ2 label.

Subset criterion: The RQ2-RQ4 subset (`small` tier, 47 circuits) is every core Ising circuit below 100 qubits plus, for every other family, the circuits with the minimum, median and maximum op count among its core circuits with 100-6,000 Pauli products (`prepare_suite.py`).
