# ZFA label usefulness — examination

**Read-only examination. No engine code or behavior changed.** This scores every ZFA term on a
*usefulness* rubric, tiers the whole vocabulary from highly useful → very not useful, and audits the
parent→child *steps* (edges/walks). It is the input to a later decision about how — or whether — to
act on it. The deferred "how to handle it" recommendation is at the end.

- **Source:** ZFA `data-version: releases/2026-06-02`; ZFIN wildtype-expression corpus = 14,485 genes.
- **Scope:** 3,107 ZFA term-nodes in the loaded graph. (obonet drops the 53 `is_obsolete: true`
  terms, so they never reach the engine — already a non-problem.)
- **Reproduce:** `uv run python analysis/zfa_usefulness/score_terms.py` → regenerates the three
  artifacts below deterministically. All metrics reuse zlabel's own functions (`data.load_zfa`,
  `data.load_zfin_expression`, `resolve.build_information_content`, `resolve._term_with_ancestors`,
  `CONVERGENCE_MIN`, `STOPLIST`) so they match the engine exactly.

Artifacts in this folder:
- `zfa_term_usefulness.csv` — per term: sub-signals, composite score, tier, flags (3,107 rows).
- `zfa_edges.csv` — per is_a/part_of edge: support both sides, gated discernibility, dead-step flag (5,377 rows).
- `summary.json` — the aggregate numbers cited here.

---

## The principle

You said it best: we want **hierarchical anatomical walks where each step is a real distinction
discernible by expression** — so `anatomical system` or `cell` (pure containers with no expression
signature) are useless, however deep the tree goes. A term is useful when (a) it names a biologically
real entity, not an administrative grouping, and (b) there is *enough* in-vivo expression evidence to
prove it has its own signature, distinct from its parent.

## The one thing that makes this hard (and shapes the whole rubric)

**Naive "discernible by expression" is a sparsity illusion.** If you just compare a parent's genes to
a child's genes, **5,334 of 5,377 edges (99.2%) look "discernible"** (Jaccard < 0.3). But that is an
artifact of how *thin* the data is: 39% of ZFA terms have **zero** ZFIN grounding, and the median
grounded term has only 7 genes. A child with 1 gene trivially looks "different" from its parent.

Concretely: of those 5,334 "discernible-looking" edges, **2,750 cannot actually be judged** — one
side has fewer than 3 genes. The same trap hits terms: a term credited by exactly 3 genes scores
IC ≈ 12.2 ("looks highly specific") purely because the corpus is sparse. **So IC is not used to claim
specificity. Credited-gene count (evidence sufficiency) is the primary axis;** IC is used only at the
low end, where it reliably flags breadth (a term almost every gene rolls up into has near-zero IC).

---

## The rubric

Four signals per term, combined into a tier. Every signal is a real, reproducible quantity:

| Dim | Signal | Source |
|----|--------|--------|
| **A. Entity vs. container** | `cell_slim` membership; `CL:` xref (the cell-type axis — 441 terms); name pattern (`anatomical *`, `portion of *`, bare `cell`/`organ`/`tissue` → container); child fan-out; `is_a` vs `part_of` profile; `STOPLIST` | `zfa.obo` |
| **B. Grounding / sufficiency** | distinct credited genes (engine ancestor-credit); ≥ `CONVERGENCE_MIN` (3) = provable; Information Content | ZFIN + `build_information_content` |
| **C. Step discernibility** | per-edge, **sufficiency-gated**: support retained parent→child, child-unique fraction vs siblings — only scored when *both* sides have ≥3 genes | ZFIN footprints |
| **D. Curation / atlas cross-check** | membership in `panels.yaml`, the tissue crosswalks, `cell_population_coverage.yaml` (a human floor); atlas coverage sanity | curated YAML |

### Tiers (the deliverable)

| Tier | Meaning | Count | What's in it |
|------|---------|------:|--------------|
| **T1 — Highly useful** | Real entity, solid grounding (≥10 genes), discernible, specific | **964** | 195 cell types (neuron, endothelial cell, hepatocyte, adaxial cell, oocyte, germ line cell) + 769 specific structures (notochord, telencephalon, somite, intestine, gonad, pharyngeal arch) |
| **T2 — Useful** | Real, grounded backbone label — coarser, or a vetted anchor | **481** | nervous system, central nervous system, eye, digestive system, musculature system, liver, retina, heart |
| **T3 — Coarse / conditional** | Real but broad/promiscuous — coarse fallback only | **24** | brain, forebrain, midbrain, hindbrain, head, trunk, gut, mesoderm, muscle, gill, sensory/visual system |
| **T4 — Real but ungroundable** | Biologically real, < 3 ZFIN genes — can't prove a signature *now* | **1,619** | 350 are real cell types (tendon cell, chromaffin cell, pancreatic acinar cell, photoreceptor subtypes), 179 with a CL xref |
| **T5 — Not useful** | Content-free administrative / structural containers | **19** | anatomical structure/system/group/cluster/space/line/surface/conduit, cell, whole organism, portion of tissue, compound organ, organism subdivision, unspecified |

**Useful label space (T1–T3) = 1,469. Curation backlog (T4) = 1,619. Drop-forever (T5) = 19.**

Grounding distribution (the reason T4 is so large): `0 genes: 1,305 · 1–2: 314 · 3–9: 455 · 10–29:
384 · 30–99: 315 · ≥100: 334`. **Over half the ontology (1,619 terms) is real anatomy ZFIN cannot
yet back with 3 genes.** That, not the algorithm, is the dominant fact about the label space.

---

## Validation (does the rubric agree with humans?)

- **62 / 62 curated anchors land T1–T2** (51 T1, 11 T2) — none lower. The data-driven rubric and the
  hand curation agree completely on the positive set.
- **5 / 5 `STOPLIST` terms land T5**, alongside 14 more content-free terms the STOPLIST doesn't list
  yet (`anatomical cluster/space/line/surface/conduit`, `compound organ`, `organism subdivision`,
  `portion of tissue`, `embryonic/presumptive structure`, …) → the STOPLIST is correct but
  **incomplete**.
- **One curation conflict, and it's a good one:** `ZFA:0001632 'portion of connective tissue'` is a
  zscape-crosswalk anchor the human curator *themselves* tagged `# review`. The rubric independently
  flagged it `curated_but_admin` (container-style name). Our automated rule rediscovered the exact
  doubt the curator had flagged by hand.
- **Spot-checked against raw OBO blocks** across all five tiers (endothelial cell → T1, liver → T2,
  brain → T3, tendon cell → T4, anatomical system → T5): every tier matches the term's actual
  definition (subset, CL xref, is_a parent).

---

## Edge / walk findings

Of 5,377 is_a/part_of edges: **2,609 are judgeable** (both sides ≥3 genes), **2,515 are genuinely
discernible** steps, and **77 are "dead steps"** — the child retains ≥98% of the parent's footprint,
so naming the child instead of the parent adds *no* expression-distinguishable information. Examples:

```
respiratory system        -> gill                      retained 1.00   (2031 -> 2031)
solid compound organ      -> liver                     retained 1.00   (2334 -> 2334)
electrically signaling cell -> neuron                  retained 1.00   (1352 -> 1352)
liver and biliary system  -> liver                     retained 0.993  (2350 -> 2334)
posterior segment eye     -> retina                    retained 0.993  (2268 -> 2252)
```

These are pure renamings the ZFA hierarchy inserts — a descent could collapse them and lose nothing.

**Useful spines** (greedy descent along discernible, non-T5 steps) show exactly where the walk earns
its keep and where it idles:

```
nervous system(T2) → central nervous system(T2) → brain(T3) → forebrain(T3)
                   → diencephalon(T3) → epithalamus(T1) → pineal complex(T1) → parapineal organ(T1)
vasculature(T1) → blood vasculature(T1) → artery(T1) → dorsal aorta(T1) → ventral wall of dorsal aorta(T1)
musculature system(T2) → muscle(T3) → myotome(T1) → hypaxial myotome region(T1)
liver(T2) → hepatocyte(T1)
```

The neural spine is the whole problem in one line: it threads through **five coarse container steps
(T2/T3)** before reaching anything specific. The vasculature spine, by contrast, is a clean ladder of
all-useful steps. Usefulness is not uniform across the tree — it's path-dependent.

---

## Notable findings (the examination's payload)

1. **The drop-list is tiny and safe (19 terms).** Beyond the 5 STOPLIST roots, 14 more content-free
   containers (`anatomical cluster/space/line/...`, `compound organ`, `portion of tissue`, …) are
   never a useful label and could join the STOPLIST today with zero risk.

2. **The real story is the backlog, not the noise.** 1,619 terms are real anatomy ZFIN can't ground
   (≥ 3 genes). **350 of them are bona-fide cell types** (`cell_slim`/CL), 179 CL-xref'd — tendon
   cell, chromaffin cell, pancreatic acinar cell, Golgi cell, UV/blue photoreceptor subtypes. These
   are the cell types zlabel *structurally cannot name today*, and they're a ranked curation target.

3. **Two "deferred" panels are actually groundable as terms.** `thyroid follicle` (29 genes) and
   `hatching gland` (274 genes) score T1 — the term-level grounding exists even though the panels were
   deferred on the ≥3-marker bar. Worth revisiting.

4. **Abstract grouping cell-types pollute even T1.** `electrically active cell` (1,560) and
   `electrically signaling cell` (1,352) are CL abstraction-layer terms that are *dead-step renamings
   of `neuron`* — high grounding, near-zero meaning. The dead-step flag catches them.

5. **A pure data rubric can't see "undifferentiated."** `blastomere` scores T1 (well-grounded,
   specific) but the curators deliberately mark it `not_scored` — it's a real, distinct cell state
   that is *not a useful identity call*. This is a genuine limit of any expression-only rubric and
   argues for keeping a small human deny-list on top.

---

## Limitations (so the tiers aren't over-trusted)

- **ZFIN is the lens.** A term ungroundable in ZFIN may be perfectly discernible in the scRNA-seq
  atlases — T4 means "unprovable *from ZFIN*," not "biologically indistinct." Atlas-marker per-term
  discernibility is the natural deepening of dimension D and is left as follow-on.
- **Dead-step footprint inflation:** a child in a dead-step pair inherits its parent's whole footprint,
  which can make a fairly specific organ (e.g. `gill`) look broad and land T3. Bounded and visible in
  `zfa_edges.csv`.
- **Thresholds are provisional** (`SOLID_GENES=10`, `BROAD_FOOTPRINT=1000`, `IC_BROAD=3.0`) and chosen
  to agree with curation; they're one edit away in the script and the CSV carries the raw signals so
  any cutoff can be re-derived without recomputing.

---

## Recommended handling (the deferred decision)

You asked me to recommend. The rubric should become a **per-term usefulness annotation the engine
consults**, in three escalating, independently-shippable steps:

1. **Now, zero-risk — extend the deny-list.** Promote the 19 T5 terms into a principled superset of
   today's 5-term `STOPLIST` (data-derived, regenerated by this script). Pure cleanup.
2. **Next — roll up to the nearest useful term + skip dead steps.** Teach the descent to never *name*
   a T4/T5 term and to collapse the 77 dead steps: when the walk lands on an ungroundable or
   container term, report the nearest T1–T3 ancestor instead. This is the change that directly
   improves zlabel's labels and is the natural home for the rubric.
3. **Later — work the backlog.** Treat the 350 ungroundable cell types (and thyroid/hatching gland) as
   a ranked curation queue: each is a cell type zlabel could name if its ZFIN/atlas grounding were
   added. This is where coverage actually grows.

Keep a tiny hand-maintained deny-list for the cases expression can't judge (`blastomere` and other
undifferentiated states). Everything above is a separate implementation plan to be approved after you
review this examination — **no engine change has been made.**
