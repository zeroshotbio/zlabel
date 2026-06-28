"""Build a Zebrahub eval set for the held-out 3rd-atlas generalization check.

Zebrahub (Lange et al., Cell 2024; CZ Biohub) is an independent, wild-type single-embryo
time-course atlas -- a different lab and design from Daniocell and ZSCAPE. The locally available
file is the scANVI REFERENCE, annotated at only 10 broad classes on a developmental-domain axis
(paraxial/lateral/intermediate mesoderm, neural_crest, endoderm, central_nervous_system,
mesenchyme, hematopoietic_system, notochord, periderm), each with a native ZFA id. So this is a
COARSE, germ-layer-level cross-lab sanity wall -- not a fine cell-type eval.

Each cell_type class is treated as a cluster; its markers come from a one-vs-rest
rank_genes_groups over normalized+log1p counts. The atlas already names genes by current-ish ZFIN
symbols (var_names), so markers are taken from var_names directly and normalized downstream by the
engine (no ENSDARG harmonization needed, unlike the ZSCAPE builder). The output is the same schema
as the other benchmarks, scored later by evaluate.py at the COMMITTED defaults against
benchmarks/zebrahub_tissue_crosswalk.yaml -- never tuned on.

This reuses the atlas-agnostic marker core from build_daniocell_eval.py (top_positive_markers,
representative_stage, assemble_rows); only the source (h5ad), the grouping column, and the
hpf/dpf stage parsing differ. The scanpy/IO path is a one-off and not unit-tested, matching the
Daniocell and ZSCAPE builders.

Run (needs the [eval] extra):
    uv run --extra eval python scripts/build_zebrahub_eval.py --h5ad <path> --out benchmarks/zebrahub_eval.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import build_daniocell_eval as build_eval

REPO = Path(__file__).resolve().parent.parent
DEFAULT_H5AD = "/home/ec2-user/.cache/prism-celltype/zebrahub/zebrahub_reference.h5ad"
DEFAULT_OUT = REPO / "benchmarks" / "zebrahub_eval.csv"

GROUPBY = "cell_type"  # the 10 broad classes -> the benchmark "clusters" and the gold axis
STAGE_COL = "timepoint"  # e.g. "16hpf", "3dpf"
MIN_CELLS = 50  # a class with fewer cells gives unreliable one-vs-rest markers; skip it


def timepoint_to_hpf(value: str) -> int | None:
    """Convert a Zebrahub timepoint label to integer hpf, or None if unparseable.

    Args:
        value (str): A timepoint label such as 16hpf or 3dpf.

    Returns:
        int | None: Hours post fertilization (dpf multiplied by 24), or None when the label is
        not an integer count of hpf or dpf.
    """
    v = value.strip().lower()
    for suffix, factor in (("hpf", 1), ("dpf", 24)):
        if v.endswith(suffix):
            head = v[: -len(suffix)].strip()
            return int(head) * factor if head.isdigit() else None
    return None


def _write_csv(rows: list[dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=build_eval._COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build(h5ad_path: str, out_path: Path) -> int:
    """Build the Zebrahub eval CSV from the h5ad. Returns the number of clusters written."""
    import scanpy as sc

    sys.stderr.write(f"loading {h5ad_path} ...\n")
    adata = sc.read_h5ad(h5ad_path)

    # Drop sparse classes (none expected; the smallest class is ~1k cells).
    group_sizes = adata.obs[GROUPBY].astype(str).value_counts()
    keep = set(group_sizes[group_sizes >= MIN_CELLS].index)
    sys.stderr.write(f"classes with >= {MIN_CELLS} cells: {len(keep)} of {len(group_sizes)}\n")
    group_str = adata.obs[GROUPBY].astype(str)
    adata = adata[group_str.isin(keep)].copy()
    adata.obs[GROUPBY] = adata.obs[GROUPBY].astype(str).astype("category")

    # X is raw counts (integer-valued, variable library size) -> standard normalize + log1p.
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
        rows_in_group = obs[obs[GROUPBY].astype(str) == group]
        stages = [hpf for s in rows_in_group[STAGE_COL] if (hpf := timepoint_to_hpf(str(s))) is not None]
        markers[group] = top
        per_cluster[group] = {
            "tissue": group,  # the class is the gold axis; the crosswalk is keyed by the class name
            "tissue_name": group,
            "stage_hpf": build_eval.representative_stage(stages),
        }

    rows = build_eval.assemble_rows(markers, per_cluster)
    _write_csv(rows, out_path)
    sys.stderr.write(f"wrote {len(rows)} clusters to {out_path}\n")
    return len(rows)


def main() -> int:
    """Parse args and build the Zebrahub eval CSV from the h5ad. Returns 0."""
    parser = argparse.ArgumentParser(description="Build the Zebrahub 3rd-atlas eval set (coarse, 10 broad classes).")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD, help="Zebrahub reference h5ad path")
    parser.add_argument("--out", default=str(DEFAULT_OUT), type=Path, help="output CSV path")
    args = parser.parse_args()
    build(args.h5ad, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
