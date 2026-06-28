# Phase-3 experiment — does following `develops_from` improve coverage? (NO-GO)

**Read-only experiment; the engine change was prototyped, measured, and reverted.** This tests the
phase-1/2 hypothesis that the biggest capability lever is the relationship axis zlabel ignores: letting
the descent follow `develops_into` (the `develops_from` inverse) so it can reach the +102 useful terms
that no `is_a`/`part_of` path reaches (see `RELATIONSHIPS.md`, `coverage.md`).

## Method

- **Prototype:** one line in `resolve.py:_descend` — add `develops_from` to the descent's `children()`
  edge types so the walk can step progenitor → marker-supported derivative. Everything else (ancestor
  credit, IC, support floors, STOPLIST) unchanged.
- **Measure:** regenerate all three atlas reports and the per-cluster named terminal, vs the committed
  `origin/main` baseline. Bar (from the plan): **more correct named calls without raising the
  parent-child overcall audit**, respecting the attractor wall.

## Result — no coverage gain, no accuracy gain, mixed label quality

Measured on current `main` (after the #41 panel broadening; baseline 76.1%).

| atlas | metric | baseline | prototype | Δ |
|---|---|---|---|---|
| daniocell | named+fallback (N) | 176 | 176 | **0** |
| daniocell | accuracy | 76.1% (134/176) | 76.1% (134/176) | **0** |
| daniocell | coverage | 42.7% | 42.7% | **0** |
| daniocell | overcall audit | 5/172 | 3/172 | −2 (incidental) |
| zscape | all | 40 / 87.5% / 0 | 40 / 87.5% / 0 | 0 |
| zebrahub | all | 3 / 100% / 0 | 3 / 100% / 0 | 0 |

Per-cluster over all 522 Daniocell clusters: **7 terminals changed; 0 newly named (zero coverage
gain); 0 lost.** All seven are lateral re-termings at the same tier:

| cluster | gold | baseline → prototype | judgement |
|---|---|---|---|
| otic.5 | otic | otic vesicle → **otolith** | **worse** (otolith is an acellular biomineral, never a cell type) |
| otic.16 | otic | otic vesicle → **otolith** | **worse** |
| otic.2 | otic | otic vesicle → inner ear | neutral |
| musc.19 | musc | segmental plate → dermis | worse (dermis is not muscle) |
| hema.24 | hema | dorsal aorta → intersegmental vessel | neutral (both vessels) |
| hema.28 | hema | dorsal aorta → intersegmental vessel | neutral |
| fin.9 | fin | fin fold pectoral fin bud → fin bud | neutral/slightly better |

## Why the +102 ceiling doesn't convert

`coverage.md` predicted ~79 `develops_into` steps *could* fire under the support floors — but only **7
clusters'** actual markers route differently, and **none** produce a new label. The clusters whose
markers would support those +102 terms are already named (at another term) or abstain for unrelated
reasons; `develops_into` only changes *where* a few already-named clusters land. The lineage axis also
routes to non-identity terminals (`otolith`), conflating "what a cell came from / becomes" with "what
it is" — the exact reason `develops_from` was excluded in the first place (`data.py:31`).

This reproduces the documented boundary in `docs/design.md`: **finer reach lifts the ceiling without
converting it; the binding constraint is the selection/marker layer, not graph reachability.** Injecting
a richer reference (design.md's `xpat_stage_anatomy` test) showed the same shape — feasibility up,
realized recovery ~0.

## Verdict

**NO-GO.** Following `develops_from` adds 0 coverage, 0 accuracy, and slightly degrades label quality
(`otolith`). It is not worth the added descent complexity or the lineage/identity conflation. The
relationship-axis investigation was still worth doing: it produced the primer (`RELATIONSHIPS.md`) and
**rules out, with evidence, the most plausible coverage lever** — so effort goes to the curation
backlog (Phase 4), which is where coverage can actually grow. The descent edge set stays `is_a`+
`part_of`.
