"""Build a single-stage Daniocell h5ad for `zspine ingest` (zlabel-scope studio dataset).

The studio shows one recursive cluster tree per dataset; zspine re-clusters de novo from a flat
h5ad, so this only needs: raw integer counts in ``layers["counts"]``, a precomputed 2-D UMAP in
``obsm["X_umap"]``, ZFIN-compatible gene symbols (the Daniocell release var names already are), and a
tissue reference obs column. We subset to ONE well-populated stage (default 48 hpf) and cap the cell
count so the embedding + ingest stay fast and the studio tree stays legible — exactly the minifin recipe.

Reuses the committed Daniocell loaders/embedder:
  scripts/build_daniocell_umap.py :: load_counts() (MTX -> cells x genes raw counts)
                                      embed()       (normalize->log1p->HVG->PCA->neighbours->UMAP)

Heavy source files (the ~2.5 GB MTX) are read locally and never committed.

Example:
    uv run --extra eval python scripts/build_daniocell_h5ad.py \
        --stage 48 --cap 30000 --out /tmp/daniocell-48hpf.h5ad
"""

from __future__ import annotations

import argparse
import csv
import gzip
import sys
from pathlib import Path
from typing import Any

# Reuse the committed loaders/embedder (same dir on sys.path when run as a script).
from build_daniocell_umap import embed, load_counts

_DATA = Path(__file__).resolve().parent.parent / "data" / "daniocell"
_COUNTS = _DATA / "GSE223922_Sur2023_counts.mtx.gz"
_GENES = _DATA / "GSE223922_Sur2023_counts_rows_genes.txt.gz"
_CELLS = _DATA / "GSE223922_Sur2023_counts_cols_cells.txt.gz"
_META = _DATA / "GSE223922_Sur2023_metadata.tsv.gz"


def read_cell_meta(path: Path) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Per-cell metadata from the Daniocell TSV.

    Returns:
        (cell -> clust, cell -> {stage, tissue, tissue_name}) for cells that carry a clust.
    """
    cell_clust: dict[str, str] = {}
    cell_meta: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            clust = row.get("clust", "")
            if not clust:
                continue
            cell = row["cell"]
            cell_clust[cell] = clust
            cell_meta[cell] = {
                "stage": int(float(row["stage.integer"])),
                "tissue": row.get("tissue", ""),
                "tissue_name": row.get("tissue.name", ""),
            }
    return cell_clust, cell_meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a single-stage Daniocell h5ad for zspine.")
    parser.add_argument("--stage", type=int, default=48, help="stage.integer to keep (hpf)")
    parser.add_argument("--cap", type=int, default=30000, help="max cells (random downsample, seeded)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", required=True, help="output .h5ad path")
    args = parser.parse_args(argv)

    import numpy as np
    import pandas as pd

    for required in (_COUNTS, _GENES, _CELLS, _META):
        if not required.exists():
            parser.error(f"missing Daniocell input: {required}")

    cell_clust, cell_meta = read_cell_meta(_META)
    sys.stderr.write(f"metadata: {len(cell_clust)} clustered cells\n")

    adata = load_counts(_COUNTS, _GENES, _CELLS, cell_clust)  # cells x genes, raw counts, obs["clust"]
    names = adata.obs_names.to_list()
    adata.obs["stage"] = [cell_meta[c]["stage"] for c in names]
    adata.obs["tissue"] = [cell_meta[c]["tissue"] for c in names]
    adata.obs["tissue_name"] = [cell_meta[c]["tissue_name"] for c in names]

    adata = adata[adata.obs["stage"] == args.stage].copy()
    sys.stderr.write(f"stage {args.stage}: {adata.n_obs} cells\n")
    if adata.n_obs == 0:
        parser.error(f"no cells at stage {args.stage}")

    if adata.n_obs > args.cap:
        rng = np.random.default_rng(args.seed)
        keep = np.sort(rng.choice(adata.n_obs, args.cap, replace=False))
        adata = adata[keep].copy()
        sys.stderr.write(f"downsampled to {adata.n_obs} cells\n")

    # Preserve raw integer counts BEFORE the embed copy normalizes anything.
    adata.layers["counts"] = adata.X.copy()

    # 2-D UMAP via the committed embedder (HVG-restricted copy); lift coords back onto all genes.
    embedded = embed(adata.copy(), args.seed)
    xy = pd.DataFrame(np.asarray(embedded.obsm["X_umap"]), index=embedded.obs_names)
    adata.obsm["X_umap"] = xy.loc[adata.obs_names].to_numpy()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    adata.write_h5ad(out)
    sys.stderr.write(
        f"wrote {out}  ({adata.n_obs} cells x {adata.n_vars} genes; "
        f"layers={list(adata.layers)}; obsm={list(adata.obsm)})\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
