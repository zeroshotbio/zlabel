"""Audit every panels.yaml marker against the real ZFIN data for resolution and grounding.

The curation gate behind the panel taxonomy. For each marker it checks two things
against the downloaded data/ontologies snapshot:

  1. Resolution: the symbol resolves to a current ZFIN symbol via the GAF synonym
     map (genes.normalize_symbol). A marker that resolves to nothing is dead weight
     -- the scorer can never match it -- and fails the audit.
  2. Grounding: the marker's ZFIN wildtype-expression records sit at or under one of
     the panel's ontology anchors (is_a/part_of ancestry). Each identity panel needs
     at least CONVERGENCE_MIN grounding markers, or resolve.py can never name the
     anchor and the panel only ever falls back.

Anchor existence is checked separately by scripts/verify_anchors.py; this script
assumes the ids are real and focuses on the markers. State panels carry no anchor,
so only their resolution is checked.

Run before committing panel changes (needs scripts/setup_data.sh data):
    uv run python scripts/audit_panels.py

Exits non-zero if any marker is dead or any identity panel has fewer than
CONVERGENCE_MIN grounding markers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import zlabel
from zlabel.data import ancestors
from zlabel.genes import normalize_symbol
from zlabel.panels import KIND_IDENTITY, load_panels
from zlabel.resolve import CONVERGENCE_MIN

ROOT = Path(__file__).parent.parent
PANELS_YAML = ROOT / "src" / "zlabel" / "panels.yaml"
DATA = ROOT / "data" / "ontologies"
GAF = DATA / "zfin.gaf"
EXPR = DATA / "zfin_wildtype_expression.txt"
ZFA = DATA / "zfa.obo"


def main() -> int:
    """Audit panels.yaml markers and print a per-panel report.

    Returns:
        int: 0 when every marker resolves and every identity panel has at least
            CONVERGENCE_MIN grounding markers, else 1.
    """
    for path in (GAF, EXPR, ZFA):
        if not path.exists():
            print(f"ERROR: {path} not found. Run scripts/setup_data.sh first.", file=sys.stderr)
            return 1

    synonyms = zlabel.load_gene_synonym_map(GAF)
    expression = zlabel.load_zfin_expression(EXPR)
    zfa = zlabel.load_zfa(ZFA)
    panels = load_panels(PANELS_YAML)

    def resolved_symbols(marker: str) -> set[str]:
        return set(normalize_symbol(marker, synonyms).symbols)

    def grounds(symbol: str, anchors: frozenset[str]) -> bool:
        # A marker grounds when any expression record sits at or under an anchor:
        # the anchor is the record's own term or one of its is_a/part_of ancestors.
        for record in expression.get(symbol.lower(), []):
            # ZFIN expression rows occasionally cite non-ZFA terms (e.g. BSPO spatial
            # ids); those are not in the anatomy graph, so they cannot ground.
            if record.zfa_id not in zfa:
                continue
            if record.zfa_id in anchors:
                return True
            if anchors & set(ancestors(zfa, record.zfa_id)):
                return True
        return False

    dead: list[str] = []
    thin: list[str] = []
    print(f"Auditing {len(panels)} panels against {DATA.name} (CONVERGENCE_MIN={CONVERGENCE_MIN}):\n")
    for panel in panels:
        grounding = 0
        panel_dead: list[str] = []
        for marker in sorted(panel.markers):
            symbols = resolved_symbols(marker)
            if not symbols:
                panel_dead.append(marker)
                continue
            if panel.kind == KIND_IDENTITY and any(grounds(symbol, panel.ontology_anchor) for symbol in symbols):
                grounding += 1
        dead.extend(f"{panel.bucket}:{marker}" for marker in panel_dead)

        if panel.kind == KIND_IDENTITY:
            ok = not panel_dead and grounding >= CONVERGENCE_MIN
            if grounding < CONVERGENCE_MIN:
                thin.append(f"{panel.bucket} ({grounding} grounding)")
            flag = "OK " if ok else "FAIL"
            print(f"  [{flag}] {panel.bucket:18s} {grounding}/{len(panel.markers)} ground", end="")
        else:
            flag = "OK " if not panel_dead else "FAIL"
            print(f"  [{flag}] {panel.bucket:18s} state ({len(panel.markers)} markers)", end="")
        print(f"  DEAD: {', '.join(panel_dead)}" if panel_dead else "")

    if dead:
        print(f"\nFAIL: {len(dead)} dead marker(s) that do not resolve via the GAF: {', '.join(dead)}", file=sys.stderr)
    if thin:
        print(f"FAIL: identity panel(s) below CONVERGENCE_MIN grounding: {', '.join(thin)}", file=sys.stderr)
    if dead or thin:
        return 1
    print("\nAll panels pass: every marker resolves; every identity panel converges.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
