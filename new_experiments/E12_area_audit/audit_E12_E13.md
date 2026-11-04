# Audit E12 (area accounting) / E13 (Clifford-correction parity): RQ1

Repo: `harvest_magic_state_rust` (branch harvest-rust, HEAD bbbc72a, clean). Paths are relative to the repo unless they start with `PM:`, which means `/home/jannik/.cache/harvest-tools/PureMagic` (commit f990c3e, clean tree).
Read-only audit: no repo file was changed.

## Common plumbing

- CSV columns come from `src/harvest/eval/collect.py:89-95`:
  - `area_tiles` = `result.logical_patches`
  - `volume_tile_cycles` = `result.space_time_volume`
  - `area_initial_tiles` / `area_pruned_tiles` = `initial_logical_patches` / `post_pruning_logical_patches`
- Volume = patches × schedule length (`src/harvest/baselines/metrics.py:11-19`).
- The per-type split (`{routing,magic,data}_tiles_{initial,pruned}`) exists only for in-tree runs. It is read from `metadata.area` (`collect.py:123-126`).
- RQ1 variants:
  - PureMagic `("puremagic_bus", "puremagic")`, Litinski compact/intermediate/fast, O3LS min/medium/large (`src/scripts/rq/rq1_sota.py:28-32`).
  - Harvest/EAF template defaults to `blocks4` (`rq1_sota.py:117-119`).
  - The current harvest_rust `results/rq/rq1/rq1.csv` holds only Harvest rows with `template=auto`. `auto` takes the min-volume template out of ring/blocks4/dense4/dense4full (`rq_common.py:62, 361-393`).
  - The main checkout's rq1.csv holds all compilers on `blocks4`.

## E12: area accounting per compiler

| Compiler | `area_tiles` = | Kind | Magic/cultivation patches | Routing tiles | Code |
|---|---|---|---|---|---|
| **Harvest** | retained routing cells + retained patch tiles + every register qubit's data patch | **retained count after pruning**, not a bounding box | 1 tile per magic patch (`magic_patch_1cell`), counted only if its M-port was used by some route. No cultivation footprint beyond that 1 tile | counted only if some Steiner tree used the cell | `baselines/harvest.py:18-37, 136-140, 191-192`; `eval/instrument.py:32-47`; `layout/pruner.py:84-153` |
| **EAF** (in-repo, Silva et al. TQC 2024) | identical to Harvest: same placed layout, and `prune=True` is forced in RQ1 | retained count | same as Harvest (only used storage sites) | used cells only | `rq_common.py:339-340`; `baselines/silva.py:351-359, 405` |
| **Litinski** compact / intermediate / fast (in-repo analytic model) | closed form 1.5n+3 / 2n+4 / ceil(2n+√(8n)+1), plus magic port tiles | formula (data block incl. its internal routing) | instant: +1 tile (`MAGIC_PORT_TILES`). Cultivation: +ceil(mean/worst-case steps) ports, i.e. 1/1/3 for mean 3. No distillation/cultivation footprint | inside the block formula | `baselines/litinski.py:53-60, 84-95, 147, 186-193` |
| **O3LS** min / medium / large (in-repo reimpl.) | board rows×cols + 1 | **full board rectangle** (data, ancilla A, all routing) | 1 port tile in both models; cultivation adds no ports | all board tiles | `baselines/o3ls.py:67, 849, 858` |
| **PureMagic** bus (`puremagic_bus`, no `--use-magic-routing`, `--ancilla-rows 1`) | native `total` = data + bus + magic nodes | **full generated rectangle** (n_cols × n_rows) | every magic node counts 1 tile: the border ring plus unused data slots | every bus node | adapter `puremagic.py:375-391, 435, 473`; `PM:src/topograph.rs:91-96, 247-263, 435-474, 608-632` |
| **PureMagic** magic-routing (`puremagic`, `--use-magic-routing`, `--ancilla-rows 1`) | same `total` | **full rectangle** | every non-data tile is a Magic node and counts once as 1 tile. These dual-purpose ancilla/cultivator tiles are not double-counted | same tiles as the magic nodes | `puremagic.py:386-387`; `PM:src/topograph.rs:97-98, 512-553` |

Details:

- **Harvest: what pruning removes.** `prune_lattice` keeps only graph nodes listed in some result's `steiner_nodes`, `magic_terminal` or `qubit_terminals` (`pruner.py:84-97, 127-153`). It removes:
  - routing cells that were never used;
  - unused magic ports, and with them their magic patches;
  - every data-patch port that was never used.
- `processor_patch_count` then adds back the data patch `q_i` of every **register** qubit i < num_qubits, even if no product touched it (`harvest.py:27-36`).
- So the unbound layout slots `q_i` with i ≥ n stay pruned.
- Degree-0 routing cells were already dropped when the routing graph was built (`layout/engine.py:180, 193-225`), but `initial_area` still counts them (`instrument.py:21-29`, `W*H - blocked - magic - data`).
- **The 412-vs-440 case.**
  - For blocks4, `build_layout` uses ceil(412/4)=103 blocks → cols=ceil(√103)=11, rows=10 → 110 blocks = **440 data slots** (`src/scripts/compare_sota_baselines.py:183-186, 202-203`; `layout/presets.py:165-186`).
  - The 28 slots q_412..q_439 hold no qubit. Their ports are never used, so they are pruned → `data_tiles_pruned` = 412.
  - Checked against ising_n412 (harvest_rust rq1.csv, cultivation seed 42, chosen template blocks4): initial 1188 = 36×33 (W=3·11+3, H=3·10+3); data 440→412; magic 130→130; routing 618→614.
  - The 4 lost routing tiles are the four corner cells, which have no free neighbour.
- **Is `area_tiles` a bounding box for Harvest?** No. It is the retained-tile count (`harvest.py:191`, `logical_patches=post_patches`).
  - Holes are not counted: here the 28 empty slots, plus any unused routing cells inside the hull.
  - `area_initial_tiles` = W·H − BLOCKED is the template rectangle (`harvest.py:12-15`). That is the only rectangle-type figure.
- **Existing bounding-box code:** none for Harvest/EAF. A grep for `bounding|bbox` finds only matplotlib `bbox_inches`, the A* heuristic comment at `engine.py:292`, and the LSQCA bank shape at `baselines/lsqca.py:161` (LSQCA is not in RQ1).
- **PureMagic geometry.** Each grid cell with data holds the X (or Z) node of 2 qubits, and `data_count/2` makes 1 tile per logical qubit (`topograph.rs:557-582, 259-260`).
  - For odd n, `max_qi = 2n+1` adds one padding data tile (`topograph.rs:448, 527`).
  - Checked for n=412 (main rq1.csv):
    - magic-routing: n_rows=31, n_cols=43 → **1333**;
    - bus: n_cols=45, n_rows=33 → **1485** (= 412 data + 917 bus + 156 magic by hand count).
  - Both match the CSV.
- **Litinski and O3LS cross-check (n=412).**
  - Litinski: compact 621+1=622, intermediate 829, fast 883+1=884 (instant) / 883+3=886 (cultivation). All match the CSV.
  - O3LS is the board plus 1 (730 / 1123 / 1483).

**Asymmetries that could bias the comparison:**

1. **Pruning helps only Harvest and EAF.** Litinski, O3LS and PureMagic report their whole block, board or rectangle, including unused routing and magic tiles. Harvest/EAF report used tiles only and leave out holes.
   - ising_n412 blocks4: Harvest 1188→1156 (−2.7%); EAF instant 1188→1094 (−7.9%, only 90 of 130 magic ports used).
   - The effect is larger for `dense4full`, which is designed to over-provision ports and prune the unused ones (`rq_common.py:49-53`), and for `auto`, which picks by post-pruning volume (`rq_common.py:385`).
   - The adapter does not parse PureMagic's used-node counts (`puremagic.py:116-183`), so no equivalent pruned PureMagic number is available.
2. **Retained count vs. rectangle.** A pruned Harvest footprint is not a rectangle, but the PureMagic/O3LS footprints are. Harvest's bounding box would be ≥ `area_tiles` (for the n=412 case it is 1188 vs 1156).
3. **One tile per magic port everywhere.** No compiler charges a cultivation or distillation footprint beyond 1 tile, so this part is symmetric.
   - But PureMagic magic-routing makes all 921 non-data tiles cultivators at 1 tile each, while Harvest has 130 ports (blocks4) and O3LS has 1.
   - Supply capacity per tile therefore differs a lot between tools. That is a modelling choice of each tool, not an accounting bug.
4. **Litinski is a closed form.** It has no routing to ports outside the block and assumes the port is adjacent.
5. **Harvest counts every register data patch.** Idle qubits are kept (`harvest.py:21-30`). This matches the external tools, which always place all n qubits, so it is not a bias.

## E13: π/4 correction after π/8 injection

| Tool | Models correction? | How | Enabled: instant | Enabled: cultivation | Code |
|---|---|---|---|---|---|
| Harvest | **No** | each routed product takes one time step and consumes one magic state. No 50% branch and no extra step or route. A grep for correction/clifford/failure in `src/harvest/routing`, the validator and the Rust router finds nothing relevant | n/a | n/a | `routing/scheduler.py:1139-1148, 1188` |
| EAF | **No** | 1 step per op | n/a | n/a | `baselines/silva.py:181-231` |
| Litinski | **No (explicit)** | "Clifford corrections are commuted forward and cost no time". π/8 cost is per the block rules only | n/a | n/a | `baselines/litinski.py:11-13, 105-118` |
| O3LS | **No (explicit)** | π/8 = 1-step P⊗Z measurement, "auto-correction/Clifford frame absorbed". The π/4 rotations it does schedule come only from Y-synthesis | n/a | n/a | `baselines/o3ls.py:36-39, 770, 704-708` |
| PureMagic | **Yes, when T failures are on** | 50% coin per scheduled T (`scheduler.rs:1286`). On failure, a per-qubit S-power counter in the T's basis is incremented (`:1299-1305`). See the cost bullets below | **off** (`--no-t-failures`) | **on** (no flag; also on for `cultivation_pm`) | `rq_common.py:419`; `puremagic.py:390-391`; `PM:src/scheduler.rs:1274-1315` |

**What a PureMagic T failure costs:**

- **No recovery lcycle.** "T gates complete in one lcycle regardless of outcome … no recovery lcycle is needed" (`scheduler.rs:1274-1278`).
- **Effect A: conjugated later T gates.** A pending odd power conjugates the bases of later T gates on that qubit (X↔Y etc.), which changes their terminals and routing (`scheduler.rs:609-664, 1063-1083`).
  - For example, a Y operator needs both the X and Z nodes.
  - The change can make routing harder or easier.
- **Effect B: a physical S gate.** It costs routing and lcycles, and fires only before an explicit S/SX Clifford product on that qubit (`scheduler.rs:870-930`; merge path `955-1001`; trigger `1035-1061`).
- **Our inputs never trigger Effect B.** `pauli_dag_to_trans` emits only `<T>` (and `<M>`) lines (`puremagic.py:79-101`), so there are no S/SX products.
  - The "S correction gates" line is never printed (`PM:src/puremagic.rs:145`).
  - Corrections still pending at the end are never paid: the loop exits when `pps_pending` is empty (`scheduler.rs:335`).
- **Net effect in our cultivation runs:** only the basis re-labelling of later T gates (Effect A). No extra correction cycles are charged.
- **Observation (PureMagic's simplification, not ours):** for a multi-qubit P, the correction of a failed P-rotation is exp(±iπ/4·P). PureMagic instead tracks independent single-qubit S powers on each qubit of P (`scheduler.rs:1301-1305`).

**Can PureMagic turn this off under cultivation?** Yes: pass `no_t_failures=True` together with `magic_state_lambda=1/3`. In code, change `"no_t_failures": model == "instant"` at `rq_common.py:419`. The CLI accepts the combination (`PM:src/utils.rs:18-24`).

What else the flag changes:

- (a) It short-circuits the only use of `rng_uniform` (`scheduler.rs:260, 1286`).
  - Cultivation times come from a separate `rng_exp` pool (`PM:src/cultivation.rs:15, 31, 43-54`), so the cultivation draw sequence per seed is unchanged.
  - Which node receives which draw can still differ once the schedule diverges.
- (b) It changes the printed "Volume estimate / Normalized scheduling efficiency" lines (`puremagic.rs:156-167`; `circuit.rs:471`). The adapter does not parse these: it reads only "Scheduled … logical cycles, volume", the banner and "Number of qubits" (`puremagic.py:144-170`).
- (c) It flips metadata `t_injection_failures` (`puremagic.py:490-492`).
- Nothing else reads the flag (grep).

## Record: baseline versions and cultivation handling

| Baseline | Version / provenance | Cultivation model handling |
|---|---|---|
| PureMagic | external, BQSKit/PureMagic (`origin https://github.com/BQSKit/PureMagic.git`), commit **f990c3eca0ed** (2026-09-12), built at `target/release/puremagic` (`experiments/eval/tools.json`). tools.json labels it "QCE (paper snapshot requested)", but the binary is f990c3e; the adapter records the banner commit (`puremagic.py:146-149, 446-464`) | native: λ=1/3 for cultivation, 1e6 for instant (`rq_common.py:417-418`). Every Magic node cultivates, with times = round(Exp(1/λ)). **A draw of 0 is allowed and makes the node ready at once** (`cultivation.rs:51, 97-129`); Harvest clamps to ≥1 cycle (`cultivation.py:398-400`; `magic_state_cultivator.py:74-80`). This is a slight supply advantage for PureMagic: P(round<1)=1−e^{−1/6}≈15% at mean 3. In magic-routing mode, magic nodes used as routing are marked used and restart cultivation (`cultivation.rs:100-117`) |
| EAF | in-repo reimplementation, `src/harvest/baselines/silva.py` (Silva et al. TQC 2024, Alg. 1-2). Documented deviations: deterministic candidate order instead of random (`:146-148`), orientation proxy (`:86-89`). The module does not mention official code, and this audit did not check whether any exists | same cultivator object as Harvest. A storage site is offered only while it holds a state (`silva.py:160-178, 337-341`) |
| Litinski | in-repo **analytic model**, `src/harvest/baselines/litinski.py`. "The paper is a resource model, not a released compiler" (`:4-7`) | **not ignored:** cultivation ports sized ceil(mean/worst-case steps), sequential rotations wait for a ready port (`:58-80, 187-193`) |
| O3LS | in-repo reimplementation, `src/harvest/baselines/o3ls.py` (Zhu et al., arXiv:2604.15099). "No implementation was released" (`:4-5`) | **not ignored:** the single port waits Exp(mean) after each π/8 (`:652-660, 693-706, 723-727`; note `:870-871`). Docstring `:41-44` and NOTES `:760` still say "free", but the appended note overrides them. One port only, so this is possibly pessimistic for O3LS under cultivation (speculative) |

So under cultivation, none of Litinski, O3LS or EAF assumes always-ready states. All four in-tree and analytic models share `sample_cycles`/`exponential_sampler` (Exp(mean), rounded, ≥1). PureMagic uses its native sampler (rounded, can be 0).
