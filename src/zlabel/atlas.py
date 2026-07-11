"""Roll any ZFA term up to a curated, organ-level "atlas" vocabulary.

The zlabel-scope studio's atlas view needs ONE human-readable, organ-level anatomy label per cluster,
consistent across datasets. Every reference tissue or engine call resolves to a ZFA (Zebrafish Anatomy
Ontology) term; this rolls that term up the ontology (is_a + part_of ancestry, nearest-first via
zlabel.data.ancestors) to the nearest term in the atlas tier.

Two tiers, ORGAN-FIRST: take the nearest ORGAN, and only fall back to a system / germ-layer term when no
organ ancestor is reachable. This matters because ZFA is a multi-parent DAG -- e.g. rhombomere is
is_a neuromere (-> nervous system) and part_of hindbrain (-> brain) at equal depth; organ-first
guarantees Brain wins. It also keeps honestly-coarse labels (a generic neural cluster -> "Nervous
system") instead of dropping them.

Every id is verified present in zfa.obo and every roll-up on the three studio datasets was
adversarially checked against ZFA/ZFIN. Anchors are chosen so sibling-gap terms still resolve: fin bud
(0001383) for fin-fold terms, pronephros (0000151, the larval kidney -- a sibling of generic
kidney), and ionocyte (0005323) kept distinct from its epidermis sibling under integument.
"""

from __future__ import annotations

import networkx as nx

from zlabel.data import ancestors

# Organ / cell-type level -- first-class, human-readable. Roll-ups prefer these over the fallbacks.
ATLAS_ORGANS: dict[str, str] = {
    # nervous + sensory (organs, split out of the coarse "nervous system")
    "ZFA:0000008": "Brain",
    "ZFA:0000075": "Spinal cord",
    "ZFA:0000107": "Eye",
    "ZFA:0000217": "Ear",  # inner ear
    "ZFA:0000051": "Ear",  # otic vesicle (embryonic anlage; reaches Ear only via this hand-anchor)
    "ZFA:0000034": "Lateral line",  # lateral line system
    "ZFA:0001469": "Lateral line",
    "ZFA:0001149": "Olfactory",
    "ZFA:0000045": "Neural crest",  # lineage, but a bounded, high-value developmental population
    "ZFA:0009073": "Glia",
    "ZFA:0000019": "Pineal",  # epiphysis -- a distinct photosensory/endocrine organ
    "ZFA:0005323": "Ionocyte",  # canonical distinct cell type; sibling of epidermis under integument
    # muscle / skeleton / structural
    "ZFA:0000548": "Muscle",  # musculature system
    "ZFA:0000135": "Notochord",
    "ZFA:0000031": "Hypochord",
    "ZFA:0000108": "Fin",
    "ZFA:0001383": "Fin",  # fin bud -- fin-fold/bud terms don't pass through 'fin' (0000108)
    "ZFA:0001501": "Cartilage",
    "ZFA:0001632": "Connective tissue",
    "ZFA:0001306": "Pharyngeal arch",
    "ZFA:0000026": "Hatching gland",
    # circulatory / blood
    "ZFA:0000114": "Heart",
    "ZFA:0005249": "Blood vessel",  # vasculature
    "ZFA:0005314": "Blood vessel",
    "ZFA:0005944": "Mural cell",  # pericytes/vSMC -- a distinct lineage, parallel to blood vessel
    "ZFA:0000007": "Blood",
    "ZFA:0001159": "Immune",
    # skin / surface (integument 0000368 is a FALLBACK so Ionocyte wins over its epidermis sibling)
    "ZFA:0000105": "Epidermis",
    "ZFA:0001185": "Periderm",  # part_of ectoderm, NOT epidermis -- transient EVL layer, keep distinct
    "ZFA:0009090": "Pigment",
    # kidney / endoderm / endocrine / germ line / early
    "ZFA:0000151": "Kidney",  # pronephros = larval zebrafish kidney
    "ZFA:0000529": "Kidney",
    "ZFA:0000163": "Kidney",  # renal system
    "ZFA:0000123": "Liver",
    "ZFA:0000140": "Pancreas",
    "ZFA:0001338": "Intestine",  # part_of gut; more specific than the "Gut" fallback
    "ZFA:0000056": "Pharynx",
    "ZFA:0000076": "Swim bladder",
    "ZFA:0001282": "Pituitary",
    "ZFA:0001345": "Interrenal",
    "ZFA:0009288": "Germ line",
    "ZFA:0009016": "Germ line",
    "ZFA:0000088": "Yolk syncytial layer",
}

# System / germ-layer / catch-all -- used ONLY when no organ ancestor exists, so honestly-coarse
# clusters are still labelled rather than dropped. Mesenchyme is the lowest-value catch-all.
ATLAS_FALLBACKS: dict[str, str] = {
    "ZFA:0000396": "Nervous system",
    "ZFA:0000012": "Nervous system",  # central nervous system
    "ZFA:0000142": "Peripheral nervous system",
    "ZFA:0000368": "Epidermis",  # integument (its sibling Ionocyte out-ranks via the organ tier)
    "ZFA:0005023": "Blood",  # hematopoietic system
    "ZFA:0000339": "Gut",  # digestive system
    "ZFA:0000434": "Skeleton",  # skeletal system
    "ZFA:0001158": "Endocrine",  # endocrine system
    "ZFA:0000255": "Paraxial mesoderm",
    "ZFA:0001204": "Axial mesoderm",
    "ZFA:0001206": "Intermediate mesoderm",
    "ZFA:0000017": "Endoderm",
    "ZFA:0000393": "Mesenchyme",  # cross-lineage architectural grab-bag -- lowest precedence
}

_ALL = {**ATLAS_FALLBACKS, **ATLAS_ORGANS}  # organs win on any id overlap


def _nearest(graph: nx.MultiDiGraph, zfa_id: str | None, tier: dict[str, str]) -> str | None:
    """The nearest ancestor id (self first) present in tier, walking is_a+part_of, or None."""
    if not zfa_id or zfa_id not in graph:
        return None
    for cand in (zfa_id, *ancestors(graph, zfa_id)):
        if cand in tier:
            return cand
    return None


def atlas_anchor(graph: nx.MultiDiGraph, zfa_id: str | None) -> str | None:
    """The atlas ZFA anchor a term rolls up to: nearest ORGAN, else nearest system fallback, else None."""
    return _nearest(graph, zfa_id, ATLAS_ORGANS) or _nearest(graph, zfa_id, ATLAS_FALLBACKS)


def atlas_rollup(graph: nx.MultiDiGraph, zfa_id: str | None) -> dict[str, str] | None:
    """The atlas anchor a ZFA term rolls up to, as {"term", "zfa_id"}, or None if it reaches no tier.

    term is the human-readable organ; zfa_id is the tier anchor it grounded on.
    """
    anchor = atlas_anchor(graph, zfa_id)
    return None if anchor is None else {"term": _ALL[anchor], "zfa_id": anchor}
