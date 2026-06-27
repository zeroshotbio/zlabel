"""Build a ZSCAPE eval set for the held-out 2nd-atlas generalization check (E3).

ZSCAPE (Saunders 2023, GSE202639-derived h5ad) is a whole-embryo perturbation atlas. To keep the
generalization test about wild-type identity (not perturbation-shifted markers) we use ONLY the
wild-type control cells (gene_target prefixed "ctrl"). Each ZSCAPE cell_type_broad annotation is
treated as a cluster; its markers come from a one-vs-rest rank_genes_groups, harmonized from the
atlas's ENSDARG gene ids to current ZFIN symbols (the engine's vocabulary). The output is the same
schema as the Daniocell benchmark, scored later by evaluate.py at the COMMITTED default thresholds
against benchmarks/zscape_tissue_crosswalk.yaml — never tuned on.

This reuses the atlas-agnostic marker core from build_daniocell_eval.py (top_positive_markers,
representative_stage, _modal, assemble_rows); only the source (h5ad), the column names, and the
ENSDARG->symbol harmonization differ. The scanpy/IO path is a one-off and not unit-tested, matching
the Daniocell builder.

Run (needs the [eval] extra + data/ontologies/zfin_ensembl_1_to_1.txt):
    uv run python scripts/build_zscape_eval.py --h5ad <path> --out benchmarks/zscape_eval.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import build_daniocell_eval as build_eval

from zlabel.data import load_ensdarg_to_symbol

REPO = Path(__file__).resolve().parent.parent
ENS_PATH = REPO / "data" / "ontologies" / "zfin_ensembl_1_to_1.txt"
DEFAULT_H5AD = "/home/ec2-user/PycharmProjects/transcriptformer/datasets/zscape_perturb_panel4866.h5ad"
DEFAULT_OUT = REPO / "benchmarks" / "zscape_eval.csv"

GROUPBY = "cell_type_broad"  # ZSCAPE's per-cell annotation -> the benchmark "clusters"
TISSUE_COL = "tissue"  # the broad gold axis (33 categories), crosswalked to ZFA
STAGE_COL = "timepoint"  # hpf
GENE_TARGET_COL = "gene_target"
CONTROL_PREFIX = "ctrl"  # wild-type injection controls (ctrl-inj, ctrl-noto, ...)
MIN_CELLS = 50  # a cell_type_broad group with fewer control cells gives unreliable markers; skip it


def _sanitize(name: str) -> str:
    """A filesystem/CSV-safe cluster id from a free-text cell-type name."""
    return re.sub(r"[^0-9a-z]+", "_", name.strip().lower()).strip("_")


def _write_csv(rows: list[dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=build_eval._COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build(h5ad_path: str, out_path: Path) -> int:
    """Build the ZSCAPE eval CSV from the h5ad. Returns the number of clusters written."""
    import anndata as ad
    import scanpy as sc

    ens_map = load_ensdarg_to_symbol(ENS_PATH)

    sys.stderr.write(f"loading {h5ad_path} (backed) ...\n")
    backed = ad.read_h5ad(h5ad_path, backed="r")
    gene_target = backed.obs[GENE_TARGET_COL].astype(str)
    ctrl_mask = gene_target.str.startswith(CONTROL_PREFIX).to_numpy()
    sys.stderr.write(f"wild-type controls: {int(ctrl_mask.sum())} of {backed.n_obs} cells\n")
    adata = backed[ctrl_mask].to_memory()

    # Harmonize genes: ENSDARG (var['id']) -> current ZFIN symbol; drop unmapped, dedupe.
    symbols = [ens_map.get(str(gene_id), "") for gene_id in adata.var["id"]]
    mapped = [bool(symbol) for symbol in symbols]
    sys.stderr.write(f"genes mapped ENSDARG->ZFIN symbol: {sum(mapped)} of {adata.n_vars}\n")
    adata.var["symbol"] = symbols
    adata = adata[:, mapped].copy()
    adata.var_names = adata.var["symbol"].astype(str).to_numpy()
    adata.var_names_make_unique()

    # Drop sparse cell_type_broad groups (unreliable one-vs-rest markers).
    group_sizes = adata.obs[GROUPBY].astype(str).value_counts()
    keep = set(group_sizes[group_sizes >= MIN_CELLS].index)
    sys.stderr.write(f"cell_type_broad groups with >= {MIN_CELLS} control cells: {len(keep)} of {len(group_sizes)}\n")
    group_str = adata.obs[GROUPBY].astype(str)
    adata = adata[group_str.isin(keep)].copy()
    adata.obs[GROUPBY] = adata.obs[GROUPBY].astype(str).astype("category")

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sys.stderr.write(f"rank_genes_groups ({build_eval.MARKER_METHOD}) over {adata.n_obs} cells, {adata.n_vars} genes\n")
    sc.tl.rank_genes_groups(adata, groupby=GROUPBY, method=build_eval.MARKER_METHOD)
    result = adata.uns["rank_genes_groups"]

    markers: dict[str, list[str]] = {}
    per_cluster: dict[str, dict[str, object]] = {}
    obs = adata.obs
    for group in result["names"].dtype.names:
        ranked = list(zip(result["names"][group], result["logfoldchanges"][group], strict=True))
        top = build_eval.top_positive_markers(ranked, build_eval.TOP_N)
        if not top:
            continue
        cluster_id = _sanitize(group)
        rows_in_group = obs[obs[GROUPBY].astype(str) == group]
        markers[cluster_id] = top
        per_cluster[cluster_id] = {
            "tissue": build_eval._modal([str(t) for t in rows_in_group[TISSUE_COL]]),
            "tissue_name": group,
            "stage_hpf": build_eval.representative_stage([int(s) for s in rows_in_group[STAGE_COL]]),
        }

    rows = build_eval.assemble_rows(markers, per_cluster)
    _write_csv(rows, out_path)
    sys.stderr.write(f"wrote {len(rows)} clusters to {out_path}\n")
    return len(rows)


def main() -> int:
    """Parse args and build the ZSCAPE eval CSV from the h5ad. Returns 0."""
    parser = argparse.ArgumentParser(description="Build the ZSCAPE 2nd-atlas eval set (wild-type controls).")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD, help="ZSCAPE h5ad path")
    parser.add_argument("--out", default=str(DEFAULT_OUT), type=Path, help="output CSV path")
    args = parser.parse_args()
    build(args.h5ad, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
