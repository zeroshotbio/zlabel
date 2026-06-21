# Daniocell evaluation benchmark

The Phase 4b measurement substrate for zlabel: one row per Daniocell fine cluster, scored for
broad-tissue agreement against the current engine. Built reproducibly from the public Daniocell
release; only the small derived CSV and the crosswalk are committed here (the ~2.5 GB source
objects are not).

## Files

- `daniocell_eval.csv` — the benchmark. Columns:
  - `cluster_id` — Daniocell `clust` (fine subcluster, e.g. `musc.3`).
  - `markers` — top-25 up-regulated markers, `;`-joined, rank-ordered.
  - `broad_tissue` — the cluster's parent Daniocell `tissue` code (the gold broad label).
  - `tissue_name` — the detailed `tissue.name` (metadata; not scored in 4b).
  - `stage_hpf` — representative developmental stage (see Parameters).
- `daniocell_tissue_crosswalk.yaml` — the gold-side, fail-closed `{tissue -> broad ZFA
  anchor(s)}` scoring map, reviewed like code. Audited by `scripts/audit_crosswalk.py`
  (`make audit`): every structure a tissue's comment names must ground under that tissue's
  anchor (members are listed before `--`; glosses and composition notes after).
- `daniocell_baseline_report.md` — the generated baseline report (regenerate; do not hand-edit).
- `daniocell_umap.json` — a 2-D UMAP overview asset for the zlabel-scope companion: one centroid
  (x, y) + true cell count per cluster, plus a downsampled cell cloud. A VIEW of the substrate for
  the cluster-overview map; it never feeds the labeler and is not used in scoring. See Rebuild.
  Shape (coordinates rounded to 3 dp):
    - `provenance` — `{source, n_cells_total, n_cells_embedded, n_clusters, max_per_cluster, n_hvg, n_pcs, seed}`.
    - `bounds` — `{xmin, xmax, ymin, ymax}`: the coordinate extent of the embedded cells.
    - `clusters` — `[{cluster_id, x, y, n_cells}, ...]`: one centroid per `clust` (n_cells is the true size).
    - `cloud` — `[[x, y, cluster_id], ...]`: positional triples (not keyed) for the faint background cells.

## Source

Daniocell: Sur, Wang, Capar, Margolin, Prochaska, Farrell (2023), "Single-cell analysis of
shared signatures and transcriptional diversity during zebrafish development," Developmental
Cell 58(24). Data: GEO GSE223922 (counts MTX + per-cell metadata TSV; Python-readable, no R).

## Rebuild

The builder NEVER downloads by default. Provide local paths, or opt in to a one-time cached fetch:

```bash
uv sync --extra eval   # scanpy + anndata (builder only)
uv run python scripts/build_daniocell_eval.py --download --cache-dir data/daniocell
uv run python -m zlabel.evaluate benchmarks/daniocell_eval.csv
uv run --extra eval python scripts/build_daniocell_umap.py   # the companion's UMAP overview asset
```

The UMAP asset is a stratified-subsample embedding (at most 150 cells per cluster) for stable
centroids at tractable cost; reported `n_cells` is the true cluster size. It is panel-independent —
the companion re-colors it from the current outcomes on restart, so it needs rebuilding only if the
Daniocell source changes, not when panels or the engine change.

## Parameters (deterministic)

- Benchmark unit: fine `clust`; broad agreement scored against the parent `tissue`.
- Markers: scanpy `rank_genes_groups` (default `method="t-test"` — scanpy's default, far faster
  than wilcoxon at this scale and near-identical top-N for labeling; `MARKER_METHOD="wilcoxon"`
  for rigor), positive (logfoldchange > 0) and non-technical (mitochondrial/ribosomal genes
  dropped) only, rank-ordered, top N = 25, after `normalize_total(target_sum=1e4)` + `log1p`.
- Representative stage: the modal `stage.integer` per cluster; the median of the cluster's
  stages on a modal tie.

## Scoring (how evaluate.py uses these files)

A prediction agrees when its ZFA id grounds (is at or under) any of the gold tissue's ZFA
anchors — pure ZFA ancestry via `ground.grounds_under`. Named calls score by the voted term;
fallback calls are enriched eval-side from the full panel anchor (`Label.zfa_id` keeps only one
of a multi-anchor panel's ids). Rollups and abstentions carry no ZFA handle and sit in the
coverage/split columns, out of the agreement count.

## Recorded limitations

- No fine-depth truth. Daniocell gives broad `tissue` labels, so within-bucket
  over-specification (e.g. muscle to a specific muscle subtype) is measured by the structural
  parent-child overcall audit, not validated against truth. Finer-reference depth validation is deferred to a future calibration pass.
- Fallback anchor truncation. For the 6 panels with two ontology anchors, `Label.zfa_id` keeps
  only `sorted(anchor)[0]`; the evaluator recovers the full anchor from `panel_bucket` for
  scoring, but the Label object itself still carries a single id.
- not_scored tissues. Categories with no clean ZFA anchor (e.g. `blas` blastomeres) are excluded
  from agreement; the crosswalk fails closed on any unmapped tissue.
- One-directional crosswalk audit. `scripts/audit_crosswalk.py` checks that each tissue's named
  members ground under its anchor (catching a too-tight anchor that silently mis-scores a real call
  as a disagreement), but not that the anchor grounds only members (a too-loose anchor that lets
  non-member calls count — the more flattering error). A reverse check is future work.
