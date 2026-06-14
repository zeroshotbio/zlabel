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
  `kind` (`identity` or `state`), a frozenset of curated marker symbols, and optional
  `subpanels` for finer resolution on subclusters. Domain knowledge lives here; the
  scorer just does arithmetic over it.
- **BucketScore** — the output of `score_markers` for one panel: the `bucket` name, a
  `score` in [0, 1] computed by rank-weighted overlap (`w(r) = 1 / log2(r + 1)` so
  the most significant markers drive the score), and the matched markers. The top
  candidate is always at index 0. Ambiguous and unresolved markers are excluded from
  both numerator and denominator so the score never reflects an uncertain symbol.

## Naming from anatomy (the convergence vote)

- **Convergence vote** — how zlabel *names* a cluster (`resolve.py`). Each marker's in-vivo
  ZFIN expression points at ZFA anatomy terms; every term and all its ancestors get one vote
  per distinct gene. The most specific term enough genes agree on wins. Panels propose a coarse
  prior; this vote does the naming.
- **IC / information content** — how specific a ZFA term is, measured from the data:
  `IC = -log2(fraction of all genes that ever express under the term)`. Rare, specific terms
  (endothelial cell) score high; near-root terms (whole organism) score ~0. IC is the vote's
  selector — the highest-IC term that clears the gates wins.
- **The three gates** — a term must clear all three to be a candidate: `CONVERGENCE_MIN`
  (at least 3 distinct genes vote for it), `STOPLIST` (a few content-free attractors like
  "whole organism" are never labels), and `IC_MIN` (at least 1.0 bits — screens near-root
  terms). All three are provisional, calibrated by the Phase 4b eval.
- **TermVote** — the internal candidate object `resolve.resolve_label` returns, one per
  surviving term (its ZFA id, name, the genes that voted for it, IC, and ancestor depth). Not
  a user-facing API; reach it via `zlabel.resolve` if you need it.

## Decision output

- **Labeler** — the entry point. `Labeler(stage_hpf=48).label([...markers...])` loads the
  ontologies once and returns a `Label`. The one object most users touch.
- **Label** — the evidence packet for one cluster. `bucket` is the named ZFA anatomy term the
  markers converged on (or the coarse panel bucket / `mixed/unresolved` when the vote found
  nothing). It also carries `panel_bucket`, `depth`, `convergent_genes`, the `confidence`, the
  markers and in-vivo `expression_evidence`, a one-line `rationale`, and a `next_step`.
  `.to_yaml()` serialises it.
- **bucket vs. panel_bucket** — `bucket` is the fine call (the named ZFA term, e.g.
  `muscle cell`); `panel_bucket` is the coarse prior that anchored it (the winning panel, e.g.
  `muscle`), kept visible so you see both the guardrail anchor and the finer name.
- **positive_markers vs. convergent_genes vs. expression_evidence** — three easily-confused
  marker sets. `positive_markers` matched the winning *panel*. `convergent_genes` are the
  markers whose in-vivo expression *voted for the named ZFA term* (the anatomy vote — may differ
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
- **convergence cap** — a confidence ceiling (distinct from the convergence *vote* above):
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
  `CONVERGENCE_MIN` genes while a broader parent term had more support (the IC-first sort favouring
  a rare specific term over the consensus). Phase 4b reports it; it is not yet tuned.

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
src/zlabel/resolve.py   ->  build_ic() · resolve_label() -> list[TermVote]               (Phase 4a)
src/zlabel/label.py     ->  decide() · Labeler.label() -> Label                         (Phase 3+4a)
src/zlabel/evaluate.py  ->  evaluate() over the Daniocell benchmark -> baseline report  (Phase 4b)
```
