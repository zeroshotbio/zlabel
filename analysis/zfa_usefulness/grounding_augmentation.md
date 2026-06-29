# Grounding augmentation — can we convert the backlog? (feasibility)

The backlog (`backlog.md`) is 255 descent-reachable cell types with < 3 ZFIN genes; 50 are within 1–2
genes of the ≥3 **corpus-capacity** bar. This assessed the ways to add grounding. Light review, not a build.

> **Phase-3 correction (`grounding_pilot.md`).** Targeted curation (Option C) was the *predicted* viable
> path, but the end-to-end test refuted it: the near-bar terms' markers never co-occur in any of the 629
> eval clusters, so adding a gene fires nothing on the benchmarks; and the panel-addition route hits the
> selection/attractor wall (periderm regresses the hard gate). **No grounding/panel lever realizes
> coverage on the current benchmarks.** Options A/B were already ruled out; Option C is now NO-GO too.

## Option A — bulk: inject ZFIN's fuller `xpat_stage_anatomy` corpus — RULED OUT

zlabel grounds on `wildtype-expression_fish.txt` only. ZFIN's larger `xpat_stage_anatomy` adds
endogenous cell-type grounding the loaded subset lacks. **This was already tested in `docs/design.md`:**
injecting it lifts per-term feasibility (mural 15→41 genes, glia 90→250) but **recovers zero blind-spot
clusters, and injected naively it regresses named calls 146→111.** More grounding everywhere also feeds
the broad attractor panels, so the net is negative. A bulk corpus swap is **not** the move.

## Option B — atlas markers as grounding — NOT DIRECTLY USABLE

The atlas eval sets (Daniocell/ZSCAPE/Zebrahub) carry rich per-cluster markers, but grounding is keyed
**per ZFA term**, and the atlases only have **broad-tissue** gold labels (the crosswalks). There is no
per-cluster fine-cell-type label to attach atlas markers to a specific ZFA cell type, so atlas markers
cannot ground `pancreatic acinar cell` or `adrenergic neuron` without first fine-labelling those
clusters — which is the very thing zlabel is trying to do. Circular; not a grounding source today.

## Option C — targeted curation — PREDICTED VIABLE, TESTED NO-GO (see the correction above)

The backlog is actionable precisely because it is *specific and small at the margin*. The 50 near-bar
cell types each already carry 1–2 correct canonical markers and need one more (examples from
`backlog.csv`):

| cell type | has | a canonical missing marker (illustrative) |
|---|---|---|
| adrenergic neuron | dbh, th | `ddc` / `slc6a2` |
| UV cone photoreceptor | opn1sw1, arr3b | `gngt2a` (cone) |
| blue cone photoreceptor | opn1sw2, arr3b | `gnat2` |
| glycinergic neuron | slc6a5, nkx1-2b | `glra1` / `slc32a1` |
| pancreatic acinar cell | prss1, nr5a2 | `cpa5` / `ctrb1` |
| Golgi cell (cerebellar) | gad1b, gad2 | `grm2` |

The theory was that adding a curated ZFIN expression record (NOT a panel `marker` — only expression
records enter the descent tally, per `resolve.resolve_label`) flips each term over the ≥3 *capacity*
bar. Phase 3 refuted the conversion: for all 11 "1-gene-short" terms, no eval cluster carries even the
two current markers, so cluster support never reaches 3 regardless of a curated third gene
(`grounding_pilot.md`). The illustrative markers above stay literature candidates; they do not move the
benchmark.

## Recommendation

1. **Do not** swap in `xpat_stage_anatomy` wholesale — design.md already showed it regresses.
2. **Do not** expect the 50 near-bar terms to convert — Phase 3 showed their markers never co-occur in
   any eval cluster, so added grounding fires nothing on the benchmarks (`grounding_pilot.md`).
3. Atlas-marker grounding only becomes available *after* fine labelling exists — a later loop, not now.
4. Panels for unanchored / develops_from-only terms were tested (periderm) and **regress** the gate. No
   grounding or panel lever grows coverage on the current benchmarks; keep `backlog.csv` as a capacity
   map and `coverage_headroom.py` as the standing instrument.
