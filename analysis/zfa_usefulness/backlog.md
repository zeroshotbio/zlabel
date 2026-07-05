# Curation backlog — ungroundable cell types, ranked

Read-only. This ranks the **350 T4 cell-identity terms** (cell_slim/CL, < 3 credited genes today) by
how many curated ZFIN genes they sit from the >= 3 grounding bar.

> **Phase-3 correction (`grounding_pilot.md`): `genes_to_min` is CORPUS CAPACITY, not
> eval-realizability.** It means "one more curated gene makes the term's *theoretical max* support 3" —
> not "a real cluster would then be named it." Tested: of the 11 "1-gene-short" terms below, **0 have
> any eval cluster (out of 629) carrying even both current markers**, so a third gene fires nothing on
> the benchmarks. The adjacent panel-addition lever also regresses on its best candidate (periderm).
> Treat this as a curation *capacity* map, not a queue of guaranteed coverage wins.

| reachability from current anchors | count | meaning |
|---|---|---|
| is_a/part_of (descent-reachable) | 255 | could reach the >=3 bar in principle (corpus capacity; not eval-fireable) |
| develops_from only | 26 | engine won't reach it (Phase-3 NO-GO); needs a panel too |
| unreachable | 69 | no axis reaches it; needs a new panel |

**Corpus capacity: 50 descent-reachable cell types are within 2 genes of the >= 3 bar (11 within 1).**
On paper the highest-yield curation per unit effort — but per the Phase-3 correction above, none fires
on the current benchmarks, because the markers do not co-occur in any eval cluster.

## "1 gene short" by corpus capacity (already have 2) — but eval-unfireable (see grounding_pilot.md)

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
