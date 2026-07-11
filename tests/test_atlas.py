"""Tests for the organ-level ZFA atlas roll-up (zlabel.atlas).

Hermetic tests exercise the PUBLIC roll-up (atlas_anchor / atlas_rollup) on a tiny synthetic ontology
built with REAL ZFA anchor ids, so they run the real ATLAS_ORGANS / ATLAS_FALLBACKS tiers without
needing zfa.obo. A final integration test pins the biologically-verified fix cases against the real
zfa.obo when it is present.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from zlabel import atlas

_OBO = Path(__file__).resolve().parents[1] / "data" / "ontologies" / "zfa.obo"

# Real tier anchors, so the toy graph drives the real public API rather than a re-implemented precedence.
_BRAIN = "ZFA:0000008"  # ATLAS_ORGANS -> "Brain"
_CNS = "ZFA:0000012"  # ATLAS_FALLBACKS -> "Nervous system"
_LIVER = "ZFA:0000123"  # ATLAS_ORGANS -> "Liver"
_RHOMBOMERE = "ZFA:0001064"


def _toy() -> nx.MultiDiGraph:
    """child -> parent edges keyed by relation, mirroring obonet's graph shape.

    Anchor nodes use real ZFA ids so atlas_anchor/atlas_rollup resolve against the real tiers;
    intermediate/leaf ids are stand-ins (they never appear in a tier).
    """
    g = nx.MultiDiGraph()
    # rhombomere sits at an equal-depth multi-parent tie: is_a neuromere -> CNS (fallback, depth 2) and
    # part_of hindbrain -> brain (organ, depth 2). Organ-first must pick Brain.
    g.add_edge(_RHOMBOMERE, "neuromere", key="is_a")
    g.add_edge("neuromere", _CNS, key="part_of")
    g.add_edge(_RHOMBOMERE, "hindbrain", key="part_of")
    g.add_edge("hindbrain", _BRAIN, key="is_a")
    g.add_edge("hepatocyte", _LIVER, key="is_a")
    # a term that IS in the graph and has an ancestor, but none of its ancestors land in any tier
    g.add_edge("untracked_cell", "untracked_structure", key="is_a")
    return g


def test_nearest_walks_is_a_and_part_of():
    """The private walker returns the nearest ancestor present in the given tier (self first)."""
    g = _toy()
    assert atlas._nearest(g, _RHOMBOMERE, {_BRAIN: "Brain"}) == _BRAIN
    assert atlas._nearest(g, "hepatocyte", {_LIVER: "Liver"}) == _LIVER
    assert atlas._nearest(g, _RHOMBOMERE, {_CNS: "Nervous system"}) == _CNS


def test_atlas_anchor_is_organ_first_on_a_tie():
    """rhombomere reaches Brain (organ) and CNS (fallback) at equal depth -> organ-first picks Brain."""
    g = _toy()
    assert atlas.atlas_anchor(g, _RHOMBOMERE) == _BRAIN
    assert atlas.atlas_rollup(g, _RHOMBOMERE) == {"term": "Brain", "zfa_id": _BRAIN}


def test_atlas_rollup_falls_back_to_a_system_when_no_organ():
    """A term whose only tier ancestor is a system fallback is still labelled (coarse, not dropped)."""
    g = _toy()
    assert atlas.atlas_anchor(g, "neuromere") == _CNS
    assert atlas.atlas_rollup(g, "neuromere") == {"term": "Nervous system", "zfa_id": _CNS}


def test_atlas_rollup_none_when_no_tier_ancestor():
    """In-graph term with ancestors but none in any tier -> None (distinct from an absent id)."""
    g = _toy()
    assert atlas.atlas_anchor(g, "untracked_cell") is None
    assert atlas.atlas_rollup(g, "untracked_cell") is None


def test_absent_term_and_none():
    g = _toy()
    assert atlas.atlas_anchor(g, "not_in_graph") is None
    assert atlas.atlas_anchor(g, None) is None
    assert atlas.atlas_rollup(g, None) is None


def test_tier_invariants():
    both = {**atlas.ATLAS_ORGANS, **atlas.ATLAS_FALLBACKS}
    assert atlas.ATLAS_ORGANS and atlas.ATLAS_FALLBACKS
    assert all(z.startswith("ZFA:") for z in both)
    assert all(isinstance(v, str) and v for v in both.values())
    # organs and fallbacks must not share ids (would make precedence ambiguous)
    assert not (set(atlas.ATLAS_ORGANS) & set(atlas.ATLAS_FALLBACKS))


@pytest.mark.skipif(not _OBO.exists(), reason="zfa.obo not present (run scripts/setup_data.sh)")
def test_real_zfa_fix_cases_and_coverage():
    from zlabel import load_zfa

    g = load_zfa(str(_OBO))
    # every tier id exists in the ontology
    for z in {**atlas.ATLAS_ORGANS, **atlas.ATLAS_FALLBACKS}:
        assert z in g, f"tier id {z} absent from zfa.obo"
    # the adversarially-verified roll-ups
    cases = {
        "ZFA:0001064": "Brain",  # rhombomere (multi-parent tie -> organ-first)
        "ZFA:0005326": "Ionocyte",  # NaK ionocyte (sibling of epidermis under integument)
        "ZFA:0000150": "Kidney",  # pronephric duct -> pronephros
        "ZFA:0005316": "Fin",  # fin fold pectoral fin bud -> fin bud anchor
        "ZFA:0000079": "Brain",  # telencephalon
        "ZFA:0000152": "Eye",  # retina
        "ZFA:0009280": "Glia",  # Muller cell (is_a glial lineage beats part_of eye)
        "ZFA:0000019": "Pineal",  # epiphysis
    }
    for z, want in cases.items():
        r = atlas.atlas_rollup(g, z)
        assert r and r["term"] == want, f"{z} -> {r} (want {want})"
