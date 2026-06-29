# Phase 3 — testing the coverage levers (targeted grounding, then panel addition)

Read-only. Phase 1–2 (REPORT) concluded that the engine cannot emit a useless label and that
`develops_from` is a NO-GO, leaving **targeted grounding of near-bar backlog cell types** as "the only
lever that grows coverage." Phase 3 tested that claim end to end. **It does not hold:** the backlog
lever is dead on the benchmarks, and the adjacent panel-addition lever regresses on its best candidate.
All three coverage levers are now empirically exhausted — coverage is bound by the selection/attractor
wall, not by reachability, grounding capacity, or missing anchors.

## 1. Backlog grounding is dead on the benchmarks (corpus-capacity ≠ eval-realizability)

`backlog.csv`'s `genes_to_min` is a **corpus-wide capacity** number: "one more curated ZFIN gene would
make the term's theoretical maximum support 3." It is **not** an eval-firing number. The engine names a
term only when a real cluster has ≥ `CONVERGENCE_MIN` (3) of that term's credited genes **co-resident
in its marker list** (here, the benchmark's per-cluster markers) and clears the 0.6 support-fraction floor.

Across all **629 committed eval clusters** (Daniocell 522 + ZSCAPE 97 + Zebrahub 10), **0 of the 11
"reachable, 1-gene-short" candidates have a single cluster carrying even both of their current two
markers** — and 6 of the 22 markers appear in no cluster at all. So adding a third curated gene cannot
help: there is no cluster for it to fire on. (Verified two ways: an adversarial agent through the real
normalize+ancestor-credit path, and an independent token co-occurrence grep. Both agree.)

Examples: adrenergic neuron `dbh`+`th` never co-occur (`dbh` in one cluster, `th` in another,
different lineages); pancreatic acinar `nr5a2`+`prss1` never co-occur; UV/blue photoreceptor opsins
absent from every atlas. **The near-bar backlog is corpus-capacity-near-bar, not eval-fireable.**

## 2. The realizable-headroom scan (`coverage_headroom.py`)

Given the above, the only live lever is **adding a panel/anchor** for a well-grounded useful term that
lacks one. `coverage_headroom.py` runs the current engine over every eval cluster and asks whether a
NEW panel could turn it into a correct (or deeper-correct) named call, attributing each shortfall:

| category | count | meaning |
|---|---|---|
| covered | 187 | clean correct call (covered + panel_addable_deeper_correct = the eval's overlay-corrected numerator — a consistency check) |
| panel_addable_new_correct | 63 (31 fine-matched) | unreachable useful correct term the markers support — a new panel *might* add a correct call |
| panel_addable_deeper_correct | 5 | already correct; an unreachable finer term is supported |
| selection_bound | 334 | a useful correct term IS reachable but the engine didn't emit it (floor/score) — not a panel fix |
| resolution_bound | 27 | no useful term reaches support ≥ 3 — genuinely low-resolution |

The 63 is an **upper bound**: 32 only ground under an over-broad gold (e.g. a thyroid-follicle cluster's
markers pick "ovary", which grounds under the broad "Endocrine" gold — wrong subtype, because the true
type is a T4 backlog term). The 31 fine-matched (candidate name overlaps the atlas fine label) are
dominated by **periderm (19, Daniocell/hard gate)** and **endoderm (7, coarse germ-layer)**, with the
rest scattered held-out singletons (pharyngeal arch, hypochord, intermediate mesoderm). Full
per-cluster classification: `coverage_headroom.csv`; machine summary: `coverage_headroom.md`.

## 3. Periderm — the top candidate, tested: REGRESSES

Periderm is the cleanest, highest-yield, hard-gate candidate, so it is the decisive test. Two curation
approaches, both measured with `make eval` on the Daniocell hard gate:

| approach | overlay-corrected agreement | what broke |
|---|---|---|
| baseline (committed) | **87.5% (154/176)** | — |
| (a) add periderm anchor + markers to the **epidermis** panel | 83.1% (167/201) | epidermis attractor 21→49; fin/muscle clusters grabbed; epid clusters mis-called periderm |
| (b) **separate** periderm panel, periderm-specific markers (icn2, agr1, ckap4, tcnbb, lye, anxa1c, cyt1l, selenow1) | 82.2% (125/152) | 8 epidermis + several fin clusters → "periderm" (failures); 24 named calls demoted to rollup; overcalls 5→7 |

Both **reduce** agreement. Root cause is structural and matches the design's documented wall:

- **Periderm is graph-disconnected from epidermis** in ZFA (no is_a/part_of link — the very reason the
  Daniocell crosswalk carries a periderm→epidermis *overlay*). So a periderm anchor lets true epidermis
  clusters be named "periderm", which does **not** ground under their epidermis gold → new failures.
- **Periderm and epidermis share ZFIN grounding** (keratins express in both), so the periderm anchor
  seeds for epidermis clusters too, and even "periderm-specific" panel markers can't fully prevent the
  poach. Adding the panel also creates scoring ties that demote unrelated named calls to rollup.

This is the same attractor-selection wall that nullified `develops_from`: more reach/anchors raise the
*ceiling*, but the selection layer (marker promiscuity + the support floors) is the binding constraint.

## 4. Conclusion

All three coverage levers are now tested and exhausted:

1. `develops_from` reach — 0 new labels, otolith regression (REPORT, `develops_from_experiment.md`).
2. Backlog grounding — dead on the benchmarks (0/629 clusters carry the markers; §1).
3. Panel addition — the best, cleanest, highest-yield candidate (periderm, 19 hard-gate clusters)
   regresses two ways (§3). The remaining fine-matched candidates are smaller and individually untested:
   endoderm (7, hard gate) is the only other material one; the rest are held-out ~1-cluster singletons.

**Coverage is bound by marker promiscuity and the selection wall, not by reachability, grounding
capacity, or missing anchors.** No engine or panel change is warranted. The lasting products are the
**`coverage_headroom.py` scan** (a standing instrument that enumerates and *attributes* the headroom,
so a future curation effort can target the few fine-matched candidates and confirm with `make
gate-all`) and this evidence trail.

**Scope of the panel NO-GO:** periderm is *proven* to regress; the other fine-matched candidates are not
individually tested but are low-yield — endoderm (7, hard gate) carries a broad germ-layer + attractor
poaching risk, and the rest are held-out ~1-cluster singletons (pharyngeal arch, hypochord, intermediate
mesoderm). Each stays a future panel candidate only if it clears the same `make gate-all` poaching check
periderm failed; none is expected to clear it cleanly, so none is pursued here.

**Reproduce:** `uv run python analysis/zfa_usefulness/coverage_headroom.py` (the scan); the backlog
co-occurrence check is a token grep of the 11 candidates' markers over `benchmarks/*_eval.csv`.
