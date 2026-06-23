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

# --- Out-of-distribution flag -------------------------------------------------
# Whether a caller can honestly force the top candidate. in_set means the evidence is
# consistent with a known reference type the descent can reach (force-able); the other three
# mark genuinely-unassigned regimes. in_set is a soft signal, not a certification -- a broad
# attractor panel can mask a structural blind-spot. See the Label.ood docstring.

Ood = Literal["in_set", "structural", "doublet", "no_signal"]
OOD_IN_SET: Ood = "in_set"


# --- Sub-models ---------------------------------------------------------------


class Candidate(BaseModel):
    """One bucket the evidence is consistent with, in the near-tie candidate set.

    Surfaced on Label so a caller can see the competing types and their separation, and force the
    top of set when it judges the call worth forcing. Carries the adjusted identity score decide()
    actually ranks on, not the raw panel score (which omits the state-weight discount).

    Attributes:
        bucket (str): The identity panel bucket name (e.g. muscle, endothelium).
        germ_layer (str): The bucket's germ layer, so the caller sees germ-layer agreement.
        adjusted_score (float): The identity-only adjusted score decide() ranks on, in [0, 1].
        margin_to_top (float): The top member's adjusted score minus this one (0.0 for the top).
    """

    bucket: str
    germ_layer: str
    adjusted_score: float
    margin_to_top: float


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
            endothelium) when the descent finds no supported anchor, or to a
            germ-layer rollup / mixed/unresolved for abstentions and ties.
        levels (tuple[str, ...]): Ancestry chain from broad to specific, ending
            at the named ZFA term when the descent named one (e.g. musculature
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
            and the descent anchor (e.g. endothelium, muscle). Empty when
            abstained. Kept visible even when bucket is a named ZFA term.
        panel_germ_layer (str): The winning panel's germ layer, shown for context
            (e.g. mesoderm). Empty when abstained.
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
        candidates (tuple[Candidate, ...]): The near-tie candidate set -- identity buckets
            within DOMINANCE_GAP of the top, best-first. A clear winner yields one member; a
            near-tie yields the competing types with their margins. Empty when no identity panel
            matched. Lets a caller force the top of set when it judges that worthwhile.
        ood (Ood): Whether the call is force-able. in_set means the evidence is consistent with a
            reference type the descent can reach (the selection residual is force-able); structural
            means the markers reach no named term under any anchor (a blind-spot or novel type);
            doublet means contradictory germ layers; no_signal means no identity hit. in_set is
            high-recall but soft -- a broad attractor can mask a blind-spot, so a structural or
            doublet flag is far more trustworthy than an in_set one. Always in_set for an assigned call.
        margin (float): The raw, un-clamped lead of the top adjusted score over the runner-up
            (top_adj minus second_adj). The selection signal a caller thresholds to decide whether
            to force; distinct from the clamped margin confidence-component.
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
    candidates: tuple[Candidate, ...] = ()
    ood: Ood = OOD_IN_SET
    margin: float = 0.0

    @model_validator(mode="after")
    def _check_abstain_consistency(self) -> Label:
        """Enforce the confidence-vs-abstained and ood-vs-abstained invariants.

        confidence and confidence_score are None iff abstained. A non-in_set ood marks an
        abstention regime (structural, doublet, no_signal), so it may only appear on an
        abstention; an assigned Label is always in_set (it named or fell back to a real bucket).
        The implication is one-directional: an abstention may still be in_set (a same-germ-layer
        near-tie whose types are both known).

        Returns:
            Label: self, after validation.

        Raises:
            ValueError: If abstained, confidence, and confidence_score disagree, or a non-in_set
                ood appears on an assigned Label.
        """
        if self.abstained:
            if self.confidence is not None or self.confidence_score is not None:
                raise ValueError("abstained Label must have confidence and confidence_score = None")
        elif self.confidence is None or self.confidence_score is None:
            raise ValueError("assigned Label must have a confidence tier and score")
        if self.ood != OOD_IN_SET and not self.abstained:
            raise ValueError("a non-in_set ood marks an abstention regime; an assigned Label must be in_set")
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


# --- Introspection trace ------------------------------------------------------
# The trace models capture the intermediates a single label() call computes but
# the Label packet omits. They are the advanced surface: import from zlabel.models,
# not the top level. Produced by label.trace() / Labeler.trace().


class NormalizedMarkerTrace(BaseModel):
    """One marker's normalization outcome, made visible for introspection.

    Mirrors genes.NormalizedSymbol as a YAML-safe record, adding the marker's
    1-based input rank and a dropped flag. A dropped marker (ambiguous or
    unresolved) is silently excluded from scoring and the vote, so surfacing it
    explains gaps between the input list and the markers the engine actually used.

    Attributes:
        input (str): The marker symbol as supplied by the caller.
        status (str): Normalization outcome: resolved, ambiguous, or unresolved.
        symbols (tuple[str, ...]): Current ZFIN symbol(s), sorted. One when
            resolved, several when ambiguous, empty when unresolved.
        note (str | None): Human-readable reason when not resolved, else None.
        rank (int): 1-based position of the marker in the input list.
        dropped (bool): True when status is not resolved (excluded from scoring).
    """

    input: str
    status: str
    symbols: tuple[str, ...]
    note: str | None = None
    rank: int
    dropped: bool


class BucketScoreTrace(BaseModel):
    """One panel bucket's score, with the adjusted score and its decision role.

    The panel ladder as decide() ranks it. score is the raw scorer fraction;
    adjusted_score is the identity-only score decide() actually sorts on (it
    discounts state-only marker weight). is_winner and is_contender expose which
    buckets drove the branch the engine took.

    Attributes:
        bucket (str): The panel bucket name.
        score (float): Raw overlap fraction from score_markers, in [0, 1].
        adjusted_score (float): Identity-only adjusted score decide() ranks on
            (0.0 for buckets that were not ranked, e.g. state or zero-hit panels).
        germ_layer (str): The bucket's germ layer.
        kind (str): identity or state.
        matched_markers (tuple[str, ...]): Resolved symbols that hit this bucket,
            in rank order.
        is_winner (bool): True for the single bucket decide() selected.
        is_contender (bool): True for a bucket within the near-tie contender set.
    """

    bucket: str
    score: float
    adjusted_score: float
    germ_layer: str
    kind: str
    matched_markers: tuple[str, ...]
    is_winner: bool = False
    is_contender: bool = False


class TermVoteTrace(BaseModel):
    """One candidate ZFA term in the convergence descent, with its gate evaluation.

    Unlike resolve.TermVote (which the engine keeps only for terms that clear
    every gate), this is recorded for every tallied term -- including near-misses
    -- so an abstention or fallback can be explained by which gate a term failed.

    Attributes:
        zfa_id (str): The candidate ZFA term id.
        zfa_name (str): Human-readable name, or the raw id when name-less.
        gene_count (int): Distinct genes that credited this term.
        genes (tuple[str, ...]): Those gene symbols, sorted.
        information_content (float): Term IC under the background model (bits);
            0.0 when the term is absent from the IC model.
        ancestor_depth (int): Count of is_a+part_of ancestors (specificity proxy).
        passed_convergence (bool): Whether gene_count >= CONVERGENCE_MIN.
        passed_stoplist (bool): Whether the term is not a content-free stoplist root.
        passed_information_content (bool): Whether information_content >= INFORMATION_CONTENT_MIN.
        grounded_under_anchor (bool): True for the selected (descent terminal) term, which
            sits at or under the winning panel's anchor by construction. False for every other
            term (the descent only ever names at or under the anchor).
        eligible (bool): True when all three resolve gates passed. With the anchor-rooted
            descent these gates no longer drive naming (the descent's support floors do); kept
            as transparency, so passed_information_content is informational, not a naming gate.
        selected (bool): True for the single term the descent named the cluster.
        support_fraction (float): For a term on the descent path, its distinct-gene support as a
            share of its parent's on the path (the seed is 1.0); for other terms, its support as
            a share of the most-supported term. The consensus signal the descent stops on.
        on_descent_path (bool): True for the terms on the anchor-to-terminal descent path.
    """

    zfa_id: str
    zfa_name: str
    gene_count: int
    genes: tuple[str, ...]
    information_content: float
    ancestor_depth: int
    passed_convergence: bool
    passed_stoplist: bool
    passed_information_content: bool
    grounded_under_anchor: bool = False
    eligible: bool = False
    selected: bool = False
    support_fraction: float = 0.0
    on_descent_path: bool = False


class LabelTrace(BaseModel):
    """Faithful step-by-step trace of one label() call, for introspection.

    Produced by label.trace() and Labeler.trace(). It records the intermediates
    the Label packet omits -- the normalization outcomes, the full panel ladder,
    the complete convergence descent with per-term gate results, and the decision
    branch taken -- and embeds the real Label as the single source of truth for
    the outcome. Every field is a primitive or a trace sub-model, so to_yaml() is
    lossless. Advanced surface: import it from zlabel.models, not the top level.

    Attributes:
        markers_in (tuple[str, ...]): The raw marker symbols as supplied.
        stage_hpf (float | None): Developmental stage used, or None.
        normalized_markers (tuple[NormalizedMarkerTrace, ...]): Per-marker
            normalization outcomes, in input order.
        resolved_symbols (tuple[str, ...]): The resolved current ZFIN symbols
            scoring and the descent actually used.
        panel_scores (tuple[BucketScoreTrace, ...]): The panel ladder, in scorer
            order (descending score).
        branch (str): The decision-ladder branch taken (e.g. clear-winner).
        term_votes (tuple[TermVoteTrace, ...]): Every tallied ZFA term with its gate
            evaluation. Descent-path terms come first, anchor to terminal (ascending
            ancestor depth); the rest follow by descending support. Empty when the
            descent was not run (the precheck and rollup branches); check branch first.
        label (Label): The final evidence packet, identical to label()'s return.
    """

    markers_in: tuple[str, ...]
    stage_hpf: float | None
    normalized_markers: tuple[NormalizedMarkerTrace, ...]
    resolved_symbols: tuple[str, ...]
    panel_scores: tuple[BucketScoreTrace, ...]
    branch: str
    term_votes: tuple[TermVoteTrace, ...]
    label: Label

    def to_yaml(self) -> str:
        """Serialise the trace to YAML in declaration (pipeline) order.

        model_dump() recurses into the trace sub-models and the embedded Label;
        tuples serialise as lists. Mirrors Label.to_yaml so consumers get one
        readable, round-trippable format.

        Returns:
            str: YAML string representation of the trace.
        """
        return yaml.safe_dump(self.model_dump(), sort_keys=False, allow_unicode=True)
