# Coverage triage — what the descent can and cannot reach

Read-only. Useful = T1/T2. Anchors = 42 panel ontology_anchors. Reach = descend the given
edges from the anchors (graph reachability, an upper bound; support floors are stricter).

## Useful label space by reachability

| status | count | composition |
|---|---|---|
| reachable today (is_a+part_of) | 991 | 991 (189 cell-type, 802 structure) |
| reachable only via develops_from | 102 | 102 (21 cell-type, 81 structure) |
| unreachable even with develops_from | 352 | 352 (97 cell-type, 255 structure) |

So **102 useful terms** sit behind the ignored develops_from axis, and **352**
are unreachable by any of the three axes from the current anchors (a different gap: no panel sits in
that lineage, or the term is out of cell-typing scope).

## Will the develops_from experiment actually move outputs? (the support-floor reality check)

Graph-reachability is an upper bound. The descent only *takes* a develops_into step if the derivative
keeps >= CONVERGENCE_MIN (3) genes AND >= DESCENT_SUPPORT_FRACTION
(0.6) of the parent's credited support.

- develops_into steps from an already-reachable parent to a useful, >=3-gene child: **126**
- of those, steps that also clear the 0.6 support-retain floor: **79**

Examples that clear the floor:
  - olfactory placode -> peripheral olfactory organ (sup 485->754)
  - otic placode -> otic vesicle (sup 381->1141)
  - upper rhombic lip -> cerebellum (sup 18->719)
  - pancreatic bud -> pancreas (sup 152->419)
  - segmental plate -> somite (sup 725->1555)
  - forebrain ventricle -> third ventricle (sup 6->54)
  - lateral crista primordium -> lateral crista (sup 13->22)
  - trunk neural crest -> dorsal root ganglion (sup 32->22)
  - protoneuromast -> neuromast (sup 11->398)
  - scale primordium -> scale (sup 4->46)
  - immature hair cell posterior macula -> hair cell posterior macula (sup 2->9)
  - trigeminal neural crest -> trigeminal ganglion (sup 4->212)

**Prediction:** only ~79 develops_into steps can fire under the current floors. If that number
is small, the Phase-3 experiment will move few outputs — i.e. the coverage ceiling rises but the
support floors don't realise it (the same shape design.md found for finer ZFIN grounding). The
experiment run measures the realised effect on `make gate-all`.

Full per-term list: `coverage_unreached.csv` (454 rows).
