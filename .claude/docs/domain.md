# Domain primer — zlabel

Enough zebrafish single-cell biology to work in this repo. The design of record is
[`docs/design.md`](../../docs/design.md). 

## The task

Label one scRNA-seq **cluster** of whole-organism zebrafish (*Danio rerio*) cells
from its **marker genes**. Whole-organism, low-resolution atlases are labeled
**broad-first**: assign each cluster to one of the curated panel buckets — 33 in all
(31 identity lineages spanning every germ layer, plus 2 orthogonal state programs; see
`docs/reference/panels_and_markers_reference.md`) — or to mixed/unresolved when the
evidence does not converge, then subcluster and re-label finer. A good label usually rests on
**converging evidence**; the exception is one sharply lineage-specific marker, which rescues an
otherwise-weak signal (see Converging evidence below).

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

zlabel combines three signals: (1) curated tissue **panel** scores — the winning panel
is the **coarse prior and the anchor the namer descends from**, not the naming authority; (2) **ZFIN
in-vivo expression** grounded to **ZFA** anatomy — each marker votes for the ZFA terms it
expresses in and all their is_a/part_of ancestors; the support-weighted descent
(`resolve.py`) seeds at the panel anchor and rolls down to the deepest term the markers converge on;
and (3) **stage** plausibility — do the expression records span the sample's developmental age?

The panels (a v1 starter set, see `docs/reference/cell_labelling_playbook.md §7`) propose
a coarse prior and the descent anchor. ZFA convergence names. Because the name is descended *from*
the anchor it always sits at or under it — the old guardrail is folded into the walk; an anchor the
markers do not support falls back to the coarse panel bucket (with capped confidence). `Label.depth` is a real,
evidence-derived integer — endothelium resolves to a cell type, muscle to a tissue, a mixed
neural panel stays at CNS. Depth honesty is the whole zlabel thesis.

When the signals agree, confidence is `high`. Panels alone top out at `medium` (the
**convergence cap**). When no bucket dominates but contenders share a germ layer, zlabel
rolls up to that tier; contradictory germ layers give `mixed/unresolved`. It never overcalls.

A weak panel signal would normally abstain, but a single **sharply lineage-specific marker**
rescues the call — the way a scientist names a lineage from one canonical marker (`myod1` →
muscle) and ignores the rest. A matched marker whose inverse panel-frequency over ZFIN
expression grounds it under at most 3 of the 31 lineages survives the weak-signal veto, and the
cluster is named by descending from that marker's panel anchor (contained to the abstain branch;
the descent and overcall audit are unchanged).

On an abstention, `Label` still exposes the **forcing evidence** so a caller can decide whether to
force a call itself: `candidates` (the near-tie buckets, best-first, with margins), `margin` (the
raw lead over the runner-up), and `ood` — `in_set` (reachable, force-able), `structural` (converges
nowhere, a blind-spot), `doublet` (contradictory germ layers), or `no_signal` (no identity hit).
`structural`/`doublet` are high-precision when they fire; `in_set` is a soft signal (a broad
attractor can mask a blind-spot).

## Additional Information

Additional documentation can be found in [`docs/reference/`](../../docs/reference/).
