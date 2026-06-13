"""Shared test helpers — functions (not fixtures) used across test modules."""

from pathlib import Path


def expr_row(
    symbol: str,
    super_id: str,
    super_name: str,
    sub_id: str,
    sub_name: str,
    start: str,
    end: str,
) -> str:
    """Build one real-format ZFIN expression row (15 tab cols, no header).

    Matches the exact column layout of wildtype-expression_fish.txt used by
    data.load_zfin_expression. Pass empty strings for sub_id/sub_name when the
    record has no sub-structure annotation.
    """
    return "\t".join(
        [
            "ZDB-GENE-x",
            symbol,
            "WT",
            super_id,
            super_name,
            sub_id,
            sub_name,
            start,
            end,
            "ISH",
            "MMO:1",
            "ZDB-PUB",
            "",
            "",
            "ZDB-FISH",
        ]
    )


def write_expr(tmp_path: Path, rows: list[str]) -> Path:
    """Write ZFIN expression rows to a temp file and return the path."""
    path = tmp_path / "wt_expr.txt"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path
