"""Verify that every ontology_anchor ZFA id in panels.yaml exists in the real zfa.obo.

Run once before committing anchor changes:
    uv run python scripts/verify_anchors.py

Exits non-zero if any id is absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
PANELS_YAML = ROOT / "src" / "zlabel" / "panels.yaml"
ZFA_OBO = ROOT / "data" / "ontologies" / "zfa.obo"


def load_zfa_ids(obo_path: Path) -> dict[str, str]:
    """Return a mapping of ZFA id -> name from the obo file.

    Args:
        obo_path (Path): path to the zfa.obo file.

    Returns:
        dict[str, str]: {id: name}
    """
    ids: dict[str, str] = {}
    current_id: str | None = None
    current_name: str | None = None
    in_term = False
    for line in obo_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line == "[Term]":
            if in_term and current_id and current_name:
                ids[current_id] = current_name
            in_term = True
            current_id = None
            current_name = None
        elif line == "" and in_term:
            if current_id and current_name:
                ids[current_id] = current_name
            in_term = False
            current_id = None
            current_name = None
        elif in_term:
            if line.startswith("id:"):
                current_id = line.split(":", 1)[1].strip()
            elif line.startswith("name:"):
                current_name = line.split(":", 1)[1].strip()
    if in_term and current_id and current_name:
        ids[current_id] = current_name
    return ids


def main() -> int:
    """Verify anchor ids and print a report.

    Returns:
        int: 0 on success, 1 if any id is missing.
    """
    if not ZFA_OBO.exists():
        print(f"ERROR: {ZFA_OBO} not found. Run scripts/setup_data.sh first.", file=sys.stderr)
        return 1

    zfa_ids = load_zfa_ids(ZFA_OBO)
    panels = yaml.safe_load(PANELS_YAML.read_text(encoding="utf-8"))

    missing: list[tuple[str, str]] = []
    found: list[tuple[str, str, str]] = []

    for bucket, spec in panels.items():
        if not isinstance(spec, dict):
            continue
        anchors: list[str] = spec.get("ontology_anchor", []) or []
        for zfa_id in anchors:
            if zfa_id in zfa_ids:
                found.append((bucket, zfa_id, zfa_ids[zfa_id]))
            else:
                missing.append((bucket, zfa_id))

    if found:
        print("Verified anchors:")
        for bucket, zfa_id, name in found:
            print(f"  {bucket}: {zfa_id} = {name}")

    if missing:
        print("\nMISSING anchors:", file=sys.stderr)
        for bucket, zfa_id in missing:
            print(f"  {bucket}: {zfa_id} NOT FOUND in zfa.obo", file=sys.stderr)
        return 1

    print(f"\nAll {len(found)} anchor ids verified OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
