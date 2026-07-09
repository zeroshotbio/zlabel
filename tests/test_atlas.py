"""Tests for the organ-level ZFA atlas roll-up (zlabel.atlas).

Hermetic tests exercise the roll-up LOGIC on a tiny synthetic ontology; a final integration test pins
the biologically-verified fix cases against the real zfa.obo when it is present.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from zlabel import atlas

_OBO = Path(__file__).resolve().parents[1] / "data" / "ontologies" / "zfa.obo"


def _toy() -> nx.MultiDiGraph:
    """child -> parent edges keyed by relation, mirroring obonet's graph shape."""
    g = nx.MultiDiGraph()
    # rhombomere is a hindbrain segment (part_of brain) but also is_a neuromere (-> a fallback CNS)
    g.add_edge("rhombomere", "neuromere", key="is_a")
    g.add_edge("neuromere", "cns", key="part_of")  # nearer fallback (depth 2)
    g.add_edge("rhombomere", "hindbrain", key="part_of")
    g.add_edge("hindbrain", "brain", key="is_a")  # organ (depth 2)
    g.add_edge("hepatocyte", "liver", key="is_a")
    return g


def test_nearest_walks_is_a_and_part_of():
    g = _toy()
    assert atlas._nearest(g, "rhombomere", {"brain": "Brain"}) == "brain"
    assert atlas._nearest(g, "hepatocyte", {"liver": "Liver"}) == "liver"
    assert atlas._nearest(g, "rhombomere", {"cns": "Nervous system"}) == "cns"


def test_organ_first_beats_a_fallback():
    """An organ ancestor must win over a fallback ancestor (the rhombomere tie)."""
    g = _toy()
    organs, fallbacks = {"brain": "Brain"}, {"cns": "Nervous system"}
    anchor = atlas._nearest(g, "rhombomere", organs) or atlas._nearest(g, "rhombomere", fallbacks)
    assert organs[anchor] == "Brain"


def test_fallback_used_when_no_organ():
    g = _toy()
    organs, fallbacks = {"brain": "Brain"}, {"cns": "Nervous system"}
    # a bare neuromere reaches only the fallback cns, no organ
    anchor = atlas._nearest(g, "neuromere", organs) or atlas._nearest(g, "neuromere", fallbacks)
    assert fallbacks[anchor] == "Nervous system"


def test_absent_term_and_none():
    g = _toy()
    assert atlas._nearest(g, "not_in_graph", {"brain": "Brain"}) is None
    assert atlas._nearest(g, None, {"brain": "Brain"}) is None


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
