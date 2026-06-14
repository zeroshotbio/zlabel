"""Evidence packet for a single cluster label decision.

Label is the stable, structured output of decide() and Labeler.label(): it carries
not just the bucket name but the confidence rubric, the grounding evidence, and
enough context for a human (or a future LLM narrator) to understand and verify the
call without digging into the library internals.

pydantic is used for two reasons: validation (the abstained/confidence invariant is
enforced at construction, not asserted at call sites) and clean YAML serialisation
via to_yaml(). Every field is a Python primitive so model_dump() is YAML-safe.
"""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

# --- Confidence tier names ----------------------------------------------------
# Named constants so the rest of the codebase never hard-codes the strings.

TIER_HIGH_NAME: Literal["high"] = "high"
TIER_MEDIUM_NAME: Literal["medium"] = "medium"
TIER_LOW_NAME: Literal["low"] = "low"

Confidence = Literal["high", "medium", "low"]


# --- Sub-models ---------------------------------------------------------------


class ExprHit(BaseModel):
    """One grounded marker's in-vivo anatomy evidence.

    Recorded for each of the winner's matched markers that grounds under the
    bucket's ontology anchor (i.e. it has a ZFIN expression record pointing at
    a ZFA term that is the anchor or a descendant of it). One hit per grounded
    marker, using the first grounding record in file order (deterministic).
    Stage data is a separate confidence component, not included here.

    Attributes:
        symbol (str): The resolved current ZFIN symbol of the matched marker.
        zfa_id (str): A ZFA id the marker expresses in that grounds under the
            bucket anchor (e.g. ZFA:0000548 for a muscle marker in musculature
            system).
        zfa_name (str): Human-readable name of that ZFA term (from the ontology),
            for readable evidence packets.
    """

    symbol: str
    zfa_id: str
    zfa_name: str


# --- Main evidence packet -----------------------------------------------------


class Label(BaseModel):
    """Evidence packet for one cluster label decision.

    Emitted by decide() and Labeler.label(). Every field is a Python primitive so
    model_dump() / to_yaml() are lossless and YAML-safe.

    The validator enforces that confidence and confidence_score are both None
    exactly when abstained is True; an inconsistent Label raises ValidationError.
    By convention an abstention also sets bucket to mixed/unresolved and empties the
    evidence fields, but that convention lives in the decision layer, not this packet.

    Attributes:
        bucket (str): The data-derived anatomy label: the most specific ZFA term
            the cluster's markers converge on in vivo (e.g. endothelial cell,
            muscle cell). Falls back to the coarse panel bucket (e.g. muscle,
            endothelium) when the convergence vote produces no eligible term, or
            to a germ-layer rollup / mixed/unresolved for abstentions and ties.
        levels (tuple[str, ...]): Ancestry chain from broad to specific, ending
            at the named ZFA term when the vote succeeded (e.g. musculature
            system, cell, muscle cell). Falls back to the static panel triple
            (germ_layer, tissue, lineage) when not named. Empty when abstained.
            len(levels) is the depth signal -- it now varies with evidence.
        depth (int): len(levels) echoed as an explicit integer for callers
            (e.g. the eval harness) that need the depth without recomputing it.
        abstained (bool): True when no decision was made (mixed/unresolved).
        confidence (Confidence | None): Tier name (high, medium, or low). None
            iff abstained.
        confidence_score (float | None): The raw weighted confidence in [0, 1].
            None iff abstained.
        confidence_components (dict[str, float]): The four rubric components
            (coherence, margin, grounding, stage) each in [0, 1]. Absent
            components use NEUTRAL (0.5). Empty dict when abstained.
        ambiguity_flag (str): One of none, mixed, underclustered, provisional.
            none for a clean single-bucket call.
        states (tuple[str, ...]): Detected state programs orthogonal to identity
            (e.g. cycling). Reported on every Label, including abstentions.
        panel_bucket (str): The coarse panel bucket name that acted as the prior
            and germ-layer guardrail (e.g. endothelium, muscle). Empty when
            abstained. Kept visible even when bucket is a named ZFA term.
        panel_germ_layer (str): The winning panel's germ layer (the guardrail
            context, e.g. mesoderm). Empty when abstained.
        zfa_id (str | None): The named convergent ZFA term id when the vote
            succeeded (e.g. ZFA:0005307 for endothelial cell). Falls back to the
            sorted-first panel anchor id, or None for rollups and abstentions.
        panel_scores (dict[str, float]): Raw BucketScore.score for every panel
            bucket (a direct echo of the scorer output; the adjusted identity
            scores used inside decide() are internal).
        positive_markers (tuple[str, ...]): Resolved current ZFIN symbols of
            markers that matched the winning panel.
        convergent_genes (tuple[str, ...]): Distinct resolved symbols that voted
            for the named ZFA term (the anatomy-convergence evidence). Distinct
            from positive_markers, which are panel-matched markers. Empty when
            no term was named.
        expression_evidence (tuple[ExprHit, ...]): Grounded anatomy hits for
            markers that express at or under the named ZFA term (or the panel
            anchor when no term was named).
        rationale (str): One-line human-readable reason for the call.
        next_step (str | None): Suggested next action. Subcluster when a bucket
            or rollup was assigned; None when abstained.
    """

    bucket: str
    levels: tuple[str, ...]
    depth: int = 0
    abstained: bool
    confidence: Confidence | None
    confidence_score: float | None
    confidence_components: dict[str, float]
    ambiguity_flag: str = "none"
    states: tuple[str, ...] = ()
    panel_bucket: str = ""
    panel_germ_layer: str = ""
    zfa_id: str | None = None
    panel_scores: dict[str, float]
    positive_markers: tuple[str, ...]
    convergent_genes: tuple[str, ...] = ()
    expression_evidence: tuple[ExprHit, ...]
    rationale: str
    next_step: str | None = None

    @model_validator(mode="after")
    def _check_abstain_consistency(self) -> Label:
        """Enforce that confidence and confidence_score are None iff abstained.

        Returns:
            Label: self, after validation.

        Raises:
            ValueError: If abstained, confidence, and confidence_score disagree.
        """
        if self.abstained:
            if self.confidence is not None or self.confidence_score is not None:
                raise ValueError("abstained Label must have confidence and confidence_score = None")
        elif self.confidence is None or self.confidence_score is None:
            raise ValueError("assigned Label must have a confidence tier and score")
        return self

    def to_yaml(self) -> str:
        """Serialise the evidence packet to YAML.

        Field order is preserved (sort_keys=False) so the packet reads in
        declaration order: bucket/levels first, then confidence components,
        then evidence. model_dump() converts nested ExprHit sub-models to dicts
        recursively; pydantic tuples serialise as lists. YAML round-trips
        cleanly for any downstream consumer.

        Returns:
            str: YAML string representation of the evidence packet.
        """
        return yaml.safe_dump(self.model_dump(), sort_keys=False, allow_unicode=True)
