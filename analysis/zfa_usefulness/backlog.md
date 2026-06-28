# Curation backlog — ungroundable cell types, ranked

Read-only. The Phase-3 experiment ruled out edge-set/descent changes, so the only lever that grows
coverage is **adding ZFIN grounding** to real cell types the descent can already reach. This ranks the
**350 T4 cell-identity terms** (cell_slim/CL, < 3 credited genes today).

| reachability from current anchors | count | meaning |
|---|---|---|
| is_a/part_of (descent-reachable) | 255 | ground to >=3 genes -> nameable today |
| develops_from only | 26 | engine won't reach it (Phase-3 NO-GO); needs a panel too |
| unreachable | 69 | no axis reaches it; needs a new panel |

**Priority: 50 descent-reachable cell types are within 2 genes of nameable
(11 within 1).** Adding one or two curated markers each flips them from unnameable to
nameable — the highest-yield curation per unit effort.

## Top targets (descent-reachable, 1 gene short — already have 2)

| cell type | ZFA | have | current genes |
|---|---|---|---|
| Golgi cell | ZFA:0009069 | 2 | gad1b;gad2 |
| UV sensitive photoreceptor cell | ZFA:0009221 | 2 | arr3b;opn1sw1 |
| adrenergic neuron | ZFA:0009061 | 2 | dbh;th |
| blue sensitive photoreceptor cell | ZFA:0009222 | 2 | arr3b;opn1sw2 |
| corneal endothelial cell | ZFA:0009079 | 2 | dnajc9;krt1-19e |
| glycinergic neuron | ZFA:0009396 | 2 | nkx1-2b;slc6a5 |
| immature hair cell posterior macula | ZFA:0001099 | 2 | jag2b;sox2 |
| kappe olfactory receptor neuron | ZFA:0005828 | 2 | piezo1;piezo2b |
| pancreatic acinar cell | ZFA:0005739 | 2 | nr5a2;prss1 |
| perineuronal satellite cell | ZFA:0009237 | 2 | foxd3;mbpa |
| peripheral neuron | ZFA:0009063 | 2 | mbpa;prkcea |

Full ranked list (all 350): `backlog.csv`. Grounding strategy (bulk vs targeted) is assessed in
`grounding_augmentation.md`.
