"""Build the committed Daniocell UMAP overview asset (benchmarks/daniocell_umap.json).

A 2-D map of the benchmark for the zlabel-scope companion's cluster-overview: one centroid per
published cluster (clust) over a faint downsampled cell cloud, so the 522 clusters can be seen at a
glance and clicked through to their trace. This is a VIEW of the benchmark substrate -- it never feeds
the labeler and zlabel itself never reads it.

Derived from the same public Daniocell release the eval CSV uses (Sur et al. 2023, GEO GSE223922).
read_metadata is reused from build_daniocell_eval so the cluster keys match benchmarks/daniocell_eval.csv
exactly. The embedding is a standard scanpy pipeline (normalize -> log1p -> HVG -> PCA -> neighbours ->
UMAP) on a stratified cell subsample (at most MAX_PER_CLUSTER cells per cluster) -- enough for a stable
centroid per cluster and a representative cloud, while keeping the run tractable. Reported n_cells is the
TRUE cluster size from the full metadata, not the subsample.

The heavy source objects (the ~2.5 GB counts matrix, the metadata TSV) are read locally and NEVER
committed; scanpy/anndata/scipy/numpy are imported lazily behind the optional [eval] extra. Run once:
  uv run --extra eval python scripts/build_daniocell_umap.py
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from build_daniocell_eval import _FILES, read_metadata

SEED = 0
MAX_PER_CLUSTER = 150  # stratified subsample cap; a smaller cluster keeps all its cells
CLOUD_POINTS = 12000  # downsampled background cloud size
N_HVG = 2000
N_PCS = 50
_COORD_DP = 3  # round coords to keep the committed JSON small


def _read_lines(path: Path) -> list[str]:
    """Read a gzip text file into a list of stripped lines."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [line.strip() for line in handle]


def _resolve(cache_dir: Path) -> dict[str, Path]:
    """Resolve the four Daniocell input files under cache_dir; fail closed if any is missing.

    Args:
        cache_dir (Path): Directory holding the GEO files (the eval builder's default location).

    Returns:
        dict[str, Path]: key -> resolved path.

    Raises:
        SystemExit: When an input is missing (this builder never downloads; the eval builder's
            --download fetches them once).
    """
    paths = {key: cache_dir / name for key, name in _FILES.items()}
    missing = [key for key, path in paths.items() if not path.exists()]
    if missing:
        raise SystemExit(
            f"missing Daniocell inputs {missing} under {cache_dir}. Fetch them once with "
            f"`python scripts/build_daniocell_eval.py --download --cache-dir {cache_dir}`."
        )
    return paths


def load_counts(counts: Path, genes: Path, cells: Path, cell_to_clust: dict[str, str]) -> Any:
    """Load the genes x cells MTX into a cells x genes AnnData, keeping only clustered cells.

    Mirrors the eval builder's load: mmread yields a genes x cells COO, transposed and copied once
    into the cells x genes CSR layout AnnData wants. Each cell's clust is attached as an obs column.

    Args:
        counts (Path): The MTX counts file (gzip).
        genes (Path): The row gene-names file (gzip).
        cells (Path): The column cell-barcodes file (gzip).
        cell_to_clust (dict[str, str]): Per-cell cluster assignment from read_metadata.

    Returns:
        AnnData: Cells x genes, restricted to cells with a clust, carrying obs["clust"].
    """
    import anndata as ad
    from scipy.io import mmread
    from scipy.sparse import csr_matrix

    gene_names = _read_lines(genes)
    cell_names = _read_lines(cells)
    sys.stderr.write(f"loading counts matrix ({counts.name}) ...\n")
    with gzip.open(counts, "rb") as handle:
        matrix = csr_matrix(mmread(handle).T)
    adata = ad.AnnData(matrix)
    adata.var_names = gene_names
    adata.obs_names = cell_names
    adata.obs["clust"] = [cell_to_clust.get(c, "") for c in cell_names]
    return adata[adata.obs["clust"] != ""].copy()


def subsample(adata: Any, max_per_cluster: int, seed: int) -> Any:
    """Stratified subsample: at most max_per_cluster cells per cluster (all of a smaller one), seeded.

    Keeps every cluster represented (so all 522 get a centroid) while bounding the embedding cost,
    instead of a uniform subsample that would starve small clusters.

    Args:
        adata (AnnData): Cells x genes with obs["clust"].
        max_per_cluster (int): Per-cluster cell cap.
        seed (int): RNG seed for reproducible selection.

    Returns:
        AnnData: The subsampled view (a copy).
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    obs = adata.obs["clust"].to_numpy()
    keep: list[Any] = []
    for clust in np.unique(obs):
        idx = np.flatnonzero(obs == clust)
        if idx.size > max_per_cluster:
            idx = rng.choice(idx, max_per_cluster, replace=False)
        keep.append(idx)
    selected = np.sort(np.concatenate(keep))
    return adata[selected].copy()


def embed(adata: Any, seed: int) -> Any:
    """Standard scanpy embedding to 2-D UMAP coordinates (writes obsm["X_umap"]).

    normalize_total -> log1p -> highly_variable_genes -> scale -> PCA -> neighbours -> UMAP, all
    seeded. The exact layout is not load-bearing: it only needs to separate cell types enough that
    each cluster's centroid lands in a sensible place for the overview.

    Args:
        adata (AnnData): The (subsampled) cells x genes counts.
        seed (int): Random state for PCA / neighbours / UMAP.

    Returns:
        AnnData: The embedded data, restricted to the highly variable genes, with obsm["X_umap"].
    """
    import scanpy as sc

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata, n_top_genes=N_HVG)
    adata = adata[:, adata.var.highly_variable].copy()
    sc.pp.scale(adata, max_value=10)
    sc.tl.pca(adata, n_comps=N_PCS, random_state=seed)
    sc.pp.neighbors(adata, n_pcs=N_PCS, random_state=seed)
    sc.tl.umap(adata, random_state=seed)
    return adata


def assemble_asset(adata: Any, cell_to_clust: dict[str, str], seed: int) -> dict[str, Any]:
    """Project the embedded subsample into the committed overview asset.

    Args:
        adata (AnnData): Embedded data with obsm["X_umap"] and obs["clust"].
        cell_to_clust (dict[str, str]): The full per-cell map (for TRUE cluster sizes).
        seed (int): RNG seed for the cloud downsample.

    Returns:
        dict[str, Any]: clusters (id, x, y, n_cells), a downsampled cloud ([x, y, clust]), the
        coordinate bounds, and a provenance header.
    """
    import numpy as np

    xy = np.asarray(adata.obsm["X_umap"], dtype=float)
    clust = adata.obs["clust"].to_numpy()
    true_counts = Counter(cell_to_clust.values())

    clusters = []
    for cid in sorted(np.unique(clust)):
        centroid = xy[clust == cid].mean(axis=0)
        clusters.append(
            {
                "cluster_id": str(cid),
                "x": round(float(centroid[0]), _COORD_DP),
                "y": round(float(centroid[1]), _COORD_DP),
                "n_cells": int(true_counts[cid]),
            }
        )

    rng = np.random.default_rng(seed)
    n = xy.shape[0]
    sel = np.sort(rng.choice(n, CLOUD_POINTS, replace=False)) if n > CLOUD_POINTS else np.arange(n)
    cloud = [[round(float(xy[i, 0]), _COORD_DP), round(float(xy[i, 1]), _COORD_DP), str(clust[i])] for i in sel]

    return {
        "provenance": {
            "source": "Daniocell (Sur et al. 2023, GEO GSE223922); de-novo scanpy UMAP on a stratified subsample",
            "n_cells_total": len(cell_to_clust),
            "n_cells_embedded": int(n),
            "n_clusters": len(clusters),
            "max_per_cluster": MAX_PER_CLUSTER,
            "n_hvg": N_HVG,
            "n_pcs": N_PCS,
            "seed": seed,
        },
        "bounds": {
            "xmin": round(float(xy[:, 0].min()), _COORD_DP),
            "xmax": round(float(xy[:, 0].max()), _COORD_DP),
            "ymin": round(float(xy[:, 1].min()), _COORD_DP),
            "ymax": round(float(xy[:, 1].max()), _COORD_DP),
        },
        "clusters": clusters,
        "cloud": cloud,
    }


def main(argv: list[str] | None = None) -> int:
    """Build the Daniocell UMAP overview asset from the local Daniocell release.

    Args:
        argv (list[str] | None): Argument vector (defaults to sys.argv[1:]).

    Returns:
        int: 0 on success.
    """
    parser = argparse.ArgumentParser(description="Build the Daniocell UMAP overview asset (JSON).")
    parser.add_argument("--cache-dir", default="data/daniocell", help="dir holding the GEO files")
    parser.add_argument("--out", default="benchmarks/daniocell_umap.json")
    parser.add_argument("--max-per-cluster", type=int, default=MAX_PER_CLUSTER)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    paths = _resolve(Path(args.cache_dir))
    _, cell_to_clust = read_metadata(paths["metadata"])
    sys.stderr.write(f"metadata: {len(set(cell_to_clust.values()))} clusters, {len(cell_to_clust)} cells\n")

    adata = load_counts(paths["counts"], paths["genes"], paths["cells"], cell_to_clust)
    adata = subsample(adata, args.max_per_cluster, args.seed)
    sys.stderr.write(f"embedding {adata.n_obs} cells x {adata.n_vars} genes ...\n")
    adata = embed(adata, args.seed)
    asset = assemble_asset(adata, cell_to_clust, args.seed)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asset, separators=(",", ":")), encoding="utf-8")
    prov = asset["provenance"]
    sys.stderr.write(
        f"wrote {prov['n_clusters']} clusters + {len(asset['cloud'])} cloud points "
        f"({prov['n_cells_embedded']} embedded) -> {out}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
