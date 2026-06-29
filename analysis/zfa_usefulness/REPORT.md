# ZFA label usefulness — examination (hardened) + evidence-backed posture

**Read-only analysis; no engine behavior changed.** This scores every ZFA term on a *usefulness*
rubric, tiers the whole vocabulary highly-useful → very-not-useful, audits the parent→child *steps*,
and — after an adversarial review that overturned the first recommendation — states where the real
lever is. Companion: `RELATIONSHIPS.md` (the relationship-axis primer).

- **Source:** ZFA `releases/2026-06-02`; ZFIN wildtype-expression corpus = 14,485 genes; 3,107 ZFA
  term-nodes (obonet drops the 53 obsolete terms, so they never reach the engine).
- **Reproduce:** `uv run python analysis/zfa_usefulness/score_terms.py` → regenerates every artifact
  deterministically, reusing zlabel's own functions (`data.load_zfa`, `load_zfin_expression`,
  `resolve.build_information_content`/`_term_with_ancestors`/`CONVERGENCE_MIN`/`STOPLIST`).
- **Artifacts:** `zfa_term_usefulness.csv` (per term), `zfa_edges.csv` (per step), `sensitivity.csv`
  (threshold sweep), `summary.json` (all aggregate numbers).

## Bottom line (what the evidence says to do)

> **Phase-3 update (`grounding_pilot.md`).** The "curation backlog" lever (point 3) was tested
> end-to-end and does **not** grow coverage on the benchmarks: the near-bar terms' markers never
> co-occur in any of the 629 eval clusters (`genes_to_min` is corpus *capacity*, not eval
> realizability), and adding panels for unanchored useful terms regresses the hard gate (the best
> candidate, periderm, two ways). **All three coverage levers are now NO-GO; coverage is bound by the
> selection/attractor wall, not reachability or grounding.** Points 1–2 stand; point 3 is corrected
> in place below.

1. **The engine already cannot emit a useless label.** Of 176 named Daniocell calls, **0 are T4/T5**
   (T1 137, T2 19, T3 20). Two structural reasons: (a) the descent only names a term with
   `support >= CONVERGENCE_MIN` (3) genes, which *is* the T4 boundary, so no T4 is nameable; (b) it
   descends *downward* from curated T1–T3 anchors and never ascends, and all 19 T5 terms are DAG
   *ancestors* of the anchors (verified: 0/19 are descendants) — only 5 are in `STOPLIST`; the other
   14 are blocked by topology, not a deny-list. → **Blocking/“rolling up” useless labels is a
   non-problem. The cosmetic engine changes the first draft proposed are dropped.**
2. **The most plausible coverage lever — the ignored `develops_from` axis — was tested and is a
   NO-GO.** zlabel walks `is_a`+`part_of` only; adding `develops_into` makes +102 useful terms
   graph-reachable (`RELATIONSHIPS.md`), but the Phase-3 experiment realised **0 new labels** (the
   +102 is an unconverted ceiling) and *degraded* quality (`otic vesicle → otolith`, an acellular
   biomineral). The binding constraint is the selection/marker layer, not reachability — exactly
   design.md's documented boundary. See `develops_from_experiment.md`.
3. **A real curation backlog exists — but it is corpus *capacity*, not realizable coverage.** 350
   ungroundable cell types; 255 reachable under a current anchor; 50 within 1–2 ZFIN genes of the
   ≥3-credited-gene bar. Phase 3 tested this: **none fires on the benchmarks** (the markers never
   co-occur in an eval cluster), and panel addition for unanchored useful terms regresses the gate. So
   the backlog is a curation *capacity* map; growing coverage is blocked by the selection wall, not the
   backlog (`grounding_pilot.md`, `coverage_headroom.md`).

## The principle

We want **hierarchical walks where each step is a real distinction discernible by expression** —
`anatomical system` or `cell` (containers with no signature) are useless however deep. A term is
useful when it (a) names a real entity, not an administrative grouping, and (b) has *enough* in-vivo
evidence to prove a signature of its own.

## The trap that shapes the rubric: sparsity masquerading as specificity

Naive "discernible by expression" is an illusion. Comparing a parent's genes to a child's, **5,334 of
5,377 edges (99.2%) look discernible** (Jaccard < 0.3) — but **2,750 of those can't actually be
judged** (a side has < 3 genes). 42% of terms (1,305/3,107) have zero ZFIN grounding; the median grounded term has 7
genes. The same trap hits terms: a 3-gene term scores IC ≈ 12 ("looks specific") purely from sparsity.
**So IC never claims specificity here — credited-gene count (sufficiency) is the primary axis;** IC is
used only at the low end, where it reliably flags breadth.

## The rubric

| Dim | Signal | Source |
|----|--------|--------|
| **A. Entity vs container** | `cell_slim`; `CL:` xref (cell-type axis, 441 terms); admin name pattern; child fan-out; `STOPLIST` | `zfa.obo` |
| **B. Grounding / sufficiency** | distinct credited genes (engine ancestor-credit); ≥ `CONVERGENCE_MIN` = provable; IC for breadth | ZFIN |
| **C. Step discernibility** | per-edge **sufficiency-gated** retained-support + child-unique fraction (scored only when both sides ≥ 3 genes) | ZFIN footprints |
| **D. Curation cross-check** | membership in `panels.yaml` / crosswalks / `cell_population_coverage.yaml` (a human floor) | curated YAML |
| **Hardening: pure-grouper guard** | a term with **0 direct genes** (credited only via descendants) borrows all its support — it has no signature of its own, so it is **capped below T1** | ZFIN direct vs credited |

### Tiers

| Tier | Meaning | Count | Examples |
|------|---------|------:|----------|
| **T1 — Highly useful** | real entity, solid grounding (≥10 genes), own signature, discernible | **906** | 174 cell types (neuron, endothelial cell, hepatocyte, oocyte, chondroblast) + 732 specific structures (notochord, somite, telencephalon, dorsal aorta) |
| **T2 — Useful** | grounded backbone label — coarser, a vetted anchor, or a grouper capped from T1 | **539** | nervous system, eye, digestive system, liver, retina, heart, muscle precursor cell |
| **T3 — Coarse/conditional** | real but broad/promiscuous — coarse fallback only | **24** | brain, forebrain, head, trunk, gut, mesoderm, muscle, gill |
| **T4 — Real but ungroundable** | real, < 3 ZFIN genes — no signature *yet* | **1,619** | 350 cell types (tendon cell, chromaffin cell, pancreatic acinar cell, photoreceptor subtypes) |
| **T5 — Not useful** | content-free admin/structural containers | **19** | anatomical structure/system/group/cluster/space/line/surface/conduit, cell, whole organism, portion of tissue, compound organ, organism subdivision |

**Useful (T1–T3) = 1,469 · backlog (T4) = 1,619 · drop-forever (T5) = 19.** Over half the ontology is
real anatomy ZFIN can't yet back with 3 genes — the dominant fact about the label space.

## Validation — honest, de-circularized, and stable

- **Curation agreement, floored: 62/62** anchors in T1–T2 (49 T1, 13 T2). But the curation *floor*
  could manufacture that, so the real check is **un-floored: 51/62 land T1–T2 on data alone** (the
  floor lifts 11 broad curated compartments that the data calls T3-coarse, e.g. nervous system, plus
  the one admin-named anchor). 82% independent agreement; the 18% are explained, not silent.
- **5/5 `STOPLIST` terms land T5**, plus 14 more content-free containers the STOPLIST omits → the
  current STOPLIST is correct but incomplete.
- **Threshold sensitivity (5×4 grid, `sensitivity.csv`):** **T4 (1,619) and T5 (19) are invariant
  across every threshold** — the actionable verdicts (drop-list, backlog) don't depend on tuning.
  Curated agreement is **62/62 at every grid point.** Only the T1↔T2 split moves with `SOLID_GENES`
  (useful↔useful reshuffle). The boundaries are stable where it matters.
- **One curation conflict, well-founded:** `ZFA:0001632 'portion of connective tissue'` (a zscape
  anchor the curator hand-tagged `# review`) is independently flagged `curated_but_admin`.
- Spot-checked against raw OBO blocks across all five tiers.

## Edge / walk findings

Of 5,377 `is_a`/`part_of` edges: 2,609 judgeable, 2,515 genuinely discernible, **77 "dead steps"**
(child retains ≥98% of the parent footprint — a pure renaming). After a direction-aware fix, only the
**abstract** member of a renaming pair is flagged (7 terms): a directly-grounded child like `neuron`
is never flagged just because an abstract parent (`electrically signaling cell`) renames onto it.
Examples: `respiratory system→gill` (1.00), `solid compound organ→liver` (1.00), `posterior segment
eye→retina` (0.99).

**Spines** show usefulness is path-dependent: `nervous system(T2)→CNS(T2)→brain(T3)→forebrain(T3)→
diencephalon(T3)→epithalamus(T1)→pineal complex(T1)→parapineal organ(T1)` threads five coarse steps
before anything specific, whereas `vasculature(T1)→blood vasculature(T1)→artery(T1)→dorsal aorta(T1)`
is all-useful.

## Notable findings

1. **Drop-list is tiny and safe (19 terms)** — the 5-term STOPLIST could extend to them with zero
   output change (pure hygiene; see Recommendation).
2. **The backlog is corpus *capacity*, not realizable coverage:** 350 ungroundable cell types; 255
   reachable; 50 within 1–2 ZFIN genes of the ≥3 bar. Phase 3 found **none fires on the benchmarks** —
   the markers never co-occur in any of the 629 eval clusters (`grounding_pilot.md`).
3. **Adding panels for well-grounded unanchored terms was tested (Phase 3) and regresses.** The
   headroom scan (`coverage_headroom.py`) flagged periderm, thyroid follicle, hatching gland, etc.;
   realizing the best (periderm, hard gate) poaches epidermis/fin clusters and drops agreement.
4. **Abstract grouping cell-types** (`electrically signaling/active cell`) are now correctly capped at
   T2 by the pure-grouper guard (they have 0 direct genes — renamings of `neuron`).
5. **A pure data rubric can't see "undifferentiated":** `blastomere` scores T1 but curators correctly
   mark it `not_scored`. Keep a tiny human deny-list for states expression can't judge.

## Limitations (and how they're handled)

- **ZFIN is the lens.** T4 = "unprovable *from ZFIN*," not biologically indistinct. ZFIN is tissue-
  level and ≈81% concordant with in-situ; the atlas-marker per-term axis is the natural deepening
  (Phase 4). External critique noted: **IC is annotation-density biased** (a documented, hard problem)
  — which is exactly why this rubric demotes IC to a breadth-only role and leans on direct + credited
  gene counts.
- **Standard pattern, externally supported.** Tiering an ontology + rolling up to the most informative
  ancestor is the GO-slim / Resnik–Lin MICA pattern, and ontology-aware coarsening is used by OnClass,
  Azimuth, popV, and CASSIA. We are not inventing; we are applying it to ZFA.
- **Dead-step footprint inflation** can make a specific organ (`gill`) look broad → T3; bounded and
  visible in `zfa_edges.csv`.
- **Thresholds provisional** but proven stable (above); raw signals are in the CSV so any cutoff is
  re-derivable.

## Recommendation (revised by the evidence)

Two of the three first-draft ideas are now ruled out **with evidence**, which is the value of this
phase:

1. **Roll-up / STOPLIST extension — not a capability gain.** The 0/176 finding kills the roll-up
   (changes nothing, adds risk); the STOPLIST extension is optional hygiene only.
2. **`develops_from` coverage — TESTED, NO-GO.** The most plausible lever realised 0 new labels and
   introduced `otolith`-type regressions (`develops_from_experiment.md`). The descent edge set stays
   `is_a`+`part_of`.

3. **Coverage growth — all three levers are NO-GO (Phase 3, `grounding_pilot.md`).** `develops_from`
   (0 new labels), targeted backlog grounding (the near-bar markers never co-occur in an eval cluster —
   capacity ≠ realizability), and panel addition for unanchored useful terms (the best candidate,
   periderm, regresses the hard gate two ways) all fail at the same selection/attractor wall.

What is actually worth doing:

- **Keep the backlog as a curation capacity map and the headroom scan as a standing instrument.**
  `backlog.csv` ranks where grounding *could* help in principle; `coverage_headroom.py` enumerates and
  attributes the (currently unrealizable) per-cluster headroom so any future curation effort can target
  the few fine-matched candidates and confirm with `make gate-all`. Coverage is not grown by changing
  the walk or by the curation levers tested.
- **Optional hygiene:** extend `STOPLIST` to the 19 T5 terms + a CI guard failing if any future
  panel/crosswalk anchor is ever T4/T5/admin. Cheap, defensive, not a capability gain.
- **Keep the rubric as a standing audit:** it is trustworthy (stable thresholds, 51/62 independent
  curation agreement) and its real product is the backlog + the QA guard.

Keep a small hand-maintained deny-list for undifferentiated states (`blastomere`). **No engine change
was merged** — the one experiment that could have earned one did not clear the bar.
