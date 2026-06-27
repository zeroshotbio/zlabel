# Workflow map — `cluster → labelling → labels`

The skimmable reference for the core zlabel loop. Read it beside
[`01_workflow_walkthrough.ipynb`](01_workflow_walkthrough.ipynb) (which *runs* each stage) and the
source. Authoritative design lives in [`../../docs/design.md`](../../docs/design.md); this is a
learning aid, not a spec.

---

## The spine (the one idea)

> The curated panels are the **prior**, not the **namer**. A panel only proposes a coarse bucket and
> hands the namer a ZFA anatomy **anchor**. The name itself comes from **descending the ZFA ontology**
> along the path the markers' real ZFIN expression converges on — so the label's **depth is earned
> from evidence**, never fixed by the panel. Three signals converge: **panel overlap** (prior +
> anchor) · **ZFA expression convergence** (the namer) · **stage plausibility** (a check). Agreement →
> a confident, deep call. Disagreement → an honest abstention that still hands back the forcing
> evidence. *Depth honesty is the whole thesis.*

---

## The call path

`Labeler.label(markers)` (`src/zlabel/label.py:1123`) is three steps; `decide` does the work:

```
Labeler.label(markers)                          label.py:1123   normalize -> score -> decide
  └─ normalize_markers(markers, synonyms)        genes.py:113    old symbol -> current ZFIN symbol
       └─ resolved_symbols(...)                  genes.py:136    keep only status == resolved
  └─ score_markers(normalized, panels)           panels.py:195   rank-weighted overlap -> BucketScore ladder
  └─ decide(scores, ...)                          label.py:489    the 5-branch honesty ladder
       ├─ _abstain(...)                           label.py:436    no_signal / structural / doublet / mixed
       ├─ _assign_rollup(...)                     label.py:820    near-tie, one germ layer (cap: medium)
       └─ _assign_named(...)                      label.py:691    clear winner / specificity rescue
            └─ resolve_label(symbols, anchor)     resolve.py:323  vote + seed + descend  ← the heart
                 └─ _descend(anchor, tally, ...)  resolve.py:253  roll down to the deepest converged term
       └─ _grade_confidence(...)                  label.py:363    4 components -> score -> tier (+ caps)
  -> Label                                        models.py:88    the evidence packet
```

`Labeler.trace(markers)` (`label.py:1157`) runs the *same* decision and records every intermediate
into a `LabelTrace` (`models.py:335`) — the designed introspection surface the notebook and
`zlabel-scope` both read. It records; it never re-decides.

---

## Thresholds — what each guards (and why)

| Constant | Value | Source | Guards |
|---|---|---|---|
| `MIN_SIGNAL` | 0.15 | `label.py:69` | Weak-signal veto: a top adjusted score below this abstains rather than pick the least-bad bucket. |
| `DOMINANCE_GAP` | 0.30 | `label.py:74` | Clear-winner test (lead over runner-up); also normalizes the margin confidence component. |
| `MARKER_SPECIFICITY_MIN` | 1/3 | `label.py:78` | Specificity rescue: a matched marker grounding under ≤ 3 of ~31 lineages survives the weak veto. |
| `COHERENCE_SAT` | 2.13 | `label.py:87` | Matched weight that saturates coherence (≈ three top-ranked markers). |
| `W_COHERENCE / MARGIN / GROUNDING / STAGE` | .40 / .30 / .20 / .10 | `label.py:104` | Confidence component weights (sum to 1). |
| `TIER_HIGH / TIER_MEDIUM` | 0.80 / 0.60 | `label.py:110` | Score → tier cutoffs; *low* is the floor for any assigned call. |
| `CONVERGENCE_MIN` | 3 | `resolve.py:54` | Distinct genes a ZFA term needs before it can seed or be descended into. |
| `DESCENT_SUPPORT_FRACTION` | 0.6 | `resolve.py:64` | A child must keep ≥ 60% of its parent's support to be entered — the thin-overcall stop. |
| `STOPLIST` | 5 roots | `resolve.py:72` | Content-free attractor terms (formal root, whole organism, anatomical structure/group/system) — never seeded, entered, or counted as a depth level. |

The **sibling-uniqueness** rule has no constant: in `_descend`, if the top two eligible children
**tie** on support the walk stops, because the markers have spread across subtypes rather than
converging on one. (This is why the muscle example stays at *musculature system*.)

---

## The `Label` packet (`models.py:88`)

| Group | Fields | Meaning |
|---|---|---|
| **The name** | `bucket`, `zfa_id` | The named ZFA term (or coarse panel bucket on fallback, or `mixed/unresolved`). |
| **Depth evidence** | `levels`, `depth` | Broad→specific name chain (minus STOPLIST) and its length. `depth` varies with evidence — this is the thesis. |
| **The call** | `abstained`, `ambiguity_flag`, `next_step` | Whether a decision was made; `none/mixed/underclustered/provisional`; `subcluster` or `None`. |
| **Confidence** | `confidence`, `confidence_score`, `confidence_components` | Tier, raw [0,1] score, and the four components. `None` iff abstained. |
| **Panel context** | `panel_bucket`, `panel_germ_layer`, `panel_scores` | The prior/anchor that was descended from; the raw scorer echo. |
| **Convergence evidence** | `convergent_genes`, `expression_evidence`, `positive_markers` | Genes that voted for the named term; their grounded `ExprHit`s; the panel-matched symbols. |
| **Forcing evidence** | `candidates`, `margin`, `ood` | The near-tie set (best-first, with margins), the raw lead, and the OOD flag — what a caller needs to override an abstention. |
| **State** | `states` | Orthogonal programs (`cycling`, …), reported on every Label including abstentions. |

**Invariants** (enforced in the model, `models.py:184`): `confidence`/`confidence_score` are `None`
**iff** `abstained`; a non-`in_set` `ood` only appears on an abstention.

**`ood` values** (`models.py:35`): `in_set` (force-able — reachable reference type; the default and
always the value for assigned calls) · `structural` (markers converge nowhere under any anchor — a
blind-spot) · `doublet` (contradictory germ layers) · `no_signal` (no identity hit). `structural`
and `doublet` are high-precision when they fire; `in_set` is a soft signal.

---

## The decision ladder (`decide`, `label.py:489`)

Buckets are ranked by **adjusted** score = matched-marker weight / identity-only denominator (total
weight minus state-only weight). Then:

- **A — no identity hit** → abstain, `ood=no_signal`.
- **B — top adjusted < `MIN_SIGNAL`** → **specificity rescue** if a matched marker's panel-IDF ≥
  `MARKER_SPECIFICITY_MIN` (name from that marker's panel); else abstain (`structural` if the markers
  seed nowhere, else `in_set`).
- **C — lead ≥ `DOMINANCE_GAP`, or only one bucket** → clear winner → `_assign_named` → **descend**.
- **D — near-tie** → if all contenders share one germ layer, `_assign_rollup` (tier capped at
  *medium*); otherwise abstain, `ood=doublet`.

**Confidence caps** (`_grade_confidence`, `label.py:363`): a rollup never exceeds *medium*; a *high*
single-bucket call needs real grounding/stage corroboration (`_supports_high`, `label.py:340`) —
strong panels alone top out at *medium* (the convergence cap).

---

## The descent in detail (`resolve.py`)

1. **Vote** (`resolve_label`, line 323): each distinct gene credits every ZFA term in its ZFIN
   expression records **plus all `is_a`/`part_of` ancestors** (`_term_with_ancestors`, line 119).
   Tally is distinct genes per term.
2. **Seed** (`_descend`, line 293): the most-supported anchor id with ≥ `CONVERGENCE_MIN` genes; ties
   broken toward the rarer (higher IC) then broader term. No anchor support → return nothing → the
   caller falls back to the coarse panel bucket.
3. **Descend** (line 300): step into the best-scored child (support × information-content, support
   dominant) **while** it keeps ≥ `CONVERGENCE_MIN` genes **and** ≥ `DESCENT_SUPPORT_FRACTION` of the
   parent's support **and** uniquely leads its siblings. Stop at the deepest such term — that is the
   label.

The **information-content** model (`build_information_content`, line 152) is `-log2(count/n_genes)`
over the loaded corpus — it only *weights* the per-step choice toward specificity; the support floors
do the gating. **Marker specificity** (`build_marker_specificity`, line 194) is the panel-IDF the
rescue uses: `1 / (number of identity anchors a gene grounds under)`. Both are built once at
`Labeler` init, entirely data-derived — the only hardcoded anatomy is the content-free `STOPLIST`.

---

## Why it is shaped this way

zlabel is the **validated layer-1 distillation** of `daniotype` (`../../../daniotype`), a much larger
predecessor whose critical review found it ran cleanly but *could not demonstrate it worked* — an
unvalidated LLM de-novo namer that confidently labeled artifacts. The lesson drove three choices
here: a **deterministic** core (no LLM in the decision), a **validation harness from day one**
(`benchmarks/daniocell_baseline_report.md` + the parent-child overcall audit, walled by `make gate`),
and **depth honesty** — report the level the evidence supports and abstain otherwise, instead of
always emitting a confident leaf. See [`../../docs/design.md`](../../docs/design.md).

---

## Glossary

- **ZFA** — Zebrafish Anatomy Ontology; the DAG of anatomy terms (`is_a`/`part_of`/`develops_from`).
  The vocabulary the namer descends. Loaded by `data.load_zfa` (`data.py:37`).
- **ZFIN wildtype expression** — curated gene → ZFA + ZFS records; the in-vivo evidence ("where this
  gene actually expresses"). Loaded by `data.load_zfin_expression` (`data.py:218`).
- **ZFS** — developmental-stage ontology (hpf ranges); used for the stage-plausibility component
  (`ground.stage_plausibility`, `ground.py:181`).
- **GAF synonyms** — ZFIN gene aliases / previous names; the normalization map
  (`data.load_gene_synonym_map`, `data.py:273`).
- **anchor** — a panel's `ontology_anchor`: the ZFA id(s) the descent seeds at (`panels.yaml`).
- **IC (information content)** — corpus rarity of a ZFA term, `-log2(count/n_genes)`; the IDF half of
  the per-step descent score.
- **panel-IDF / marker specificity** — how few lineages a gene marks; the rescue signal.
- **descent** — the anchor-rooted, support-weighted roll-down that names the cluster (`_descend`).
