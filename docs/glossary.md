# Glossary & concepts (ELI5)

A quick place to flip to when a term, file, or website in the code is unfamiliar.
Intentionally shallow — enough to read the code with confidence. It grows as zlabel
does. For the full story see [`design.md`](design.md), the domain primer in
[`.claude/docs/domain.md`](../.claude/docs/domain.md), and the deeper
[`reference/cell_labelling_playbook.md`](reference/cell_labelling_playbook.md).

## The one-sentence picture

You give zlabel the **marker genes** of one **cluster** of zebrafish cells; it
checks those genes against curated **panels** and real **in-vivo expression**, and
returns a tissue/cell-type **label** with its evidence — or an honest "not sure".

## Biology terms

- **scRNA-seq** — single-cell RNA sequencing. Measures which genes are "on" in each
  individual cell. Output is a big cells × genes table of counts (mostly zeros).
- **Cluster** — a group of cells with similar expression, found by the caller (e.g.
  scanpy/Leiden). zlabel labels *one* cluster at a time; it never clusters.
- **Marker genes** — the genes most distinctively "on" in a cluster vs. the rest.
  These are zlabel's input.
- **Cell identity vs. state** — *identity* is what a cell is (muscle, neuron);
  *state* is what it's doing (dividing, stressed). A stressed muscle cell is still
  muscle. zlabel labels identity and keeps state separate. Tracked via the `kind`
  field in `panels.yaml` (`identity` or `state`).
- **Broad-first** — on a low-resolution cluster, the honest call is a broad bucket
  (muscle, blood, neural...). Finer labels come after sub-clustering. Broad is a
  floor, not a ceiling.
- **Gene symbol normalization** — the same gene can appear under old names or
  aliases. We map every marker to its current official name first, or it silently
  goes unscored.
- **Paralog (a/b genes)** — zebrafish duplicated much of its genome, so genes often
  come in pairs like `hoxa13a` / `hoxa13b`. One old name can map to several current
  paralogs, so the synonym map keeps all of them.

## Data authorities (what zlabel reads, and why)

- **ZFIN** ([zfin.org](https://zfin.org)) — the zebrafish database: official gene
  names, aliases, and curated expression. The source of two of our three files.
- **ZFA** — Zebrafish Anatomy ontology. A graph of body parts linked by `is_a`
  (a-kind-of), `part_of`, and `develops_from`. zlabel's vocabulary for tissue labels
  and the "where does this express?" grounding. File: `zfa.obo`.
- **ZFS** — Zebrafish developmental Stages (e.g. `Long-pec` ≈ 48 hours). Used to
  sanity-check that a label makes sense for the sample's age. Wired up in Phase 3
  (`ground.stage_plausibility`).
- **GO / GAF** — Gene Ontology Annotation File. zlabel uses it only for its synonym
  column (gene aliases → current symbols). File: `zfin.gaf`.
- **Daniocell / Zebrahub / ZCL** — published zebrafish atlases used as ground truth
  and references for evaluation (later phases), not loaded by the core.
- **CL / Uberon** — cross-species cell-type / anatomy ontologies; optional bridges
  for interoperability, not used in the core yet.

## File formats you'll see

- **`.obo`** — a plain-text ontology. Stanzas like `[Term]` with `id:`, `name:`,
  `is_a:`, and `relationship:` lines. Parsed by `obonet` into a graph.
- **GAF** — tab-separated GO annotations, one row per gene-function fact, `!` lines
  are comments. We read the gene symbol (col 3) and synonyms (col 11).
- **ZFIN wildtype expression** — tab-separated, no header, 15 columns: a gene, the
  anatomy (ZFA) it was seen in, and the stage range. One observation per row.

## Panels and scoring

- **Panel** — one entry in `panels.yaml`. Has a `bucket` name (e.g. `muscle`), a
  `kind` (`identity` or `state`), a frozenset of curated marker symbols, and (for
  identity panels) an `ontology_anchor` the namer descends from. Domain knowledge
  lives here; the scorer just does arithmetic over it.
- **BucketScore** — the output of `score_markers` for one panel: the `bucket` name, a
  `score` in [0, 1] computed by rank-weighted overlap (`w(r) = 1 / log2(r + 1)` so
  the most significant markers drive the score), and the matched markers. The top
  candidate is always at index 0. Ambiguous and unresolved markers are excluded from
  both numerator and denominator so the score never reflects an uncertain symbol.

## Naming from anatomy (the anchor-rooted descent)

- **Convergence descent** — how zlabel *names* a cluster (`resolve.py`). Each marker's in-vivo
  ZFIN expression points at ZFA anatomy terms; every term and all its `is_a`/`part_of` ancestors
  get one vote per distinct gene. The namer then seeds at the winning panel's `ontology_anchor`
  and rolls *down* the graph, at each step taking the child the most genes support, and stops at
  the deepest term the markers still agree on. Panels propose the coarse prior and the anchor;
  this descent does the naming.
- **Support-weighted (TF-IDF)** — each descent step picks the child by support × IC, with support
  (the count of distinct genes backing it) the dominant signal. **IC** (information content,
  `IC = -log2(fraction of all genes that ever express under the term)`) measures how specific a
  term is — rare terms like endothelial cell score high, near-root terms ~0 — and here it only
  tilts the per-step choice toward specificity; it is no longer a hard gate.
- **When the descent stops** — a child is entered only while it keeps at least `CONVERGENCE_MIN`
  distinct genes (3), retains at least `DESCENT_SUPPORT_FRACTION` (0.6) of its parent's support,
  and uniquely leads its siblings (a support tie means the markers spread across subtypes, so the
  walk stops). `STOPLIST` roots (content-free attractors like "whole organism") are never seeded
  or entered. The thresholds are provisional; Phase 4b measured the baseline — calibration is
  deferred. Because the name descends *from* the anchor it always sits at or under it, so the
  panel guardrail needs no separate contradiction check.
- **Specificity rescue (panel-IDF)** — a weak panel signal normally abstains, but a single sharply
  lineage-specific marker rescues the call (`label.decide`, precheck B). Each gene's **panel-IDF**
  (`resolve.build_marker_specificity`, `1 / #lineage anchors it grounds under`) measures how
  lineage-specific it is; a matched marker clearing `MARKER_SPECIFICITY_MIN` (1/3 — it grounds under
  at most 3 of the 31 lineages) names the cluster by descending from that marker's panel. Contained
  to the abstain branch; the descent and overcall audit are unchanged.
- **TermVote** — the candidate object `resolve.resolve_label` returns: the named terminal term
  (a one-element list, or empty when nothing converges), with its ZFA id, name, the genes that
  backed it, IC, and ancestor depth. Not a user-facing API; reach it via `zlabel.resolve` if you
  need it. (The richer per-term `TermVoteTrace` in `zlabel.models` is what `trace()` exposes.)

## Decision output

- **Labeler** — the entry point. `Labeler(stage_hpf=48).label([...markers...])` loads the
  ontologies once and returns a `Label`. The one object most users touch.
- **Label** — the evidence packet for one cluster. `bucket` is the named ZFA anatomy term the
  markers converged on (or the coarse panel bucket / `mixed/unresolved` when the descent found
  nothing). It also carries `panel_bucket`, `depth`, `convergent_genes`, the `confidence`, the
  markers and in-vivo `expression_evidence`, a one-line `rationale`, and a `next_step`.
  `.to_yaml()` serialises it.
- **candidates / ood / margin (the forcing evidence)** — what a caller uses to force a call when
  zlabel abstains (zlabel itself never forces a blind guess). `candidates` is the near-tie set
  (the buckets within `DOMINANCE_GAP` of the top, best-first, each with its `margin_to_top`);
  `margin` is the raw lead of the top adjusted score over the runner-up; `ood` flags the regime —
  `in_set` (a reference type the descent can reach: force-able), `structural` (converges on no
  named anatomy: a blind-spot / novel type), `doublet` (contradictory germ layers), `no_signal`
  (no identity hit). `structural` / `doublet` are high-precision when they fire; `in_set` is a
  soft signal — a broad attractor panel can mask a blind-spot, so it has high recall, imperfect
  precision. All derived at label time, no per-dataset calibration; the force threshold is the
  caller's.
- **attractor panel** — one of the four broad panels (epidermis, endothelium, mesenchyme, neural)
  whose markers are promiscuous enough (they express across many unrelated tissues) to out-score the
  true lineage on a low-resolution cluster. The root cause of the **selection residual**.
- **selection residual** — the error class where the correct lineage panel is scored below an
  attractor panel. A measured structural limit, bounded by the selection/decision layer of the current
  architecture (panel-overlap signal + marker promiscuity) — not reference granularity (finer data was
  injected and did not convert) and not the clusters being unresolvable in principle; see
  `docs/design.md` §Known limit.
- **bucket vs. panel_bucket** — `bucket` is the fine call (the named ZFA term, e.g.
  `muscle cell`); `panel_bucket` is the coarse prior that anchored it (the winning panel, e.g.
  `muscle`), kept visible so you see both the guardrail anchor and the finer name.
- **positive_markers vs. convergent_genes vs. expression_evidence** — three easily-confused
  marker sets. `positive_markers` matched the winning *panel*. `convergent_genes` are the
  markers whose in-vivo expression *backed the named ZFA term* (the anatomy descent — may differ
  from the panel matches). `expression_evidence` is the list of in-vivo records (`ExprHit`)
  behind the call.
- **depth** — how specific the label is, derived from the evidence (`len(levels)`, the length of
  the ZFA ancestry chain), not a fixed tier ladder. A tight endothelial cluster resolves deep
  (cell type); a mixed neural one stays shallow (CNS). Depth honesty is the thesis.
- **ExprHit** — one grounded marker's in-vivo evidence: a marker symbol and a ZFA anatomy term
  it expresses in that sits under the named term (or the bucket's anchor).
- **Confidence** — the tier of an assigned call: `high`, `medium`, or `low` (`None` when the
  cluster abstains).
- **abstained** — when the evidence doesn't converge, zlabel declines: `bucket` is
  `mixed/unresolved` and `confidence` is `None`. An honest "not sure" beats a wrong label.
- **underclustered** — when no single bucket dominates but the near-top contenders share a germ
  layer, zlabel rolls up to that coarser tier instead of guessing the finer one.
- **ambiguity_flag** — the `Label` field naming the call's shape: `none` (a clean assigned call,
  including a single-marker rescue), `underclustered` (a germ-layer rollup), `mixed` (abstained on
  contradictory germ layers — a doublet), or `provisional` (abstained on no, or too-weak, identity
  signal).
- **convergence cap** — a confidence ceiling (distinct from the convergence *descent* above):
  strong panels alone top out at `medium`; `high` is reserved for calls the in-vivo expression
  (or stage) actually corroborates.

## Evaluation (Phase 4b)

- **Daniocell benchmark** — a committed CSV (one row per Daniocell fine cluster: its markers and
  its parent broad tissue) derived from the public Daniocell atlas. zlabel's broad call is scored
  against the gold tissue. Lives in `benchmarks/`.
- **crosswalk** — the reviewed, fail-closed `{Daniocell tissue -> broad ZFA anchor(s)}` map used
  for scoring. Agreement means the prediction's ZFA term grounds (sits at or under) a gold anchor;
  unmapped tissues are `not_scored`, never guessed.
- **broad agreement / coverage** — the fraction of scored clusters whose call lands in the right
  broad tissue; coverage is the non-abstain rate (named + fallback + rollup).
- **overcall audit** — a structural check for false precision: a named term that won on the bare
  `CONVERGENCE_MIN` genes while a broader parent term had more support. Phase 4b reports it as a
  regression guard on the descent (the live count is in the benchmark report); `make gate`
  mechanizes the guard, failing on a rise in the count (install the pre-commit hook with
  `make hooks`).

## How data flows through zlabel

```
scripts/setup_data.sh   ->  data/ontologies/{zfa.obo, zfin.gaf, zfin_wildtype_expression.txt}
        (download)               (gitignored; not committed)
                                        |
                                        v
src/zlabel/data.py      ->  load_zfa() · load_zfin_expression() · load_gene_synonym_map()
        (Phase 1)               (files -> in-memory graph + dicts)
                                        |
                                        v
src/zlabel/genes.py     ->  normalize_symbol() · normalize_markers()             (Phase 2)
src/zlabel/panels.py    ->  load_panels() · score_markers() -> list[BucketScore] (Phase 2)
                                        |
                                        v
src/zlabel/ground.py    ->  expression_lookup() · grounds_under() · stage_plausibility() (Phase 3)
src/zlabel/resolve.py   ->  build_information_content() · build_marker_specificity() · resolve_label() -> list[TermVote] (Phase 4a)
src/zlabel/label.py     ->  decide() · Labeler.label() -> Label                         (Phase 3+4a)
src/zlabel/evaluate.py  ->  evaluate() over the Daniocell benchmark -> baseline report  (Phase 4b)
```
