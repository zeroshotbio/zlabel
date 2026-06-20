"""Build the committed Daniocell broad-tissue benchmark CSV.

Derives benchmarks/daniocell_eval.csv from the public Daniocell release (Sur et al. 2023,
Dev Cell; GEO GSE223922): per-cluster (clust) marker genes computed from the counts matrix,
each cluster's parent tissue as the gold broad label, the detailed tissue.name as metadata,
and a representative developmental stage.

The heavy source objects (the ~2.5 GB counts matrix, the metadata TSV) are read locally and
NEVER committed. This script NEVER downloads by default: missing inputs raise a clear error;
pass --download with --cache-dir DIR to fetch them once (cached). scanpy/anndata/scipy are
imported lazily behind the optional [eval] extra, so importing this module needs only the
core deps.

Marker defaults (also recorded in benchmarks/README.md): group by clust, scanpy
rank_genes_groups (default method t-test -- scanpy's own default and far faster than wilcoxon at
this scale; near-identical top-N for feeding a labeler; edit MARKER_METHOD for a rigorous run),
positive (logfoldchange > 0), non-technical (mitochondrial/ribosomal genes dropped) markers only,
rank-ordered, top N = 25. Representative stage: the modal stage.integer per cluster, the median of
all the cluster's stages on a modal tie.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import statistics
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Daniocell GEO GSE223922 supplementary files.
_GEO_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE223nnn/GSE223922/suppl/"
FILES = {
    "counts": "GSE223922_Sur2023_counts.mtx.gz",
    "genes": "GSE223922_Sur2023_counts_rows_genes.txt.gz",
    "cells": "GSE223922_Sur2023_counts_cols_cells.txt.gz",
    "metadata": "GSE223922_Sur2023_metadata.tsv.gz",
}

# t-test is scanpy's default and far faster than wilcoxon at this scale (489k cells x 522
# clusters); for feeding top-N markers to the labeler the two give near-identical gene lists.
# Set "wilcoxon" for a rigorous (much slower) run -- it, like the t-test family, emits the
# logfoldchanges that top_positive_markers needs; "logreg" does not and would KeyError below.
MARKER_METHOD = "t-test"
TOP_N = 25
GROUPBY = "clust"
_COLUMNS = ["cluster_id", "markers", "broad_tissue", "tissue_name", "stage_hpf"]


def representative_stage(stages: list[int]) -> float:
    """Return a cluster's representative stage: the modal stage.integer, median on a tie.

    Args:
        stages (list[int]): The stage.integer of every cell in the cluster.

    Returns:
        float: The most frequent stage; the median of all stages when several tie for most
        frequent. 0.0 for an empty cluster (never expected).
    """
    if not stages:
        return 0.0
    counts = Counter(stages)
    top = max(counts.values())
    modes = sorted(s for s, c in counts.items() if c == top)
    return float(modes[0]) if len(modes) == 1 else float(statistics.median(stages))


def _is_technical(gene: str) -> bool:
    """Whether a gene is a technical (mitochondrial or ribosomal) marker, not cell identity."""
    g = gene.lower()
    return g.startswith("mt-") or g.startswith(("rps", "rpl", "mrps", "mrpl"))


def top_positive_markers(ranked: list[tuple[str, float]], n: int = TOP_N) -> list[str]:
    """Keep the first n score-ranked, up-regulated, non-technical genes.

    Drops mitochondrial and ribosomal genes (a QC/technical signal, not cell identity) so the
    benchmark feeds the labeler identity markers -- standard marker-selection practice, and
    without it technical-dominated clusters look falsely unlabelable.

    Args:
        ranked (list[tuple[str, float]]): (gene, log_fold_change) pairs, already ordered by
            differential-expression score (most significant first).
        n (int): How many markers to keep.

    Returns:
        list[str]: The top n up-regulated, non-technical marker symbols, in rank order.
    """
    return [gene for gene, logfc in ranked if logfc > 0 and not _is_technical(gene)][:n]


def _modal(values: list[str]) -> str:
    """Return the most common string in values (smallest on ties), or '' when empty."""
    if not values:
        return ""
    counts = Counter(values)
    top = max(counts.values())
    return sorted(v for v, c in counts.items() if c == top)[0]


def assemble_rows(
    markers: dict[str, list[str]],
    per_cluster: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Assemble the benchmark CSV rows from per-cluster markers and metadata.

    Args:
        markers (dict[str, list[str]]): clust -> rank-ordered marker symbols.
        per_cluster (dict[str, dict[str, Any]]): clust -> {tissue, tissue_name, stage_hpf}.

    Returns:
        list[dict[str, str]]: One row dict per cluster (sorted by cluster_id for stability),
        with the benchmark schema columns.
    """
    rows: list[dict[str, str]] = []
    for clust in sorted(markers):
        meta = per_cluster[clust]
        rows.append(
            {
                "cluster_id": clust,
                "markers": ";".join(markers[clust]),
                "broad_tissue": str(meta["tissue"]),
                "tissue_name": str(meta["tissue_name"]),
                "stage_hpf": f"{meta['stage_hpf']:g}",
            }
        )
    return rows


def read_metadata(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Read the per-cell Daniocell metadata TSV (gzip) in one pass.

    Args:
        path (Path): Path to GSE223922_Sur2023_metadata.tsv.gz.

    Returns:
        tuple[dict[str, dict[str, Any]], dict[str, str]]: the per-cluster summary
        (clust -> {tissue, tissue_name, stage_hpf}, using each cluster's modal tissue /
        tissue.name and representative_stage) and the per-cell cell -> clust map.
    """
    tissues: dict[str, list[str]] = defaultdict(list)
    names: dict[str, list[str]] = defaultdict(list)
    stages: dict[str, list[int]] = defaultdict(list)
    cell_to_clust: dict[str, str] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for r in csv.DictReader(handle, delimiter="\t"):
            clust = r["clust"]
            cell_to_clust[r["cell"]] = clust
            tissues[clust].append(r["tissue"])
            names[clust].append(r.get("tissue.name", ""))
            stages[clust].append(int(float(r["stage.integer"])))
    per_cluster = {
        clust: {
            "tissue": _modal(tissues[clust]),
            "tissue_name": _modal(names[clust]),
            "stage_hpf": representative_stage(stages[clust]),
        }
        for clust in tissues
    }
    return per_cluster, cell_to_clust


def compute_markers(counts: Path, genes: Path, cells: Path, cell_to_clust: dict[str, str]) -> dict[str, list[str]]:
    """Compute per-cluster markers from the counts matrix (lazily uses scanpy/anndata/scipy).

    Reads the genes x cells MTX, builds a cells x genes AnnData, attaches each cell's clust,
    normalizes and log-transforms, runs rank_genes_groups, and keeps the top up-regulated
    markers per cluster (see module defaults).

    Args:
        counts (Path): The MTX counts file (gzip).
        genes (Path): The row gene-names file (gzip).
        cells (Path): The column cell-barcodes file (gzip).
        cell_to_clust (dict[str, str]): Per-cell cluster assignment from read_metadata.

    Returns:
        dict[str, list[str]]: clust -> rank-ordered marker symbols.
    """
    # Lazy imports: the [eval] extra, builder-only. Importing this module needs only core deps.
    import anndata as ad
    import scanpy as sc
    from scipy.io import mmread
    from scipy.sparse import csr_matrix

    gene_names = read_lines(genes)
    cell_names = read_lines(cells)
    sys.stderr.write(f"loading counts matrix ({counts.name}) ...\n")
    # mmread yields a genes x cells COO matrix; .T is a cheap axis swap, then a single CSR copy
    # gives the cells x genes layout AnnData wants (one fewer full sparse copy than csr-then-T).
    with gzip.open(counts, "rb") as handle:
        matrix = csr_matrix(mmread(handle).T)
    adata = ad.AnnData(matrix)  # cells x genes
    adata.var_names = gene_names
    adata.obs_names = cell_names
    adata.obs[GROUPBY] = [cell_to_clust.get(c, "") for c in cell_names]
    adata = adata[adata.obs[GROUPBY] != ""].copy()
    sys.stderr.write(f"computing markers ({MARKER_METHOD}) over {adata.n_obs} cells x {adata.n_vars} genes\n")

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.tl.rank_genes_groups(adata, groupby=GROUPBY, method=MARKER_METHOD)
    result = adata.uns["rank_genes_groups"]
    out: dict[str, list[str]] = {}
    for group in result["names"].dtype.names:
        ranked = list(zip(result["names"][group], result["logfoldchanges"][group], strict=True))
        out[group] = top_positive_markers(ranked, TOP_N)
    return out


def read_lines(path: Path) -> list[str]:
    """Read a gzip text file into a list of stripped lines."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [line.strip() for line in handle]


def _resolve_inputs(cache_dir: Path, explicit: dict[str, str | None], download: bool) -> dict[str, Path]:
    """Resolve the four input paths; fetch only when --download is set, never by default.

    Args:
        cache_dir (Path): Directory holding (or to hold) the Daniocell files.
        explicit (dict[str, str | None]): Optional explicit path overrides per key.
        download (bool): Whether a one-time fetch into cache_dir is permitted.

    Returns:
        dict[str, Path]: key -> resolved path.

    Raises:
        SystemExit: When inputs are missing and download is False (fail closed).
    """
    paths: dict[str, Path] = {}
    for key in FILES:
        override = explicit.get(key)
        paths[key] = Path(override) if override else cache_dir / FILES[key]
    missing = [key for key, path in paths.items() if not path.exists()]
    if missing and not download:
        raise SystemExit(
            f"missing Daniocell inputs {missing} under {cache_dir}. This builder never downloads "
            f"by default; pass --download --cache-dir DIR to fetch them once, or give explicit paths."
        )
    if missing:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for key in missing:
            url = _GEO_BASE + FILES[key]
            sys.stderr.write(f"downloading {url} -> {paths[key]}\n")
            urllib.request.urlretrieve(url, paths[key])
    return paths


def main(argv: list[str] | None = None) -> int:
    """Build the benchmark CSV from the Daniocell release.

    Args:
        argv (list[str] | None): Argument vector (defaults to sys.argv[1:]).

    Returns:
        int: 0 on success.
    """
    parser = argparse.ArgumentParser(description="Build the Daniocell broad-tissue benchmark CSV.")
    parser.add_argument("--cache-dir", default="data/daniocell", help="dir holding the GEO files")
    parser.add_argument("--download", action="store_true", help="fetch missing GEO files once (opt-in)")
    parser.add_argument("--out", default="benchmarks/daniocell_eval.csv")
    for key in FILES:
        parser.add_argument(f"--{key}", default=None, help=f"explicit path to the {key} file")
    args = parser.parse_args(argv)

    explicit = {key: getattr(args, key) for key in FILES}
    paths = _resolve_inputs(Path(args.cache_dir), explicit, args.download)

    per_cluster, cell_to_clust = read_metadata(paths["metadata"])
    sys.stderr.write(f"metadata: {len(per_cluster)} clusters, {len(cell_to_clust)} cells\n")
    markers = compute_markers(paths["counts"], paths["genes"], paths["cells"], cell_to_clust)
    rows = assemble_rows(markers, per_cluster)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    sys.stderr.write(f"wrote {len(rows)} clusters -> {out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
