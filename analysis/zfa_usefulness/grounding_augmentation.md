# Grounding augmentation — can we convert the backlog? (feasibility)

The backlog (`backlog.md`) is 255 descent-reachable cell types zlabel can't name only because they have
< 3 ZFIN genes; **50 are within 1–2 genes.** Coverage grows by adding *grounding*, not by changing the
walk (Phase-3 NO-GO). This assesses the two ways to add grounding. Light review, not a build.

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

## Option C — targeted curation — THE VIABLE PATH

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

Adding these as ZFIN-curated or panel `markers` (one to three per term) flips each from unnameable to
nameable, with **no bulk-grounding regression** because it touches only the target term. This is
literature/marker-DB curation (per term), not an atlas or corpus swap. `backlog.csv` is the ranked work
queue; the illustrative third markers above must be verified against ZFIN/literature before use.

## Recommendation

1. **Do not** swap in `xpat_stage_anatomy` wholesale — design.md already showed it regresses.
2. **Do** work the 50 near-bar, descent-reachable cell types in `backlog.csv` by adding 1–3 verified
   markers each (highest coverage-yield per unit effort, zero regression risk).
3. Atlas-marker grounding only becomes available *after* fine labelling exists — a later loop, not now.
4. The 69 "unreachable" + 26 "develops_from-only" backlog cell types need a **panel/anchor**, not just
   grounding — a separate, larger curation decision, lower priority than the 50 near-bar terms.
