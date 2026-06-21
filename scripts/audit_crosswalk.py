"""Audit the Daniocell gold-anchor crosswalk: every comment-named member must ground under its anchor.

The crosswalk (benchmarks/daniocell_tissue_crosswalk.yaml) is the eval's hand-curated
answer key: each Daniocell tissue code maps to the ZFA anchor ids a prediction must
ground under (is_a/part_of) to count as agreement. The Daniocell codes are authoritative;
the anchor choice is the fallible, hand-curated layer. Each tissue's inline comment
enumerates the structures it is meant to cover, for example:

    axia:  # axial (notochord, prechordal plate, hatching gland)

This script reads those comment members and checks each one grounds under the tissue's
anchors. A member that resolves to a real ZFA term but does not ground is a too-tight
anchor: the gold denominator silently mis-scores a legitimate call as a disagreement,
which is the bug the notochord and hatching-gland fixes closed.

Blind spot: this catches a too-tight anchor (a missing member), not a too-loose one (an
anchor that also grounds non-members, letting wrong calls count) -- the more flattering
error. A reverse check (do other tissues' members wrongly ground here?) is future work.

Per-member verdicts:
  PASS  grounds under the tissue's anchors (the anchor itself or an is_a/part_of descendant)
  INFO  broader than an anchor (an ancestor) -- a gloss, e.g. pron (kidney), not a gap
  ACPT  a reviewed gap intentionally left open (see ACCEPTED_GAPS), not auto-closed
  GAP   resolves to a ZFA term that neither grounds nor is a gloss -- a curation miss (fails)
  ????  did not resolve to a ZFA name or synonym (a prose label, or a name gap); reported only

Run before changing the crosswalk (needs scripts/setup_data.sh data):
    uv run python scripts/audit_crosswalk.py

Exits non-zero on any GAP that is not in ACCEPTED_GAPS.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import networkx as nx

import zlabel
from zlabel.data import term_name
from zlabel.evaluate import load_crosswalk
from zlabel.ground import grounds_under

ROOT = Path(__file__).parent.parent
CROSSWALK = ROOT / "benchmarks" / "daniocell_tissue_crosswalk.yaml"
ZFA = ROOT / "data" / "ontologies" / "zfa.obo"

# Reviewed gaps intentionally NOT closed by adding an anchor -- a curation decision recorded
# in the open, never a silent pass. Each asserts a relationship ZFA does not itself encode, so
# closing it would be the curator overriding the ontology. Keyed by (tissue, member); the value
# is the rationale and the pending decision.
ACCEPTED_GAPS: dict[tuple[str, str], str] = {
    ("mura", "vascular smooth muscle"): (
        "ZFA encodes no is_a/part_of path from vascular smooth muscle (ZFA:0005321) to mural cell "
        "(ZFA:0005944), though VSM is biologically a mural cell. Pending sign-off: add ZFA:0005321 "
        "to mura's anchors, or keep it a known gap (a VSM call on a mura cluster will not count)."
    ),
}


def build_name_index(zfa: nx.MultiDiGraph) -> dict[str, list[str]]:
    """Map every ZFA term name and synonym (lowercased) to the ids that bear it.

    Args:
        zfa (nx.MultiDiGraph): The ZFA ontology from zlabel.load_zfa.

    Returns:
        dict[str, list[str]]: Lowercased name or synonym text to the ZFA ids that bear it.
            obonet stores synonyms as raw OBO strings (a quoted term plus a scope); only the
            quoted term is indexed.
    """
    index: dict[str, list[str]] = {}
    for node_id, attrs in zfa.nodes(data=True):
        name = attrs.get("name")
        if isinstance(name, str):
            index.setdefault(name.lower(), []).append(node_id)
        for raw in attrs.get("synonym", []) or []:
            quoted = re.match(r'"([^"]+)"', raw)
            if quoted:
                index.setdefault(quoted.group(1).lower(), []).append(node_id)
    return index


def resolve(index: dict[str, list[str]], member: str) -> list[str]:
    """Resolve a comment member name to ZFA ids: exact, then simple singular, then synonym.

    Substring matching is deliberately avoided -- a loose match would let the audit claim a
    structure is covered when it is not, defeating the point.

    Args:
        index (dict[str, list[str]]): The name and synonym index from build_name_index.
        member (str): A structure name taken from a crosswalk comment.

    Returns:
        list[str]: The matching ZFA ids, or an empty list when nothing resolves (a prose
            label or a genuine name gap).
    """
    name = member.strip().lower()
    if name in index:
        return index[name]
    if name.endswith("s") and name[:-1] in index:  # pericytes -> pericyte
        return index[name[:-1]]
    return []


def parse_members(comment: str) -> list[str]:
    """Extract the structure names a tissue's inline comment enumerates.

    Splits on the separators the crosswalk comments use -- parentheses, commas, slashes, and
    pluses -- after dropping any trailing review note. Category labels that are not ZFA terms
    simply fail to resolve later and are reported, not failed on.

    Args:
        comment (str): The inline comment after a tissue key (the text after the hash).

    Returns:
        list[str]: Candidate member names, lowercased and de-duplicated in order.
    """
    head = re.split(r"--|review:", comment)[0]
    members: list[str] = []
    for token in re.split(r"[(),/+]", head):
        name = token.strip().lower()
        if name and name not in members:
            members.append(name)
    return members


def tissue_comments(path: Path) -> dict[str, str]:
    """Read each tissue key's inline comment from the raw crosswalk yaml.

    load_crosswalk parses the anchors, but yaml.safe_load drops comments, so the member
    enumerations are recovered from the file text here.

    Args:
        path (Path): Path to daniocell_tissue_crosswalk.yaml.

    Returns:
        dict[str, str]: Tissue code to its inline comment text.
    """
    comments: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^  (\w+):\s*#\s*(.*)$", line)
        if match:
            comments[match.group(1)] = match.group(2)
    return comments


def classify(zfa: nx.MultiDiGraph, member_ids: list[str], anchors: frozenset[str]) -> str:
    """Classify a resolved member against a tissue's anchors.

    Args:
        zfa (nx.MultiDiGraph): The ZFA ontology.
        member_ids (list[str]): The ZFA ids the member name resolved to.
        anchors (frozenset[str]): The tissue's gold anchor ids.

    Returns:
        str: PASS when the member grounds under an anchor (self or is_a/part_of descendant);
            INFO when an anchor grounds under the member (the member is a broader ancestor, a
            gloss); GAP otherwise.
    """
    if any(grounds_under(zfa, member_id, anchors) for member_id in member_ids):
        return "PASS"
    if any(grounds_under(zfa, anchor, frozenset(member_ids)) for anchor in anchors):
        return "INFO"
    return "GAP"


def main() -> int:
    """Audit the crosswalk comment members and print a per-tissue report.

    Returns:
        int: 0 when every resolved member grounds, is a gloss, or is an accepted gap; 1 when
            any member is an unaccepted grounding gap.
    """
    if not ZFA.exists():
        print(f"ERROR: {ZFA} not found. Run scripts/setup_data.sh first.", file=sys.stderr)
        return 1

    zfa = zlabel.load_zfa(ZFA)
    crosswalk = load_crosswalk(CROSSWALK)
    comments = tissue_comments(CROSSWALK)
    index = build_name_index(zfa)

    gaps: list[str] = []
    print(f"Auditing {len(crosswalk.anchors)} scored crosswalk tissues against {ZFA.parent.name}:\n")
    for tissue in sorted(crosswalk.anchors):
        anchors = crosswalk.anchors[tissue]
        for member in parse_members(comments.get(tissue, "")):
            member_ids = resolve(index, member)
            if not member_ids:
                print(f"  [????] {tissue:5s} {member:24s} no ZFA name/synonym (prose label?)")
                continue
            verdict = classify(zfa, member_ids, anchors)
            if verdict == "GAP" and (tissue, member) in ACCEPTED_GAPS:
                verdict = "ACPT"
            shown = term_name(zfa, member_ids[0]) or member_ids[0]
            print(f"  [{verdict}] {tissue:5s} {member:24s} {member_ids[0]} ({shown})")
            if verdict == "GAP":
                gaps.append(f"{tissue}:{member}")

    if gaps:
        print(
            f"\nFAIL: {len(gaps)} member(s) do not ground under their tissue anchor: {', '.join(gaps)}",
            file=sys.stderr,
        )
        print(
            "Add the member's ZFA term to that tissue's anchors if Daniocell groups it there and "
            "biology agrees (the addition must stand even if it lowered agreement), or record it in "
            "ACCEPTED_GAPS with a rationale.",
            file=sys.stderr,
        )
        return 1
    print("\nAll crosswalk members ground under their tissue anchors (or are accepted gaps/glosses).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
