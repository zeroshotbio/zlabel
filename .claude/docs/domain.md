# Domain primer — zlabel

Enough zebrafish single-cell biology to work in this repo. The design of record is
[`docs/design.md`](../../docs/design.md). 

## The task

Label one scRNA-seq **cluster** of whole-organism zebrafish (*Danio rerio*) cells
from its **marker genes**. Whole-organism, low-resolution atlases are labeled
**broad-first**: assign each cluster to a high-level tissue / germ-layer / lineage
bucket (neural, epidermis, muscle, blood, immune, endothelium, endoderm/gut,
mesenchyme/cartilage, notochord, pigment, germline, cycling, or mixed/unresolved),
then subcluster and re-label finer. A good label rests on **converging evidence**,
not a single gene.

## scRNA-seq in a paragraph

Single-cell RNA-seq gives a cells × genes count matrix, ~90–99% zeros. Cells are
clustered (e.g. Leiden); each cluster's **marker genes** are the genes
differentially expressed vs. the rest. zlabel starts from those marker genes — it
never sees the matrix and does not cluster.

## Zebrafish gene names (normalize first)

Official zebrafish symbols are lowercase; genes carry aliases and superseded names;
the teleost genome duplication left many `a`/`b` paralog pairs (`hoxa13a` /
`hoxa13b`). A valid marker can be missed purely because a dataset used an old
symbol. So **normalize every marker to its official ZFIN symbol before scoring**
(zlabel uses the ZFIN GAF synonym column).

## The ontology stack

- **ZFA** — Zebrafish Anatomy Ontology (~2,860 classes): a DAG of anatomy with
  `is_a` / `part_of` / `develops_from` edges. The vocabulary for tissue/anatomy labels.
- **ZFIN wildtype-expression** — curated gene → ZFA anatomy + ZFS stage records.
  The in-vivo evidence: where a marker actually expresses.
- **ZFS** — developmental-stage ontology (hpf ranges); used for stage plausibility.
- **CL** — species-neutral Cell Ontology; an optional secondary anchor for generic
  cell types (neuron, macrophage…) once resolution justifies it.

These are *data authorities*: ZFIN curates the files, OBO Foundry / GO host them; we
download and parse them (`scripts/setup_data.sh`). Which Python library does the
parsing is a separate, swappable choice.

## Converging evidence

zlabel combines three signals: (1) curated tissue **panel** scores — how strongly a
cluster's markers overlap a known bucket, and how far that bucket leads the runner-up;
(2) **ZFIN in-vivo expression** of those markers, grounded to **ZFA** anatomy — do they
actually express where the bucket says they should?; and (3) **stage** plausibility — do
the expression records span the sample's developmental age?

When the signals agree, confidence is `high`. Panels alone — with nothing in-vivo to
corroborate, or with anatomy that points elsewhere — top out at `medium` (the **convergence
cap**: panels propose, grounding and stage confirm). When no single bucket dominates but the
near-top contenders share a germ layer, zlabel rolls up to that tier (`underclustered`);
contradictory germ layers give `mixed/unresolved`. It never overcalls. The exact weighting
is an implementation detail — see [`design.md`](../../docs/design.md) and `label.py`.

## Additional Information

Additional documentation can be found in [`docs/reference/`](../../docs/reference/).
