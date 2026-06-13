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
src/zlabel/label.py     ->  decide() · Labeler.label() -> Label                         (Phase 3)
```
