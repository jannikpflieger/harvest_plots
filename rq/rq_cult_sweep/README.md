# Cultivation-delay sweep (HARVEST vs PureMagic)

Script: `src/scripts/rq/rq_cult_sweep.py`. `small` tier (47 circuits), HARVEST template `auto`,
PureMagic both variants (best mean volume per circuit, as RQ1) with `no_t_failures=True`;
exponential cultivation with mean 3 (`cultivation`), 10 (`cultivation10`) and 25.8 cycles
(`cultivation_pm`, PureMagic's published rate); seeds 42-51.

- `rq_cult_sweep.csv`: runs made here (`status` per run, HARVEST rows with strict-validator
  `paper_*` columns in paper numbering, every `auto` candidate pre/post pruning).
- `runs.csv`: every run used, `source` = new / reused:rq1 (HARVEST mean 3 and PM rate) /
  reused:E13 (PureMagic mean 3, flag on). Reused HARVEST rows take `paper_*` from
  `results/rq/revalidate/`.
- `per_circuit.csv`: means over the 10 seeds; a circuit counts only with all 10 runs ok.
- `summary.csv`: per mean delay, geomean PureMagic/HARVEST volume (p10, p90, wins), T and area
  ratios, T/T_cp and area per qubit per compiler. `scope=per_delay`: circuits complete at that
  delay (`n_shared`); `scope=common`: circuits complete at every delay. Models are never pooled.
- `fig_cult_sweep.pdf`: the `common` rows.
