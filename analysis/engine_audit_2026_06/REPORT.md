# Engine audit — fix-impact, fine-naming, calibration (2026-06-29)

Read-only evidence pass over the committed engine (`main` @ e055ce6). **No engine code, panels, or
behavior changed** — new analysis scripts only. Every number comes from running the real engine through
a harness that reproduces the committed baselines exactly:

| atlas | coverage (non-abstain) | broad agreement | matches baseline? |
|---|---|---|---|
| Daniocell | 218/511 = 42.7% | 134/176 = 76.1% (overlay 154/176 = 87.5%) | yes |
| ZSCAPE | 46/96 = 47.9% | 35/40 = 87.5% | yes |

Goal: drive each open improvement lever to a confident GO / NO-GO, **extending** (not duplicating)
`analysis/zfa_usefulness/`, `analysis/validation/disagreement_sweep.md`, and `docs/design.md §Validation`.

Reproduce: `cd ~/PycharmProjects/zlabel && uv run python analysis/engine_audit_2026_06/run_audit.py`
(needs `data/ontologies/`; not in CI, like the other `analysis/` scripts).

---

## 1. Grounding / curation as a COVERAGE lever — NO-GO (three independent lines)

`analysis/zfa_usefulness/backlog.csv` ranks 50 "near-bar" cell types (1–2 ZFIN genes short of groundable);
`grounding_augmentation.md` argued targeted curation is "the viable path" but never measured the **cluster**
impact. Measured now:

- **Support-floor probe** — lowering `CONVERGENCE_MIN` 3→2→1 recovers **0** abstaining clusters (named
  172→175→176, all from already-non-abstaining fallbacks; agreement unchanged). The floor is not the blocker.
- **Targeted injection** — injecting `grounding_augmentation.md`'s own proposed markers (grm2→Golgi,
  ddc→adrenergic, gngt2a/gnat2→cones, glra1→glycinergic, cpa5→pancreatic acinar) flips **0** clusters.
  Root cause: **3/6 of those markers appear in zero clusters' marker lists, the rest in only 2.** The
  near-bar terms' markers simply are not in the atlas clusters.
- **Bulk xpat** (design.md, prior) — 0 clusters recovered, regresses 146→111.

**Verdict:** term groundability is decoupled from whether clusters present those markers. Curate the
backlog for **vocabulary completeness**, but it will **not move Daniocell/ZSCAPE coverage**. *(Caveat: the
benchmark uses top-25 markers; a top-50/100 rebuild is the one untested adjacent angle, but it needs the
raw atlas and design.md found marker-method changes "move labels only marginally.")*

## 2. Fine-naming accuracy — the validation gap design.md defers — MAJOR FINDING

design.md validates only **broad-tissue** agreement; fine/depth correctness was never scored against
truth. Scored here against ZSCAPE's finer `cell_type_broad` gold via `grounds_under` (29 cleanly-mappable
assigned calls):

| grain | result |
|---|---|
| broad agreement | **87.5%** |
| fine-correct (pred is the gold cell type or under it) | **38% (11/29)** |
| too-broad-but-on-lineage (correct coarser ancestor) | 10% (3/29) |
| **fine WRONG** | **52% (15/29)** |

The fine errors are overwhelmingly the **neural attractor collapsing diverse CNS/PNS neurons to one
region**: dorsal-spinal-cord / motor / spinal-cord / dopaminergic / retinal / cranial-ganglion neurons all
→ "telencephalon"/"diencephalon." The excluded vague-gold bucket shows the same "→ telencephalon" pattern.

**Verdict:** the engine's deep names are frequently **false precision** — broad-correct, fine-wrong. Its
validated competence is broad tissue (76–88%); fine cell-type naming is ~38%. This is a **positioning /
honesty** finding and it *confirms* the design choice to score broad agreement and leave forcing to the
caller. *(Caveat: N=29, one atlas, noisy free-text gold — but the dominant failure matches Daniocell's
broad failure gallery, so it generalizes.)*

## 3. Calibration — confidence is a fine-UNCERTAINTY signal, not P(correct) — GO (additive)

Daniocell assigned calls (n=176):

- **Brier 0.243** (raw `confidence_score`) is *worse* than a base-rate constant (0.182) — it is not a good
  probability of broad-correctness.
- The **low tier is severely under-confident** (states ~0.45, is 73% correct); the <0.5 bin is the *most*
  accurate (81.5%) — a monotonicity inversion. Those calls are **deep** (mean depth 7.0) and **low-margin**
  (0.036): near-ties whose two candidates are usually siblings under the same broad tissue, so they stay
  broad-correct while the margin-dominated score reads "uncertain." Confidence measures **fine-call
  certainty**, not broad correctness.
- **A held-out (5-fold) isotonic recalibration drops Brier 0.243 → 0.171** (−30%, beating the base-rate
  constant) — recalibration genuinely helps.
- **The rank is usable at the top:** margin ≥ 0.20 → 96% accurate (14% coverage); confidence ≥ 0.80 → 100%
  (11%). Clean high-precision operating points.

**Deliverable (additive, gate-safe — no decision-path change):**
1. Document that `confidence_score` is a fine-certainty signal, **not P(broad-correct)**.
2. Publish operating points: `margin ≥ 0.2` → ~96%, `confidence ≥ 0.8` → ~100% (for a soft-set caller).
3. Optionally ship an isotonic recalibration of `confidence_score` (CV Brier 0.171) as a *reported*
   probability beside the raw rubric score.

## 4. Margin-gated depth governor (roll up near-ties) — NO-GO

The natural fix for §2: "when sibling fine-regions are near-tied, roll up to the common ancestor." Tested
whether margin separates fine-wrong from fine-correct:

- fine_correct margin **median 0.050**, fine_wrong **median 0.093** — **inverted**. Correct terminal cell
  types (lens, PGC, xanthophore) are themselves low-margin; the neural attractor's wrong calls are
  *confident*. A governor at T=0.10 suppresses 82% of fine-correct but only 53% of fine-wrong.

**Verdict:** margin (and confidence) cannot gate fine-naming honesty — the same wall every selection lever
hit, confirmed from the fine grain.

## 5. Region-capped neural depth — NO-GO as an automatic rule

Distinct from the NO-GO'd "descent-axis fix" (that addressed *broad* panel-selection errors; these are
broad-correct calls with wrong within-neural region). Simulated capping calls under the neural panel anchor:

- The neural anchor is `ZFA:0000396` (**nervous system**), which via `part_of` **bundles correctly
  fine-named lens, RPE, optic-cup→retina, and pituitary** with the wrong neuron-region calls. A blunt cap
  fixes 8 confident-wrong calls but **destroys 7 fine-correct ones (lens, RPE, pituitary, retina)** — a bad
  trade.
- A surgically targeted cap on the `brain` subtree (ZFA:0000008) only would still trade ~3 correct
  brain-region calls for ~6–7 wrong ones — marginal, and the existing `margin`/`ood` signal already lets a
  caller make that call.

**Verdict:** not worth an automatic rule; the honest move is documentation (§2/§3), not a depth cap. *(The
read-only prototype prevented a rule that would have quietly degraded lens/RPE/pituitary.)*

## 6. Abstain-recovery ceiling — confirms the shipped marker-broadening lever

Of Daniocell's 293 abstains: **67% recoverable** (`weak_signal`/`in_set` — a home exists, marker-vocab
gap), 33% structural (needs a new panel/anchor). ZSCAPE: 64% / 36%. This is the addressable pool for *more*
marker broadening (the one shipped positive lever) and bounds its ceiling. The 22 residual scored
disagreements (after the gold overlay) are the known wall (neural 11, epidermis 8).

---

## Verdict summary

| Lever | Verdict | Key evidence |
|---|---|---|
| Grounding/curation for coverage | **NO-GO** | floor 0, injection 0 (markers absent from clusters), bulk-xpat 0 |
| Margin-gated depth governor | **NO-GO** | margin anti-separates fine-wrong (0.093) from fine-correct (0.050) |
| Region-capped neural depth (auto rule) | **NO-GO** | neural anchor bundles lens/RPE/pituitary; blunt cap loses 7 correct |
| Confidence recalibration + operating points | **GO** (additive) | Brier 0.243→0.171 (CV isotonic); margin≥0.2→96%, conf≥0.8→100% |
| Honest fine-grain positioning | **DO** (docs) | fine accuracy 38% vs broad 87.5% |
| More marker broadening | bounded **GO** | 67% of abstains are recoverable weak_signal |

**Bottom line:** the engine-selection space is comprehensively walled — three improvement levers
independently confirmed NO-GO here, reinforcing design.md's earned boundary. The genuinely new, actionable
outputs are both **additive and gate-safe**: a measured **fine-naming accuracy (38%)** that should govern
how the engine is positioned/displayed, and **calibration guidance** (operating points + a recalibration
that cuts Brier 30% + the fine-certainty framing). Any actual engine change remains a separate gated task
(`make gate` byte-identical).
