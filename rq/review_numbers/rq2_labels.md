# RQ2 labels (current meaning)

Leave-one-out: every label removes one component from `full`; same layout (template, placement) unless placement is the ablated component.

| Label | Meaning |
|---|---|
| `full` | The paper configuration: `HarvestConfig()` defaults (critical-path priority with router priority, router-chosen magic terminals `terminals="route"`, negotiated congestion, greedy fill, magic retry, admission control), circuit-aware placement with the Y-factor term, pruning. |
| `-negotiation` | `negotiate=False`: greedy first-fit Steiner packing (EAF-style commit), everything else as `full`. |
| `-retry` | `greedy_fill=False, magic_retry=False`: no greedy fill of dropped products into the space left by committed routes and no retry through another free magic terminal. **Name is outdated:** with router-chosen terminals (the router already picks and moves terminals), STATUS.md records this label as effectively 'no greedy fill'. |
| `-admission` | `admission=False`: every ready magic product is assigned a terminal and routed regardless of supply; a route to an empty terminal stalls after occupying routing space that step. |
| `-matching` | `terminals="nearest"`: each product takes the Euclidean-nearest free ready terminal before routing; the router may not choose or move terminals. **Name is outdated:** the default is no longer min-cost matching but router choice, so this label measures 'no router terminal choice', not 'no matching' (STATUS.md). |
| `-priority` | `priority="dag_order", router_priority=False`: products compete in DAG order and the router neither routes nor keeps high-priority products first. |
| `-placement` | Index (row-major) placement instead of circuit-aware placement. |
| `-yfactor` | Circuit-aware placement without the Y-factor centrality term (beta = 0). |
| `-pruning` | No run of its own: the `full` schedule priced on its unpruned footprint (`volume_initial`). |
| `+reuse` | Scheduler step (study `scheduler`): HARVEST-2, `full` plus a reuse cost (cell 1 / magic 2) on routing cells and magic patches no earlier step used. |
| `+resched` | Scheduler step: `full`, then up to 4 rounds of pruning the least-used 10% of retained tiles and rescheduling on the smaller layout (kept only if volume drops). |
| `+reuse+resched` | Scheduler step: HARVEST-3, both of the above. |
