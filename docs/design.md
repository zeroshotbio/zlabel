# zlabel — design

## What it is

A small, readable library that **labels one scRNA-seq cluster from its marker
genes**, for whole-organism zebrafish (*Danio rerio*). 

**Input**: a cluster's marker genes (+ developmental stage).<br>
**Output**: a cell-identity label **at the deepest tier the evidence supports**, with an evidence packet — or an honest abstention. 

> [!CAUTION]
> It does not cluster cells (the caller does, with `scanpy` probably). 

This is **layer 1 only**.

### Rationale

zlabel is the clean distillation of `daniotype` (`../daniotype`), a ~11k-LOC
predecessor (descent + spine + gate + walk + audit + log). A critical review of
daniotype found it ran but could not *demonstrate* it worked (no validation leg),
its LLM de-novo naming was unmeasured and likely sparse at 48 hpf, and it could
confidently name QC artifacts. The conclusion was to rebuild the one valuable thing
— grounded cluster naming — as something a person can read top-to-bottom (the
nanoGPT / smolagents bar), with a validation leg from day one.

## What it does (the loop)

A label rests on **converging evidence, not one gene**:

1. **Normalize gene symbols** → official ZFIN symbol (resolve aliases + `a`/`b` paralogs) before anything else.
2. **Score markers against curated tissue panels** → a ranked bucket table; the winning panel is the coarse prior, and its ontology anchor is the root the namer descends from.
3. **Descend from the anchor on ZFA anatomy** → for each marker, look up ZFIN in-vivo expression and walk the ZFA ancestor DAG; tally distinct genes per anatomy term; seed at the panel's ontology anchor and roll *down* into the best-supported child while the markers keep converging on a single subtype (the support floor + unique-winner stop). The deepest such term names the cluster. Depth falls out of the evidence: a tight endothelial panel resolves to a cell type; generic muscle markers stay at the broad muscle level.
4. **Guardrail (now intrinsic) + stage** → the name is descended from the anchor, so it is always at or under it and the old contradiction check is folded into the walk; an anchor the markers do not support falls back to the coarse panel bucket. Check stage plausibility (ZFS) as a confidence component.
5. **Decide** → one dominant, corroborated bucket with convergent anatomy → assign with confidence; or, on a weak panel signal, a single sharply lineage-specific marker rescues the call (named from that marker's panel); otherwise `mixed/unresolved` (honest abstention) or a germ-layer rollup.
6. **Emit a `Label` evidence packet** → bucket (named ZFA term or coarse fallback), levels (ZFA ancestry chain), depth, panel_bucket (the prior), convergent_genes, confidence, expression_evidence, rationale.

> [!WARNING]
> The LLM is **not** in this loop for v1 (see §LLM).

### Resolution: the evidence names at whatever depth it supports

`label(markers)` is **resolution-agnostic** — it returns the *deepest ZFA anatomy term
the markers converge on in vivo* and stops (rolling up) rather than overcalling. The curated
panels are the **coarse prior and the trusted anchor the namer descends from**, not the naming authority.
`Label.depth` (`len(levels)`) is a real, evidence-dependent integer — not a hardcoded tier
ladder. The same function resolves finer on a tighter subcluster and shallower on a
heterogeneous one; that is the engine being honest, not a failure.

**The specificity rescue.** The panel score is a coarse prior, not a hard fraction veto: a
single sharply lineage-specific marker is strong evidence on its own (a scientist calls
"muscle" from `myod1` alone, ignoring the rest). So a cluster that would abstain on a weak
panel signal is rescued when a matched marker's panel-specificity — its inverse panel-frequency
over ZFIN expression (`resolve.build_marker_specificity`) — clears `MARKER_SPECIFICITY_MIN`
(1/3: it grounds under at most 3 of the 31 lineage anchors); it is then named by descending from
that marker's panel anchor. The rescue is contained to the abstain branch — every confident call
is unchanged, and the convergence descent and overcall audit are untouched. On the Daniocell eval
it roughly quadruples coverage (37 → ~146 named) while holding broad agreement at the named bar;
a gold-blind audit of the recovered disagreements puts true precision near 86%, since about half
are crosswalk/annotation artifacts rather than engine errors.

**Forcing or abstaining — the caller decides, on the evidence.** zlabel labels one cluster; it
never emits a blind forced guess. So even when it abstains it exposes the evidence a caller needs
to force a call itself: `Label.candidates` (the near-tie buckets, best-first, each with its margin
to the top), `Label.margin` (the raw lead of the top adjusted score over the runner-up), and
`Label.ood` — a flag separating "uncertain among known types" from "genuinely unassigned." `ood`
is `in_set` when the markers reach a reference type the descent can seed on (the selection
residual — force-able), `structural` when they converge on no named anatomy under any anchor (a
blind-spot or novel type), `doublet` on contradictory germ layers, and `no_signal` on no identity
hit. The caveat the field docs lead with: `structural`/`doublet` are high-precision *when they
fire*, but `in_set` is a soft signal, not a certification — a broad attractor panel can mask a
structural blind-spot (periderm seeding under epidermis), so `in_set` has high recall and
imperfect precision. The flags are derived at label time from signals `decide()` already computes,
with no per-dataset calibration; the force/no-force threshold on `margin` is left to the caller
(baking one in would re-introduce the forced mode this design rejects).

The panels themselves are a versioned **v1 starter set** (see `docs/reference/
cell_labelling_playbook.md §7`): *"These are starter panels for first-pass annotation.
They must be versioned and adapted to stage, genome build, sequencing chemistry, and
atlas source. Do not treat this table as a final marker authority."* They will be
replaced by a curated gold standard as the eval matures. The starter set has since been
expanded to a complete, atlas-spanning broad taxonomy (33 buckets — 31 identity + 2
state — covering Daniocell / Zebrahub / ZSCAPE populations); see
[`docs/reference/panels_and_markers_reference.md`](reference/panels_and_markers_reference.md)
for the per-marker rationale, anchors, and evidence, and
[`benchmarks/cell_population_coverage.yaml`](../benchmarks/cell_population_coverage.yaml)
for the coverage proof.

What v1 deterministic *won't* do: **open-ended de-novo naming of types with no
expression footprint.** That is the LLM's job (§LLM).

## Known limit: selection is bounded by reference granularity

Gate fixed and forcing answered — both gold-free, both generalizing. The one residual zlabel cannot
cross is *selection*: on a low-resolution cluster whose markers are promiscuous, a broad **attractor**
panel (epidermis, endothelium, mesenchyme, neural) out-scores the true lineage. This is a *measured*
structural limit, not an open problem — and the record is worth stating precisely, because "we stopped"
and "we measured exactly where the wall is and why" are different artifacts.

**What is fixed, gold-free.** The panel *gate* (the F2 specificity rescue: a single sharply
lineage-specific marker rescues a weak-signal cluster — ~4× coverage at ~86% true precision once the
Stage-L key errors are credited) and *forcing honesty* (the candidate set + `ood` + `margin`, with the
caller owning the force/abstain decision). Both shipped.

**What is bounded, and why — the bound is earned, not exhausted.** Seven independent levers NO-GO'd on
the same attractor-selection residual. Six are *marker-derived*: convergence-gating (F3), descent-level
IDF (F4), grounding-argmax (Stage B), negative markers / mutual exclusion (N0), gold-free attractor
derivation (N0b), and the descent-axis fix (D2 — whose premise proved false: the "wrong-axis overshoots"
are selection failures, 35 of 42 named disagreements won by an attractor panel, not descent crossings).
The seventh makes the bound defensible: the diagnosis itself nominated the escape hatch — the cues a
human uses to disambiguate (developmental stage, tissue topology, context) are simply not in a marker
list — so we tested the one such cue the system *does* receive, the **known HPF**, and it is
non-discriminative: wrong (attractor) calls are stage-plausible (mean 0.938) almost exactly like correct
ones (0.995), only ~2% of wrong calls implausible. Testing the diagnosis's own proposed fix and finding
it flat is what makes this a measured boundary, not "we didn't try the right signal."

And stage closes for a reason that **unifies three of the walls into one root cause**: it fails because
ZFIN's stage annotations are *broad* (a marker spans 20+ developmental stages), so a known HPF lands
inside almost everything's plausible window — the same shape as F4 (ZFIN expression sparsity) and a
hypothetical CL grounding layer (ZFIN carries 0% Cell-Ontology annotation). **Three walls reduce to one:
the reference data (ZFIN) is not fine-grained enough — not the algorithm.** That is the map of the
boundary, and it says what would actually move the needle on a future dataset: finer reference
annotations, not a cleverer rule.

**What was ruled out, on evidence.** Grounding against the **Cell Ontology (CL)** — redundant *and*
walled: ZFA already carries the cell-type axis (441 terms carry CL cross-references, all under the
`cell` root ZFA:0009000 with zero overlap into the region roots, a clean verified split), so CL adds no
axis ZFA lacks; and CL grounding is blocked anyway, since ZFIN expression carries 0% CL annotation and
only ~21% of panel anchors map to CL. **Negative markers** — the gold-free attractor set they need is
underivable (no marker-distribution or anchor-shape signal separates the attractors from specific
lineages whose own markers are broad in ZFIN). **HPF as a selector** — non-discriminative (above); it
stays the soft confidence component it already is, and a caller who knows the stage can apply it to the
candidate set themselves.

**The fallible-key caveat.** A gold-blind audit (Stage L) found ~14% of apparent errors (16 of 112) are
Daniocell's own labels, not zlabel's — so the residual is partly benchmark error, and true performance
is bounded below by the key.

**The generalization claim.** Every shipped mechanism is dataset-composition-independent and gold-free
(scored against the fixed ZFIN/panel reference, never the query), so it carries to other datasets
unchanged. That — not a Daniocell agreement number — was the goal. The system now knows exactly what it
can and cannot do, and why.

## Public surface (the whole API)

### Phase 2 primitives (lower-level API)

Gene normalization and panel scoring are live:

```python
import zlabel

synonyms = zlabel.load_gene_synonym_map("data/ontologies/zfin.gaf")
result = zlabel.normalize_symbol("flk1", synonyms)
# NormalizedSymbol(input='flk1', status='resolved', symbols=frozenset({'kdrl'}), note=None)

panels = zlabel.load_panels("src/zlabel/panels.yaml")   # curated buckets (see panels_and_markers_reference.md)
normalized = zlabel.normalize_markers(["mylpfa", "acta1b", "tnnt3a", "myod1", "myog"], synonyms)
scores = zlabel.score_markers(normalized, panels)
scores[0]   # BucketScore(bucket='muscle', score=0.8105, kind='identity', ...)
```

### Phase 4a + 4b (shipped — the resolution engine + eval)

```python
from zlabel import Labeler

labeler = Labeler(stage_hpf=48)                  # loads ZFA + ZFIN-expr + GAF + panels once
label = labeler.label(["mylpfa", "acta1b", "tnnt3a", "myod1", "myog"])
# Label(bucket="musculature system",              # named ZFA term, descended from the muscle anchor
#       depth=1, zfa_id="ZFA:0000548",            # the honest broad level -- generic muscle markers
#       levels=("musculature system",),           # with no single subtype they all converge on
#       panel_bucket="muscle",                     # coarse prior (kept visible)
#       convergent_genes=("acta1b", "mylpfa", "myod1", "myog", "tnnt3a"),  # all five converge here
#       confidence="high", abstained=False, next_step="subcluster")
print(label.to_yaml())                           # the evidence packet
```

> [!NOTE]
> Five generic muscle markers name `musculature system`, not a subtype: the anchor-rooted descent
> (§Resolution) walks down only while the markers converge on a *single* child, and here they spread
> across muscle subtypes, so it stops at the broad muscle level. The support floor + unique-winner stop
> keep the descent from over-specifying — the Phase 4b overcall audit finds 1 thin call in 36 named
> clusters. Fine-naming on a richer truth set is still future work.

One entry point. The public surface is small — `Labeler`, `Label`, and the Phase 1/2
primitives — while the decision code beneath it stays readable and unit-tested.

### Confidence rubric (provisional — measured in Phase 4b; calibration deferred)

`Labeler` grades an assigned call on a weighted 0–1 score: **coherence** 0.40 (rank-weighted
strength of the winner's markers) + **margin** 0.30 (lead over the runner-up) + **grounding**
0.20 (fraction of the winning panel's matched markers whose ZFIN expression grounds under the
named ZFA term, or the panel anchor when the vote fails) + **stage** 0.10 (fraction on-stage for the
sample). Tiers: ≥ 0.80 `high`, ≥ 0.60 `medium`, else `low`. Two caps keep it honest — a
germ-layer rollup never exceeds `medium`, and `high` requires real anatomy convergence (a fallback
to the coarse bucket grounds against the broad anchor, lowering grounding and preventing false `high`). The weights are a
first cut; Phase 4b measured the baseline — calibration is deferred.

### Introspection: `trace()` (advanced surface)

`Labeler.trace(markers)` (and the module-level `label.trace(...)` over shared resources, for a
caller that varies stage per request) returns a `LabelTrace`: the same decision as `label()` plus
the intermediates the `Label` omits — the normalization outcomes (which markers were dropped), the
full panel ladder, the **complete ZFA convergence descent with per-term gate pass/fail, near-misses
included**, and the decision branch taken. It is opt-in and faithful: it threads a `recorder`
through the real `decide()` / `resolve_label` (no second decision path), so `trace.label` is
identical to `label(markers)` and the labeling path is unchanged when not tracing. `LabelTrace`
lives on the advanced surface (`zlabel.models`), not the top-level API — it exists to *explain* a
call (e.g. why a low-resolution cluster abstained, or what it nearly named), which is what a
companion introspection UI consumes.

## Repo structure (~9 core modules, ~2,800 LOC core)

Files marked [P1] / [P2] shipped; later phases show their planned target.

```text
zlabel/
  pyproject.toml          # uv · ruff (120) · pyright basic · py3.13 · minimal deps  [P1]
  README.md               # what it is + the loop + quickstart                         [P1]
  Makefile                # setup / format / lint / lint-docstrings / type / test / verify [P1]
  scripts/
    setup_data.sh         # curl zfa.obo, zfin.gaf, zfin_wildtype_expression.txt -> data/ontologies/  [P1]
    build_daniocell_eval.py  # Daniocell clust markers + parent tissue -> benchmarks/ csv  [P4b shipped]
  src/zlabel/
    data.py     # LIFT (pure): load ZFA via obonet; parse ZFIN-expr TSV; load GAF synonym map  [P1]
    genes.py    # normalize_symbol() via GAF alias/paralog resolution                           [P2]
    panels.yaml # THE MODEL: curated buckets -> {germ_layer, tissue, lineage, kind, markers[], cite, ontology_anchor[]}  [P2]
    panels.py   # load panels + rank-weighted overlap score (readable, no heavy dep)            [P2]
    ground.py   # pure fns: expression_lookup / grounds_under / stage_plausibility              [P3 shipped]
    label.py    # converging-evidence decision -> Label  (the heart)                           [P3+4a shipped]
    models.py   # Label evidence packet (pydantic) + to_yaml()                                 [P3+4a shipped]
    resolve.py  # anchor-rooted ZFA convergence namer (build_information_content + resolve_label) [P4a]
    evaluate.py # run on Daniocell clusters -> agreement + coverage + overcall audit            [P4b shipped]
    explain.py  # OPTIONAL [llm] extra: thin narrator over a finished Label                    [P7]
    cli.py      # typer: zlabel label --markers ... --stage 48 ; zlabel eval <csv>            [P5]
  benchmarks/   # committed eval substrate: daniocell_eval.csv + crosswalk + baseline report  [P4b shipped]
  data/         # gitignored: downloaded ontologies
  tests/        # genes, panel scoring, ground lookups, label decision, eval — real unit tests, no LLM
  notebooks/
    build-demos/
      phase_01.ipynb           # data-layer walkthrough + explorer (Phase 1)        [P1 shipped]
      phase_02.ipynb           # genes + panels walkthrough + explorer (Phase 2)    [P2 shipped]
      phase_03.ipynb           # grounding + the decision, unfolded (Phase 3)       [P3+4a shipped]
      phase_04.ipynb           # Daniocell eval diagnostic workbench (Phase 4b)     [P4b shipped]
    demo/
      01_label_one_cluster.ipynb    # the muscle-cluster walkthrough                [P5]
      02_cluster_with_scanpy.ipynb  # layer-2: adata -> leiden -> rank_genes -> zlabel [P6]
      03_end_to_end.ipynb           # layer-3: a real 48 hpf subset, start to finish   [P6]
```

**Core deps (added per phase):** Phase 1 obonet + networkx; Phase 2 adds pyyaml;
Phase 3 adds pydantic; Phase 4b keeps the core unchanged — the evaluator is stdlib +
these core deps. **No pandas, numpy, scanpy, anndata, decoupler, or pydantic-ai in the
core** — scanpy/anndata live in the optional `[eval]` extra (the benchmark builder; also
the notebooks), and pydantic-ai will live in the optional `[llm]` extra. The labeler takes
strings in, hands an evidence packet out.

## Lift vs. rewrite (zero daniotype dependency)

- **LIFT ~verbatim (pure, already clean):** the ZFA OBO loader + edge-type-aware
  ancestors; the ZFIN wildtype-expression TSV parser; the GAF synonym map; the ZFS
  stage→hpf table. Sources: daniotype `ontology/{zfa,zfin_expression,go,zfs_stages}.py`.
- **REWRITE as small pure functions:** the grounding lookups (strip the pydantic-ai
  `RunContext` / `DescentDeps` wrappers → `f(loaded_data, query) -> dict`) and the
  gene normalizer.
- **NEW (the value):** `panels.yaml`, the overlap scorer, the decision in `label.py`,
  the `Label` packet, the `evaluate` harness.
- **DROP entirely:** descent panel/orchestrator, gate, decision-log/replay, walk,
  audit notebooks, schema registry, marker DB — all of daniotype's machinery.

## Validation (built in from day one)

`build_daniocell_eval.py` derives a small benchmark CSV (`cluster_id, markers, broad_tissue,
tissue_name, stage_hpf`) from the public Daniocell release (GEO GSE223922): one row per fine
`clust`, with its parent `tissue` as the gold broad label and top-25 computed markers. Only the
derived CSV plus a reviewed, fail-closed `{tissue -> broad ZFA anchor}` crosswalk are committed
under `benchmarks/` (the ~2.5 GB source is not). `evaluate.py` runs the engine over it and scores
**broad agreement** in ZFA-ancestry space (`grounds_under`), reporting **coverage**, the
**named/fallback/rollup/abstain** split, **confidence-by-correctness**, and a structural
**parent-child overcall audit** — a regression guard that the descent does not overcall (a
specific term winning on the bare `CONVERGENCE_MIN` while a broader parent had more support): 1 thin
call in 36 named clusters. The engine is untouched by the eval; the audit replays the vote tally
privately. Daniocell's broad labels cannot validate
within-bucket fine-naming, so depth correctness there is reported by the structural audit, not
checked against truth — finer-reference depth validation (ZSCAPE/Zebrahub) and bare-LLM /
panels-only baselines are deferred to a future calibration pass.

## Build order (7 phases, one PR each)

See [`.claude/docs/workflow.md`](../.claude/docs/workflow.md) for the per-phase
discipline and the review bar.

1. **Skeleton + data** — repo, `pyproject`, `setup_data.sh`, `data.py` loaders + fixture tests.
2. **Genes + panels** — `normalize_symbol`, `panels.yaml`, the overlap scorer + tests.
3. **Ground + label** — grounding lookups, then the decision in `label.py` → `Label`; unit-test the worked examples.
4. **Resolution engine + eval** — split into two PRs:
   - **4a (engine)** — `resolve.py` support-weighted, anchor-rooted ZFA convergence namer (descends from the panel anchor, folding the guardrail into the walk); `label.py`/`models.py` wired to name from ZFA; panels supply the coarse prior + the descent anchor.
   - **4b (eval, shipped)** — `build_daniocell_eval.py` + `evaluate.py` + the Daniocell crosswalk; broad agreement, coverage, the named/fallback/abstain split, and the parent-child overcall audit. *The proof it works.*
5. **CLI + notebook 01** — `zlabel label/eval`; the one-cluster walkthrough.
6. **Notebooks 02/03** — scanpy clustering → markers → zlabel, then end-to-end.
7. **LLM (optional)** — `explain.py`, behind the `[llm]` extra.

## LLM: deferred fast-follow

v1 ships deterministic, no pydantic-ai in core — **but the seam is designed in.**
`label.py` returns a structured `Label` packet specifically so an LLM step drops in
without reshaping the core. Two roles, in order:

1. **Narrator** (`explain.py`, trivial) — prose rationale over a finished, already-decided packet.
2. **Fine de-novo namer** (the real reason we want it) — on subclusters with no
   curated panel, coin a specific name from looked-up ZFA / expression evidence
   under cite-discipline. This is where "label lower-level clusters" becomes fully
   general.
